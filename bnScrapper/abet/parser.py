from bs4 import BeautifulSoup
import re

def parse_grades_page(html_content, activities_config):
    """
    Parses the grades.html page source to extract student grades for configured activities.
    Returns a dictionary of activities mapping to a list of student dictionaries.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    table = soup.find('table', id='z_bk') or soup.find('table', class_=lambda x: x and 'd2l-grid' in x)
    if not table:
        print("Could not find the grades table.")
        return {}
        
    header_rows = table.find_all('tr', class_=lambda x: x and 'd_gh' in x)
    
    if not header_rows:
        print("Could not find the grades table headers.")
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
