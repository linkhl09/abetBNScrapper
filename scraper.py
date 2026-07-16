import base64
import os
import time
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.print_page_options import PrintOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import prompt_user_config, load_activities, select_students_for_abet, select_students_for_activity, extract_surnames, ensure_dir
from web_utils import find_in_shadow, search_element_by_id, search_text_in_element_list
from parser import parse_grades_page
from excel_utils import (
    add_sheet_with_table,
    append_array_to_table,
    create_workbook_with_sheet,
    extract_student_groups
)

BASE_URL = "https://bloqueneon.uniandes.edu.co"

class D2LScraper:
    def __init__(self):
        self.config = prompt_user_config()
        self.activities_config = load_activities()
        self._validate_groups_config()
        self._validate_activity_types()

        ensure_dir(self.config['root_folder'])
        
        # Configure results workbook
        self.workbook =  create_workbook_with_sheet(
            sheet_name="selectedStudents",
            headers=["Activity name", "Student Type", "Student name"],
            table_name="selectedStudentsTable",
        )
        add_sheet_with_table(
            self.workbook,
            sheet_name="errors",
            headers=["activity", "reason", "studentName"],
            table_name="errorsTable",
        )
        
        # Setup Chrome
        options = webdriver.ChromeOptions()
        # To handle automatic downloads:
        prefs = {"download.default_directory": self.config['root_folder'],
                 "download.prompt_for_download": False,
                 "directory_upgrade": True}
        options.add_experimental_option("prefs", prefs)
        
        print("Starting Chrome browser...")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def _validate_groups_config(self):
        contains_groups = False
        for activity in self.activities_config:
            if activity.get("groupName") is not None:
                contains_groups = True
                break
        
        if contains_groups:
            # check that a file named Groups_<course_code>.xlsx exists in the root folder
            course_code = self.config.get("course_code")
            filename = f"Groups_{course_code}.xlsx"
            if not os.path.exists(filename):
                print(f"Did not find Groups_{course_code}.xlsx in root folder.")
                print("")
            
            if os.path.exists(filename):
                print(f"Found Groups_{course_code}.xlsx in root folder. Loading groups information into config...")
                self.groups_config = extract_student_groups(filename, self.activities_config)
            else: 
                print("Could not find neither the default groups file nor a user-provided one. Please ensure you have a Groups_<course_code>.xlsx file in the root folder.")
                print("The file can be extracted from Brightspace by exporting grades with groups information.")
                print("If you do not have groups, please remove the 'groupName' field from your activities.json file.")
                print("Exiting program.")
                exit()

    def _validate_activity_types(self):
        valid_types = {"assignment", "quiz"}
        for activity in self.activities_config:
            activity_type = activity.get("type")
            if activity_type is not None and activity_type not in valid_types:
                print(f"Invalid 'type' value '{activity_type}' for activity '{activity.get('name')}'.")
                print(f"Valid values are: {sorted(valid_types)} (or omit the field for the default 'assignment' behavior).")
                print("Exiting program.")
                exit()

    def _log_exception(self, context, exc) -> None:
        """Print detailed exception info that is useful for Selenium debugging."""
        print(f"[Error] {context}")
        print(f"        Type: {type(exc).__name__}")
        print(f"        Message: {exc}")

        selenium_msg = getattr(exc, "msg", None)
        if selenium_msg and selenium_msg != str(exc):
            print(f"        Selenium message: {selenium_msg}")

        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        print("        Traceback:")
        for line in tb.rstrip().splitlines():
            print(f"          {line}")

    def _find_course_and_redirect(self) -> bool:
        navigated = False
        course_code = self.config.get('course_code', '')
        course_name = self.config['course_name']
        sections = self.config.get('sections')
        section = None
        if len(sections) == 1:
            section = sections[0]
        if len(sections) > 1:
            section = sections[self.config.get('actual_section_index', 0)]

        try:
            cards = find_in_shadow(self.driver, "d2l-card", multiple=True)
            print(f"Found {len(cards)} d2l-card elements.")
            matched_card = None
            
            if course_code:
                if section:
                    print(f"Appending section '{section}' to course code '{course_code}' for searching...")
                    course_code = course_code + '_' + str(section)
                print(f"Looking for course card with code '{course_code}' in the text attributes...")
                matched_card = search_text_in_element_list(cards, course_code)
            
            if not matched_card and course_name:
                print(f"Looking for course card with name '{course_name}' in the text attributes...")
                matched_card = search_text_in_element_list(cards, course_name)

            if not matched_card:
                raise Exception(f"No course card found containing code '{course_code}' or name '{course_name}'.")

            # Try to navigate by href
            href = matched_card.get_attribute("href")
            if href:
                # href may be relative (e.g. /d2l/home/426036)
                if href.startswith("/"):
                    href = BASE_URL + href
                print(f"Found course card. Navigating to {href}")
                self.driver.get(href)
                navigated = True
            else:
                print("Matched card found but has no href. Trying JS click...")
                self.driver.execute_script("arguments[0].click();", matched_card)
                navigated = True
        except Exception as e:
            self._log_exception(
                f"Could not find d2l-card with code '{course_code}'",
                e,
            )
        finally:
            return navigated

    def _navigate_to_grades(self)-> None:
        print("Navigating to Grades section...")
        try:
            grades_link = self.wait.until(EC.presence_of_element_located(
                (By.PARTIAL_LINK_TEXT, "Calificaciones")
            ))
            self.driver.execute_script("arguments[0].click();", grades_link)
        except Exception as e:
            self._log_exception("Could not click Grades/Calificaciones automatically", e)
            input("Please navigate to the Grades section manually and press Enter...")

    def _login_and_navigate(self):
        print(f"Navigating to {BASE_URL}")
        self.driver.get(BASE_URL)
        
        print("Waiting for you to log in manually...")
        input("Press Enter here in the terminal AFTER you have successfully logged in...")
        
        navigated = self._find_course_and_redirect()

        if not navigated:
            print(f"Could not automatically navigate to the course.")
            print("Please navigate into the course manually.")
            input("Press Enter in the terminal AFTER you have opened the course page...")

        self._navigate_to_grades()

    def wait_and_rename_download(self, activity_folder, original_filename, target_filename, timeout=45):
        """
        Waits for a file download to complete and renames it.
        """
        start_time = time.time()
        original_path = None
        if original_filename:
            # Clean up whitespace and newlines
            clean_orig = " ".join(original_filename.strip().replace("\n", " ").replace("\r", " ").split())
            original_path = os.path.join(activity_folder, clean_orig)
            
        print(f"    Waiting for download of {original_filename or 'file'} (timeout={timeout}s)...")
        
        while time.time() - start_time < timeout:
            # Check for active downloads (.crdownload files)
            files = os.listdir(activity_folder)
            crdownloads = [f for f in files if f.endswith('.crdownload')]
            if crdownloads:
                # is still downloading waittttt (you should get better internet haha)
                time.sleep(2)
                continue
                
            if original_path:
                # Find matching file case-insensitively with normalized spaces
                found_file = None
                for f in files:
                    f_clean = " ".join(f.strip().replace("\n", " ").replace("\r", " ").split())
                    if f_clean.lower() == clean_orig.lower():
                        found_file = f
                        break
                        
                if found_file:
                    time.sleep(1) # Extra buffer
                    src = os.path.join(activity_folder, found_file)
                    dst = os.path.join(activity_folder, target_filename)
                    try:
                        if os.path.exists(dst):
                            os.remove(dst)
                        os.rename(src, dst)
                        print(f"      [Success] Saved: {target_filename}")
                        return True
                    except Exception as e:
                        print(f"      [Error] Could not rename '{found_file}' to '{target_filename}': {e}")
                        return False
            else:
                # If we don't know the exact filename, find any file that is not our targets or crdownload
                non_targets = [f for f in files if not f.endswith('.crdownload') and not f.startswith('mejor-') and not f.startswith('peor-') and not f.startswith('Seguimiento_')]
                if non_targets:
                    time.sleep(1)
                    found_file = non_targets[0]
                    src = os.path.join(activity_folder, found_file)
                    dst = os.path.join(activity_folder, target_filename)
                    try:
                        if os.path.exists(dst):
                            os.remove(dst)
                        os.rename(src, dst)
                        print(f"      [Success] Saved: {target_filename} (detected file: {found_file})")
                        return True
                    except Exception as e:
                        print(f"      [Error] Could not rename '{found_file}' to '{target_filename}': {e}")
                        return False
            time.sleep(1)
            
        print(f"    [Warning] Download timed out or file not found for {original_filename or 'file'}")
        return False

    def _get_student_row(self, student_name):
        """
        Locates the student's row in the grades table.
        """
        student_row = None
        try:
            try:
                table = self.driver.find_element(By.ID, "z_bk")
            except Exception:
                table = self.driver.find_element(By.CSS_SELECTOR, "table.d2l-grid")

            all_rows = table.find_elements(By.TAG_NAME, "tr")
            for row in all_rows:
                try:
                    name_links = row.find_elements(By.XPATH, './/a[contains(@onclick, "gotoGradeUser")]')
                    if name_links and name_links[0].text.strip() == student_name:
                        student_row = row
                        break
                    # Fallback: loose text match on any cell text
                    if student_name in row.text:
                        student_row = row
                except Exception:
                    continue
        except Exception as e:
            print(f"    [Error] Could not locate grades table or student row for '{student_name}': {e}")

        return student_row
        
    def _get_submission_link_from_row(self, student_row, col_idx, activity_type="assignment"):
        # 2. Get cells and find the correct col cell
        try:
            cells = student_row.find_elements(By.XPATH, './td | ./th')
            if col_idx >= len(cells):
                print(f"    [Error] Column index {col_idx} out of range for cells (len={len(cells)})")
                return { "error": f"Column index {col_idx} out of range for cells (len={len(cells)})" }
            cell = cells[col_idx]
        except Exception as e:
            print(f"    [Error] Failed to get cells for student row: {e}")
            return { "error": f"Failed to get cells for student row: {e}" }

        # 3. Look for the submission link in the cell.
        # Assignment cells expose GetAssignmentLocation..., quiz cells expose QuizMarkNewTab(...).
        onclick_marker = "GetAssignmentLocation" if activity_type == "assignment" else "QuizMarkNewTab"
        try:
            submission_links = cell.find_elements(By.XPATH, f'.//a[contains(@onclick, "{onclick_marker}")]')
            if not submission_links:
                print(f"    [Info] No submissions link in the cell (student might not have submitted).")
                return { "error": "No submission link (student might not have submitted)" }
            link = submission_links[0]
        except Exception as e:
            print(f"    [Error] Error searching for submission link: {e}")
            return { "error": f"Error searching for submission link: {e}" }
        
        return {"link": link }

    def _find_submission_link_with_fallback(self, student, activity_name, activity_config, activity_type):
        """
        Locates the submission/quiz link for the student's row, falling back to
        the student's group members (per activity_config['groupName']) if the
        student themself has no link. Returns the link element, or None if not
        found (logging the appropriate reason to the 'errors' sheet in that case).
        """
        student_name = student['name']
        col_idx = student['col_idx']

        student_row = self._get_student_row(student_name)
        if not student_row:
            print(f"    [Error] Could not find row for student '{student_name}'.")
            append_array_to_table(self.workbook, "errors", [activity_name, "Student row not found", student_name])
            return None

        sub_link = self._get_submission_link_from_row(student_row, col_idx, activity_type)
        if sub_link.get("error") is None:
            return sub_link.get("link")

        print(f"    [Error] Submission link not found for student '{student_name}'.")
        if activity_config.get("groupName") is None:
            append_array_to_table(self.workbook, "errors", [activity_name, "No submission link (student might not have submitted)", student_name])
            return None

        activity_group_name = activity_config["groupName"]
        group_members = None
        group_name = None
        for group in self.groups_config.get(activity_group_name, []):
            if student_name in self.groups_config[activity_group_name][group]:
                group_members = self.groups_config[activity_group_name][group]
                group_name = group
                break
        if group_members is None:
            append_array_to_table(self.workbook, "errors", [activity_name, "No submission link (student might not have submitted). And the student does not belong to any group.", student_name])
            return None

        for member in group_members:
            if member == student_name:
                continue
            member_row = self._get_student_row(member)
            if not member_row:
                print(f"    [Error] Could not find row for group member '{member}'.")
                continue
            member_sub_link = self._get_submission_link_from_row(member_row, col_idx, activity_type)
            if member_sub_link.get("error") is not None:
                continue
            link = member_sub_link.get("link")
            if link is not None:
                print(f"    [Info] Found submission link from group member '{member}'.")
                return link

        print(f"    [Error] No submission link found for any group member of '{student_name}'.")
        append_array_to_table(self.workbook, "errors", [activity_name, "No submission link (student might not have submitted). And no group member has a submission link. group: " + group_name, student_name])
        return None

    def _open_link_in_new_tab(self, link):
        """
        Scrolls to and JS-clicks the link (bypassing sticky header interception),
        then waits for it to open in a new tab/window.
        Returns (main_window, opened_tab) where opened_tab indicates whether a
        new tab/window was actually opened and the driver switched into it.
        """
        main_window = self.driver.current_window_handle
        handles_before = self.driver.window_handles

        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
        time.sleep(0.5)
        self.driver.execute_script("arguments[0].click();", link)
        time.sleep(3)  # Wait for new tab / page to load

        handles_after = self.driver.window_handles
        opened_tab = False
        if len(handles_after) > len(handles_before):
            new_window = [w for w in handles_after if w not in handles_before][0]
            self.driver.switch_to.window(new_window)
            opened_tab = True

        return main_window, opened_tab

    def _close_tab_and_return(self, main_window, opened_tab):
        if opened_tab:
            self.driver.close()
            self.driver.switch_to.window(main_window)
        else:
            self.driver.back()
        # Wait a bit for the grades page to be fully interactive again
        time.sleep(2)

    def _recover_main_window(self, main_window):
        # Attempt to recover by closing the tab if we are not in the main window
        try:
            if self.driver.current_window_handle != main_window:
                self.driver.close()
                self.driver.switch_to.window(main_window)
        except Exception:
            pass

    def download_student_submissions(self, student, activity_name, activity_folder, activity_config):
        """
        Locates the student's submission cell, clicks it, and downloads files on the submission page.
        """
        student_name = student['name']
        print(f"  Student: {student_name} ({student['type'].upper()})")

        link = self._find_submission_link_with_fallback(student, activity_name, activity_config, "assignment")
        if link is None:
            return

        main_window, opened_tab = self._open_link_in_new_tab(link)

        try:
            # Set Chrome's download path BEFORE clicking the button
            self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': activity_folder
            })

            download_triggered = False

            # Try the "Descargar todos los archivos" button first (Consistent Evaluation UI)
            try:
                page_btts = find_in_shadow(self.driver, "d2l-button-subtle", multiple=True)
                download_all_btn = search_element_by_id(page_btts, "download-all-button")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_all_btn)
                time.sleep(0.5)
                # The inner <button> inside the shadow root handles the click
                self.driver.execute_script("arguments[0].click();", download_all_btn)
                print("    Clicked 'Descargar todos los archivos' button.")
                download_triggered = True
            except Exception as e:
                print(f"    'Descargar todos los archivos' button not found ({e}).")
                append_array_to_table(self.workbook, "errors", [activity_name, "Error downloading all files of the activity for the student.", student_name])

            if not download_triggered:
                print("No download method worked for this student.")
            else:
                # Build the target ZIP filename for renaming
                surnames = extract_surnames(student_name)
                target_name = f"{student['type']}-{surnames}.zip"
                self.wait_and_rename_download(activity_folder, None, target_name)

            self._close_tab_and_return(main_window, opened_tab)
        except Exception as e:
            print(f"    [Error] Exception during student download: {e}")
            self._recover_main_window(main_window)

    def download_student_quiz_pdf(self, student, activity_name, activity_folder, activity_config):
        """
        Locates the student's quiz cell and opens the review page for the most
        recent attempt (D2L's generated link already defaults to
        selectedItem=mostRecent), then saves the rendered page as a PDF.
        """
        student_name = student['name']
        print(f"  Student: {student_name} ({student['type'].upper()})")

        link = self._find_submission_link_with_fallback(student, activity_name, activity_config, "quiz")
        if link is None:
            return

        main_window, opened_tab = self._open_link_in_new_tab(link)

        try:
            # The quiz review page is a d2l-consistent-evaluation shadow-DOM SPA;
            # wait for it to mount before trying to print its rendered content.
            shell = find_in_shadow(self.driver, "d2l-consistent-evaluation", timeout=15)
            if shell is None:
                print(f"    [Error] Quiz review page did not load for student '{student_name}'.")
                append_array_to_table(self.workbook, "errors", [activity_name, "Quiz review page did not load", student_name])
                self._close_tab_and_return(main_window, opened_tab)
                return

            time.sleep(6)  # Let the quiz SPA finish rendering questions before printing

            print_options = PrintOptions()
            print_options.background = True
            pdf_bytes = base64.b64decode(self.driver.print_page(print_options))

            if len(pdf_bytes) < 5000:
                print(f"    [Warning] Generated quiz PDF looks suspiciously small ({len(pdf_bytes)} bytes); review manually.")
                append_array_to_table(self.workbook, "errors", [activity_name, "Quiz PDF looks suspiciously small, review manually", student_name])

            surnames = extract_surnames(student_name)
            target_name = f"{student['type']}-{surnames}.pdf"
            target_path = os.path.join(activity_folder, target_name)
            with open(target_path, "wb") as f:
                f.write(pdf_bytes)
            print(f"      [Success] Saved: {target_name}")

            self._close_tab_and_return(main_window, opened_tab)
        except Exception as e:
            print(f"    [Error] Exception while printing quiz PDF: {e}")
            append_array_to_table(self.workbook, "errors", [activity_name, "Error rendering/printing quiz PDF for the student.", student_name])
            self._recover_main_window(main_window)

    def download_student_evidence(self, student, activity_name, activity_folder, activity_config):
        """Dispatches to the assignment or quiz download path based on activity_config['type']."""
        activity_type = activity_config.get("type") or "assignment"
        if activity_type == "quiz":
            self.download_student_quiz_pdf(student, activity_name, activity_folder, activity_config)
        else:
            self.download_student_submissions(student, activity_name, activity_folder, activity_config)

    def run(self):
        try:
            self._login_and_navigate()
            
            sections = self.config['sections']
            # If no sections were provided, run a single pass without a section context.
            # Otherwise iterate over each section index.
            iterations = list(enumerate(sections)) if sections else [(None, None)]

            for idx, section in iterations:
                # For every iteration after the first, navigate back to the course
                # and then to the grades page for the new section.
                if idx is not None and idx > 0:
                    self.config['actual_section_index'] = idx
                    self.driver.get(BASE_URL)
                    self._find_course_and_redirect()
                    self._navigate_to_grades()

                # Extract grades table
                print("Extracting grades HTML...")
                html_content = self.driver.page_source
                
                print("Parsing grades...")
                activity_data = parse_grades_page(html_content, self.activities_config)
                
                if not activity_data:
                    print("No activities found or failed to parse for this section.")
                    continue

                # Collect all students from all activities
                all_students = [student for activity_name, students in activity_data.items() for student in students]
                
                print("Selecting 3 students for abet following...")
                abet_students = select_students_for_abet(all_students)
                
                print("\n--- Student Selection ---")
                selected_students_by_activity = {}
                for activity_name, students in activity_data.items():
                    selected = select_students_for_activity(students, abet_students)
                    selected_students_by_activity[activity_name] = selected
                    print(f"\nActivity: {activity_name}")
                    # add selected students to the results workbook
                    selected_students_list = [[activity_name, item.get("type"), item.get("name")] for item in selected]
                    append_array_to_table(self.workbook, "selectedStudents", selected_students_list)
                    for s in selected:
                        print(f"  [{s['type'].upper()}] {s['name']} (Grade: {s['grade']})")
                        
                print("\n--- Starting Downloads ---")
                for activity_name, students in selected_students_by_activity.items():
                    print(f"\nProcessing Activity: {activity_name}")
                    
                    section_folder_name = f"section{section}" if section is not None else "section_all"
                    activity_folder = os.path.join(
                        self.config['root_folder'],
                        self.config['course_name'],
                        section_folder_name,
                        activity_name
                    )
                    ensure_dir(activity_folder)
                    print(f"Destination: {activity_folder}")
                    activity_config = next((a for a in self.activities_config if a['name'] == activity_name), None)
                    
                    for student in students:
                        self.download_student_evidence(student, activity_name, activity_folder, activity_config)
        finally:
            print("Saving results workbook in given root folder...")
            filename = f"results_{self.config['course_code']}.xlsx" if self.config.get('course_code') else "results.xlsx"
            self.workbook.save(os.path.join(self.config['root_folder'], filename))

            print("Scraping finished. Closing browser in 5 seconds...")
            time.sleep(5)
            self.driver.quit()

if __name__ == "__main__":
    scraper = D2LScraper()
    scraper.run()
