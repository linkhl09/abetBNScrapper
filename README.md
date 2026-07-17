# D2L Brightspace Gradebook Scraper & Downloader for ABET accreditation

This automation tool is designed for ABET accreditation. It automates the extraction of student gradebooks and assignment submissions from the D2L Brightspace platform (`https://bloqueneon.uniandes.edu.co/`).

For each configured activity (e.g., assignments, projects, workshops), the script identifies:

- The **mejor** student submission (highest grade)
- The **peor** student submission (lowest grade)

It also randomly selects three additional students that will be used for ABET following and will be in all activities.

It then programmatically navigates the D2L interface to download, organize, and rename these submissions into structured directories.

---

## Setup & Prerequisites

### 1. Requirements

Ensure you have Python 3.8+ installed along with Google Chrome.

Install the required packages in your virtual environment:

```bash
# Create a virtual environment
python -m venv .venv

# Activate your venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Activities (`activities.json`)

Create `activities.json` in the same directory (you can also find the template in the repository). This file dictates which assignments/grade columns to target. You can specify aliases if column names vary or contain acronyms (for example `"P1 - DF"` for `"Documento Proyecto 1"`):

```json
[
  {
    "name": "Documento Proyecto 1",
    "aliases": ["P1 - DF"]
  },
  {
    "name": "Taller Prompting",
    "aliases": ["Taller de Prompting"]
  }
]
```

_If `activities.json` is not found, the script will prompt you in the terminal to enter activities and their aliases manually._

#### Quiz-type activities

Some activities are D2L "Cuestionarios" (quizzes) filled in directly on the platform instead of file uploads. Mark these with `"type": "quiz"`:

```json
{
  "name": "Cuestionario 1",
  "aliases": ["Quiz 1"],
  "type": "quiz"
}
```

Omit `type` (or set it to `"assignment"`) for regular file-upload activities — this is the default and requires no changes to existing `activities.json` files. For quiz activities, the tool opens each selected student's most recent quiz attempt and saves the rendered page as a PDF (`<type>-<Surnames>.pdf`) instead of downloading a `.zip` of submitted files. This can only be configured through `activities.json`, not from the terminal prompts.

#### Standalone quiz activities (not on the Grades page)

Some quizzes (e.g. practice/ungraded ones) are never linked to a Grades-page column, so the tool can't find them through the grades table at all. Mark these with `"type": "standalone_quiz"` instead:

```json
{
  "name": "Quiz Practica 1",
  "aliases": ["Práctica Quiz 1"],
  "type": "standalone_quiz"
}
```

The tool reaches these through D2L's "Cuestionarios" (Quizzes) course tool instead of "Calificaciones", using the quiz's own grading list to pick the best/worst/Seguimiento students and to save each one's last attempt as a PDF, same naming convention as regular quiz activities. `groupName` is not supported for `standalone_quiz` activities — the program will exit with an error if you combine them. If the course has a very long quiz list, only quizzes visible without paging through the list can currently be found; pagination is not handled yet.

If you have configured in brightspace activities in groups, you can also specify which activities belong to a group in the `activities.json` file. For example if you have a group category called "ExpoaAndes" you can configure the activities like this:

```json
[
  {
    "name": "Taller 1",
    "aliases": ["T1", "Entrega Taller 1", "Entrega T1"]
  },
  {
    "name": "ExpoAndes Documento",
    "groupName": "ExpoAndes"
  }
]
```

This option cannot be configured from the terminal as it requires that you download a file on brightspace. You can go to the "grades" page and select the "Export Grades" button. Exclude all the grades and select the name and surname of the students checkboxes. Also select the checkbox that indicates "Group membership" so it downloads the groups of each student.

Be sure to name the file as:  `Groups_<CourseCode>.xlsx` for example, the course "Introduccion a Ingenieria de Sistemas" with code ISIS1001, should be named `Groups_ISIS1001.xlsx`.


---

## How to Use the Program

### Step 1: Run the Script

Activate your virtual environment (if you haven't already) and start the scraper:

```bash
python scraper.py
```

### Step 2: Configure Settings in the Terminal

The script will prompt you for the following inputs:

1. **Output root directory path:** The directory where downloaded files should be saved (default: `./downloads`).
2. **Course name:** The name of the course in Brightspace (default: `course`). This is used to locate the course link on your homepage and name the main output folder.
3. **Sections:** Enter one or more section numbers separated by commas (e.g., `1, 2`) or press **Enter** to skip filtering and scrape the current gradebook view.

```
Important Note:
Currently, if you want to download from various sections in a unified class, the scraper does not support it yet. You can skip section selection and it will execute in the current grades view (where you can manually filter the section you want, or extract for everyone in general).
```

### Step 3: Manual Authentication

1. A Chrome browser window will open and navigate to the UniAndes login page.
2. Log in manually.
3. Once you have logged in and see the homepage, return to your terminal and **press Enter** to resume the script.

### Step 4: Section Filtering & Downloading

The script will automatically navigate to your course page and enter the **Grades (Calificaciones)** section.

For each section you specified the script will take over, select the target students, open each submission page in a new tab, download their files directly to the proper folder, rename them, and close the tabs.

---

## Output Folder Structure

Downloads are automatically organized into folders structured as follows:

```text
<root_folder>/
└── <course_name>/
    ├── section1/
    │   ├── <activity_name_A>/
    │   │   ├── mejor-LastName_FirstName.pdf
    │   │   ├── peor-LastName_FirstName.zip
    │   │   ├── random-LastName_FirstName_1.pdf
    │   │   ├── random-LastName_FirstName_2.pdf
    │   │   └── random-LastName_FirstName_3.pdf
    │   └── <activity_name_B>/
    │       └── ...
    └── section2/
        └── ...
```

_Note: If multiple files are uploaded for a single submission, they will be saved with a `_1`, `_2` index suffix._

_Note: The file extension depends on the activity's `type`: regular activities produce `.zip` files with the student's uploaded submission, while `"type": "quiz"` activities produce a `.pdf` of the student's most recent quiz attempt instead._

## About the groups

When the students use groups, only one sends the file to the course and it could be a different student than the selected ones. When this happens the program will check if it's a group activity and if it is, search for the files in the other group members activities until it's found.
If none of the students have submissions, it will log the specific case. 

## Check the results
To check the results, navigate to your output folder. There you can find the [folder structure](#output-folder-structure) and an Excel with: the selected students, and the errors found during the execution that you should check manually, some examples:

- Could not download a file for a student.
- A student didn't submit anything.
- The group of the student didn't submit anything.
- The quiz review page did not load, or the generated PDF looks suspiciously small (for `"type": "quiz"` or `"standalone_quiz"` activities) — check whether the student actually attempted the quiz.
- The quiz wasn't found in the Cuestionarios list, or a selected student never attempted a `"standalone_quiz"` activity.
- "manually uploaded grade, please submit the evidence manually before uploading to Calis" — a selected student has a grade for a `"standalone_quiz"` activity but no actual attempt (the grade was entered/overridden by hand in D2L). You'll need to track down and attach that student's evidence manually.

The errors regarding "Could not download a file for a student" are usually for large files that require more time for the download. If you want, you can increment the timeout of the function `wait_and_rename_download` which is 45 seconds by default. 