import os
import json
import random
import re

from selenium.webdriver.support.ui import WebDriverWait

def prompt_user_config() -> dict:
    """Prompts the user for initial configuration details."""
    print("=== D2L Brightspace Scraper ===")
    root_folder = input("Enter output root directory path (e.g., /home/user/downloads/abet): ").strip()
    if not root_folder:
        root_folder = os.path.join(os.getcwd(), "downloads")
        print(f"No path provided, using default: {root_folder}")
        
    course_name = input("Enter course name for output folder (default: 'course'): ").strip()
    if not course_name:
        course_name = "course"

    course_code = input("Enter the course code (e.g., ISIS1001): ").strip()

    sections_input = input("Enter section(s) separated by commas (e.g., 1, 2, 3), or press Enter to skip: ").strip()
    sections = [s.strip() for s in sections_input.split(',')] if sections_input else []

    return {
        "root_folder": root_folder,
        "course_name": course_name,
        "course_code": course_code,
        "sections": sections,
        "actual_section_index": 0 if len(sections) > 0 else None
    }

def load_activities(json_path="activities.json") -> list[dict]:
    """Loads activities from JSON or prompts user if missing."""
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        activities = []
        print(f"Could not find '{json_path}'. Let's add activities manually.")
        while True:
            activity_name = input("Enter activity name (or leave empty to finish): ").strip()
            if not activity_name:
                break
            aliases_input = input(f"Enter aliases for '{activity_name}' separated by comma (optional): ").strip()
            aliases = [a.strip() for a in aliases_input.split(',')] if aliases_input else []
            activities.append({"name": activity_name, "aliases": aliases})
        return activities

def sanitize_filename(filename):
    """Removes invalid characters from a string to make it safe for filenames."""
    # Replace invalid chars with underscore
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # Remove extra spaces
    return " ".join(sanitized.split())

def ensure_dir(path):
    """Ensures a directory exists."""
    if not os.path.exists(path):
        os.makedirs(path)

def select_students_for_abet(student_list) -> list[dict]:
    """
    Given a list of student dicts containing 'name', 'id'
    returns a list with 3 random students. This should be used for all the activities. 
    """
    non_repeated_students =list( {s['name']: s for s in student_list}.values())  # Remove duplicates by ID
    # Select up to 3 randoms
    num_random = min(3, len(non_repeated_students))
    random_students = random.sample(non_repeated_students, num_random)
    for index, rs in enumerate(random_students):
        rs['type'] = f"Seguimiento_{index + 1}"

    return random_students

def select_students_for_activity(student_list, abet_following_students):
    """
    Given a list of student dicts containing 'name', 'id', 'grade' for a specific activity,
    returns the best, worst and the 3 students marked for abet following.
    The best and worst could include the abet following students if they are among them, it will add the duplicates.

    Assumes grades are floats. If grades are None or missing, handles gracefully.
    """
    valid_students = [s for s in student_list if s.get('grade') is not None]
    if not valid_students:
        return []
    
    # Sort by grade (highest first)
    valid_students.sort(key=lambda x: x['grade'], reverse=True)
    
    best = valid_students[0]
    best['type'] = 'mejor'
    
    worst = valid_students[-1]
    worst['type'] = 'peor'

    activity_col_idx = student_list[0]['col_idx']  # Assuming all students have the same col_idx for this activity
    
    updated_abet_students = []
    for student in abet_following_students:
        student_copy = student.copy()
        student_copy["col_idx"] = activity_col_idx
        updated_abet_students.append(student_copy)

    selected = [best, worst] + updated_abet_students
    
    return selected

def extract_surnames(full_name):
    """Attempts to extract surnames assuming 'LastName, FirstName' format."""
    parts = full_name.split(',')
    if len(parts) > 1:
        # e.g. "Cardenas Nieto, Samuel Jhoel" -> "Cardenas Nieto"
        return sanitize_filename(parts[0].strip().replace(" ", "_"))
    
    # Fallback if no comma
    parts = full_name.split()
    if len(parts) >= 2:
        return sanitize_filename(parts[-1])
    return sanitize_filename(full_name)


def find_in_shadow(driver, selectors, timeout=10, multiple=False):
    """
    Busca elementos dentro de todos los open shadow roots de la página.

    Acepta un selector CSS simple (`"d2l-card"`) para búsqueda profunda global,
    o una lista de selectores para convertirla en una ruta CSS descendente.
    """

    selector = " ".join(selectors) if isinstance(selectors, (list, tuple)) else selectors
    wait = WebDriverWait(driver, timeout)

    def _deep_query(_driver):
        return _driver.execute_script(
            """
            const selector = arguments[0];
            const results = [];
            const seen = new Set();

            function collect(root) {
                if (!root || !root.querySelectorAll) {
                    return;
                }

                for (const match of root.querySelectorAll(selector)) {
                    if (!seen.has(match)) {
                        seen.add(match);
                        results.push(match);
                    }
                }

                for (const element of root.querySelectorAll('*')) {
                    if (element.shadowRoot) {
                        collect(element.shadowRoot);
                    }
                }
            }

            collect(document);
            return results;
            """,
            selector,
        )

    try:
        matches = wait.until(lambda current_driver: _deep_query(current_driver) or False)
        return matches if multiple else matches[0]
    except Exception as e:
        print(f"Error finding element with selector '{selector}': {e}")
        return [] if multiple else None
    
def search_text_in_element_list(element_list, search_term):
    """Find an element whose visible text contains `search_term` (case-insensitive)."""
    matched_element = None
    for element in element_list:
        element_text = (element.get_attribute("text") or element.text or "").strip()
        if search_term.lower() in element_text.lower():
            matched_element = element
            print(f"Matched element text: {element_text}")
            break

    return matched_element

def search_element_by_id(elements, target_id):
    """Find an element in `elements` with the given DOM id."""
    for element in elements:
        if element.get_attribute("id") == target_id:
            return element
    return None