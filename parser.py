from bs4 import BeautifulSoup
import re

def _find_grades_table(soup):
    """
    Finds the Brightspace grades table and its header rows.
    Returns (table, header_rows), or (None, []) if either can't be found.
    """
    table = soup.find('table', id='z_bk') or soup.find('table', class_=lambda x: x and 'd2l-grid' in x)
    if not table:
        print("Could not find the grades table.")
        return None, []

    header_rows = table.find_all('tr', class_=lambda x: x and 'd_gh' in x)
    if not header_rows:
        print("Could not find the grades table headers.")
        return None, []

    return table, header_rows


def _extract_student_name_and_id(cells):
    """
    Given a grades-table row's <th>/<td> cells, extracts the student's display
    name (2nd cell) and D2L userId (from the name link's onclick).
    """
    name_cell = cells[1]
    name_anchor = name_cell.find('a', onclick=re.compile(r'gotoGradeUser'))
    if not name_anchor:
        full_name = name_cell.get_text(strip=True).replace("Ver progreso de", "").strip()
    else:
        full_name = name_anchor.get_text(strip=True)

    student_id = "unknown"
    if name_anchor and 'onclick' in name_anchor.attrs:
        match = re.search(r'gotoGradeUserGroupSectionFilter\((\d+)', name_anchor['onclick'])
        if match:
            student_id = match.group(1)

    return full_name, student_id


def extract_course_roster(html_content):
    """
    Extracts every student's {name, id} from the Grades page, independent of
    which (if any) configured activity columns matched. Used as the pool for
    selecting the 3 random Seguimiento students even when a section has no
    Grades-column ("assignment"/"quiz") activities to draw a pool from otherwise.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    table, header_rows = _find_grades_table(soup)
    if not table:
        return []

    student_rows = [row for row in table.find_all('tr') if row not in header_rows]

    roster = []
    for row in student_rows:
        cells = row.find_all(['th', 'td'])
        if len(cells) < 2:
            continue
        full_name, student_id = _extract_student_name_and_id(cells)
        if full_name:
            roster.append({"name": full_name, "id": student_id})

    return roster


def parse_grades_page(html_content, activities_config):
    """
    Parses the grades.html page source to extract student grades for configured activities.
    Returns a dictionary of activities mapping to a list of student dictionaries.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    table, header_rows = _find_grades_table(soup)
    if not table:
        return {}

    # Reconstruct column names
    if len(header_rows) >= 2:
        row0 = header_rows[0].find_all(['th', 'td'])
        row1 = header_rows[1].find_all(['th', 'td'])
        N = sum(int(cell.get('colspan', 1)) for cell in row0)
        col_names = [None] * N
        row1_idx = 0
        current_col = 0
        
        for cell in row0:
            text = cell.get_text(strip=True)
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))
            
            if rowspan == 2:
                for c in range(colspan):
                    col_names[current_col + c] = text
                current_col += colspan
            else:
                for c in range(colspan):
                    r1_cell = row1[row1_idx]
                    r1_text = r1_cell.get_text(strip=True)
                    if text:
                        col_names[current_col + c] = f"{text} - {r1_text}"
                    else:
                        col_names[current_col + c] = r1_text
                    row1_idx += 1
                current_col += colspan
    else:
        # Single row header
        header_row = header_rows[0]
        headers = header_row.find_all(['th', 'td'])
        col_names = [th.get_text(strip=True) for th in headers]

    # Map reconstructed column names to activities_config
    activity_columns = {} # column_index -> activity_config
    for idx, col_name in enumerate(col_names):
        if not col_name:
            continue
        # Split by ' - ' and take the last part
        item_part = col_name.split(' - ')[-1].strip()
        
        for act in activities_config:
            names_to_check = [act['name']] + act.get('aliases', [])
            if any(name.lower() == item_part.lower() for name in names_to_check):
                activity_columns[idx] = act
                print(f"Found activity column for '{act['name']}' at index {idx} ('{col_name}')")
                break
                
    if not activity_columns:
        print("None of the configured activities were found in the headers.")
        return {}
        
    # 2. Extract Student Data
    activity_data = {act['name']: [] for act in activity_columns.values()}
    
    # I already have the rows of the table, I just need to filter out the header rows and process the rest
    student_rows = table.find_all('tr')
    student_rows = [row for row in student_rows if row not in header_rows]
    
    for row in student_rows:
        cells = row.find_all(['th', 'td'])
        if len(cells) < 2:
            continue

        full_name, student_id = _extract_student_name_and_id(cells)

        for col_idx, act in activity_columns.items():
            if col_idx < len(cells):
                cell = cells[col_idx]
                grade_text = cell.get_text(strip=True)
                grade_value = extract_numeric_grade(grade_text)
                
                assignment_anchor = cell.find('a', onclick=re.compile(r'GetAssignmentLocation'))
                folder_id = None
                if assignment_anchor and 'onclick' in assignment_anchor.attrs:
                    match = re.search(r'\.Call\((\d+)', assignment_anchor['onclick'])
                    if match:
                        folder_id = match.group(1)
                         
                activity_data[act['name']].append({
                    "name": full_name,
                    "id": student_id,
                    "grade_text": grade_text,
                    "grade": grade_value,
                    "folder_id": folder_id,
                    "col_idx": col_idx
                })

    return activity_data


