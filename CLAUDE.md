# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Selenium-based scraper that automates downloading student assignment submissions and quiz evidence from D2L Brightspace (`https://bloqueneon.uniandes.edu.co/`) for ABET accreditation evidence. For each configured activity it identifies the best (`mejor`) and worst (`peor`) graded submissions plus 3 randomly-selected students tracked across all activities (`Seguimiento_1/2/3`), downloads their evidence, renames it, and organizes it into folders. It also produces an Excel report of selected students and any download errors.

Activities are either file-upload assignments (default) or D2L "Cuestionarios" (quizzes, `"type": "quiz"` in `activities.json`) — for the latter, there's no file to download, so the tool opens the student's most recent quiz attempt and saves the rendered page as a PDF instead.

There are no automated tests, build step, or linter configured in this repo.

## Running

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scraper.py
```

Requires Google Chrome installed locally (Selenium drives a real Chrome window; login to Brightspace is manual — the script pauses with `input()` prompts for the user to log in and to navigate to the course if auto-navigation fails).

The script is interactive: it prompts in the terminal for the output root folder, course name/code, and section numbers, then opens Chrome, waits for manual login, navigates to the course's Grades page, scrapes it, and downloads submissions.

### Configuration files (not committed, created by the user at repo root)

- `activities.json` — list of `{name, aliases, groupName?, type?}` describing which gradebook columns to target (see `activitiesExample.json` for shape). `type` is `"assignment"` (default, omit the field) or `"quiz"`. If missing, the script prompts for activities interactively at startup — group-based and quiz-type activities can only be configured via this file, not interactively.
- `Groups_<course_code>.xlsx` — required only when any activity has a `groupName`. Must be exported from Brightspace's "Export Grades" with the "Group membership" and name checkboxes selected. Used to fall back to a group member's submission when the selected student didn't submit individually.

## Architecture

Five modules, each with a single responsibility, wired together by `D2LScraper` in `scraper.py`:

- **`scraper.py`** — `D2LScraper` class owns the Selenium `webdriver` session and the whole run lifecycle (`run()`): login → per-section loop → scrape grades page HTML → parse → select students → download. `download_student_evidence` dispatches per-activity on `activity_config["type"]`: `download_student_submissions` (assignments) redirects Chrome's native download behavior per-tab via `Page.setDownloadBehavior` CDP command pointed at the activity's destination folder, then `wait_and_rename_download` polls the folder for `.crdownload` completion and renames the result to `<type>-<Surnames>.zip`; `download_student_quiz_pdf` (quizzes) instead waits for the quiz review SPA to render and calls Selenium's `print_page()` (CDP `Page.printToPDF`) to save `<type>-<Surnames>.pdf` directly, no download/rename needed. Both paths share `_find_submission_link_with_fallback` (row lookup + group fallback) and `_open_link_in_new_tab`/`_close_tab_and_return`/`_recover_main_window` (tab bookkeeping).
- **`parser.py`** — pure function `parse_grades_page(html, activities_config)` takes the raw grades page HTML (BeautifulSoup) and returns `{activity_name: [student_dict, ...]}`. It reconstructs multi-row `<th>` column headers (Brightspace grade columns often span two header rows with colspan/rowspan), matches column names against `activities_config` names/aliases, and extracts each student's name, id, numeric grade (`extract_numeric_grade`), and `col_idx` (position in the row — later used by `scraper.py` to re-locate the correct `<td>` when clicking through to a submission).
- **`utils.py`** — grab-bag of stateless, non-web helpers: interactive prompts (`prompt_user_config`, `load_activities`), student selection logic (`select_students_for_abet` picks 3 random unique students; `select_students_for_activity` picks best/worst by grade plus the abet-following students), and filename helpers (`sanitize_filename`, `extract_surnames` — expects `"LastName, FirstName"` format), `ensure_dir`.
- **`web_utils.py`** — generic Selenium/DOM helpers with no project-specific logic: `find_in_shadow` — a JS-injected recursive search through open shadow DOM trees, needed because Brightspace's UI is built with `d2l-*` custom elements (shadow DOM) that regular Selenium selectors can't pierce — plus `search_text_in_element_list` and `search_element_by_id`.
- **`excel_utils.py`** — thin `openpyxl` wrapper for building/appending to Excel tables (`create_workbook_with_sheet`, `add_sheet_with_table`, `append_array_to_table`) used for the results workbook (`results_<course_code>.xlsx`, saved to the root folder at the end of `run()` even on error via `finally`), plus `extract_student_groups` which parses a `Groups_<course_code>.xlsx` roster export into `{groupCategory: {groupName: [studentNames]}}`.

### Key data flow

`activities.json` config + scraped HTML → `parse_grades_page` → `{activity: [students]}` → `select_students_for_abet`/`select_students_for_activity` → per-student `download_student_evidence` → `download_student_submissions` or `download_student_quiz_pdf` depending on activity `type` (locates row by name, cell by `col_idx` via `_find_submission_link_with_fallback`, opens the link in a new tab via `_open_link_in_new_tab`, then either downloads+renames a file or renders+prints a PDF) → results appended to the in-memory `openpyxl` workbook → workbook saved once at the end of the run.

Assignment cells expose an `onclick` containing `GetAssignmentLocation...`; quiz cells expose `QuizMarkNewTab(quizId, userId)` instead — `_get_submission_link_from_row` picks the right xpath marker based on `activity_type`. The quiz link's target URL already includes `selectedItem=mostRecent` (set by D2L itself), so the "last attempt" is loaded by default with no need to touch the attempt-switcher dropdown on that page.

### Group fallback behavior

If a selected student has no submission/quiz link for a `groupName` activity, `_find_submission_link_with_fallback` looks up the student's group (from `self.groups_config`, populated by `extract_student_groups` in `D2LScraper._validate_groups_config`) and tries every other group member's row/column until it finds one with a link. If none of the group has submitted, it's logged to the `errors` sheet instead. This logic is type-agnostic (works the same for assignment and quiz links).

### Fragile points to be aware of when modifying

- Brightspace grades table lookup falls back between `#z_bk` and `table.d2l-grid` — both selector forms have been observed in the wild.
- `col_idx` from `parser.py` is reused later in `scraper.py` to index into `<td>`/`<th>` cells of a student's row — if the row structure differs from the header row (e.g. extra leading cells), indices will misalign.
- Download detection in `wait_and_rename_download` has two modes: match by cleaned/lowercased original filename, or (if filename unknown) grab the first file in the folder that isn't a `.crdownload` or an already-renamed target — the latter mode assumes only one download lands in that folder at a time.
- `download_student_quiz_pdf`'s wait for the quiz review page (a `<d2l-consistent-evaluation>` shadow-DOM SPA, same component family the assignment path pierces via `find_in_shadow` for the download button) uses a structural `find_in_shadow` gate plus a fixed `time.sleep(6)` heuristic for content to finish rendering before printing (raised from an initial `3`s after live testing caught a PDF printed before the page had loaded) — if generated PDFs still come out blank/partial on slower quizzes, increase the sleep further or add a scroll-to-bottom-then-top nudge before calling `print_page()`.
