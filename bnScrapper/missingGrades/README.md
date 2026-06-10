# Brightspace Missing Grades Scraper & Summarizer

This toolset is designed to help instructors quickly identify student submissions that have been submitted but not yet evaluated in Brightspace (D2L). It consists of two parts:
1. **A JavaScript Scraper (`scraper.js` / `index.html`)** to extract submission data directly from the Brightspace interface.
2. **A Python Script (`get_unevaluated.py`)** to process the exported data and generate a consolidated report of missing grades.

---

## 1. Using the JavaScript Scraper

The scraper is a console-based script that works across multiple pages of a Brightspace assignment submission view without requiring any browser extensions.

### Steps to Extract Data:
1. Navigate to the **Folder Submissions** page of an assignment in Brightspace. Make sure the table showing students and their evaluation status is visible.
2. Open your browser's **Developer Tools** (usually `F12` or `Ctrl + Shift + J` / `Cmd + Option + J`) and go to the **Console** tab.
3. Open `index.html` locally to easily copy the scraper script, or directly copy the contents of `scraper.js`.
4. Paste the script into the Console and press **Enter**.
5. **Multi-page assignments:** 
   - The script will automatically scan the first page, save the results in the session memory, and switch to the next page.
   - Wait for the second page to load completely.
   - Click back into the Console, press the **Up Arrow (↑)** to bring up the script again, and press **Enter**.
   - Repeat this until you reach the final page.
6. Once the last page is scanned, the script will consolidate all the data and automatically download a CSV file named after the assignment (e.g., `Assignment_1.csv`).

*Tip: You can use this scraper on as many assignments as you need. Just repeat the process for each assignment folder to get a separate CSV file for each.*

---

## 2. Using the Python Script

After you have downloaded the CSV files for your assignments using the scraper, you can use the Python script to find exactly who has submitted work that is missing an evaluation.

### Prerequisites:
- Python 3.x installed on your computer.

### Steps to Generate the Summary:
1. Create a folder (by default named `grades` inside this directory) and move all the downloaded CSV files into it.
2. Open a terminal or command prompt in the directory containing `get_unevaluated.py`.
3. Run the script using the following command:

   ```bash
   python get_unevaluated.py
   ```

### Command Line Arguments:
You can customize the input folder and the output file name:

- **Input Folder:** Specify a different folder containing the CSVs.
  ```bash
  python get_unevaluated.py my_csv_folder
  ```
- **Output File:** Specify a custom name for the summary CSV using the `-o` or `--output` flag.
  ```bash
  python get_unevaluated.py grades -o report.csv
  ```

### Output:
The script will generate a summary CSV file (default: `unevaluated_summary.csv`). This file contains two columns:
- **Activity**: The name of the assignment (derived from the CSV filename).
- **Name**: The name of the student or group who has a submission that needs to be evaluated.