def parse_quiz_grading_page(html_content):
    """
    Parses the 'Calificar cuestionario' > 'Usuarios' tab (quiz_mark_users.d2l)
    page source. Walks <tr> elements in document order, tracking the current
    student name from 'd_gg' header rows, and emits one student dict per
    'D2LGridSummaryRow_List' row (the student's official quiz score).

    Returns a list of student dicts: {name, id, grade_text, grade, col_idx}.
    - 'id' is the D2L userId, recovered from the summary row's
      actionParam='markoverall,0,<userId>' onclick — the same id later used
      by scraper.py to find that student's per-attempt "intento N" links.
    - 'col_idx' is always None (this page has no column concept); kept only
      so utils.select_students_for_activity (which reads
      student_list[0]['col_idx']) can be reused unmodified.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    students = []
    current_name = None

    for row in soup.find_all('tr'):
        row_classes = row.get('class') or []

        if 'd_gg' in row_classes:
            # Normal header row: <tr><td>checkbox</td><td width="100%">Name</td></tr>.
            # A student with zero attempts (e.g. a manually-entered/overridden
            # grade) has no checkbox to select an attempt with, so the row only
            # has ONE <td> (no width="100%") holding the name directly. Taking
            # the LAST <td> in the nested row handles both shapes.
            nested_row = row.find('tr')
            current_name = None
            if nested_row:
                tds = nested_row.find_all('td', recursive=False)
                if tds:
                    current_name = tds[-1].get_text(strip=True)
            continue

        if 'D2LGridSummaryRow_List' in row_classes:
            if current_name is None:
                continue

            overall_anchor = row.find('a', onclick=re.compile(r"actionParam='markoverall,"))
            user_id = "unknown"
            if overall_anchor and 'onclick' in overall_anchor.attrs:
                match = re.search(r"actionParam='markoverall,\d+,(\d+)'", overall_anchor['onclick'])
                if match:
                    user_id = match.group(1)

            strong_tag = row.find('strong')
            grade_text = strong_tag.get_text(strip=True) if strong_tag else ""
            grade_value = extract_numeric_grade(grade_text)

            students.append({
                "name": current_name,
                "id": user_id,
                "grade_text": grade_text,
                "grade": grade_value,
                "col_idx": None,
            })
            current_name = None

    return students


def extract_numeric_grade(grade_string):
    """
    Extracts the first number from a grade string like "4.32 / 5, 4.31" or "0* / 5"
    Returns a float or None.
    """
    if not grade_string or grade_string == "- / -, -":
        return None
    # Usually it's something like "4.32 / 5, ..."
    # Let's extract the part before the slash
    parts = grade_string.split('/')
    if parts:
        score_part = parts[0].replace('*', '').strip()
        try:
            return float(score_part)
        except ValueError:
            return None
    return None
