# CSV Aggregator & Comparison Tool

## Project Overview

The CSV Aggregator & Comparison Tool is a web application designed to help users analyze and compare data across multiple CSV files. Users can upload several CSV files, specify an operation column (e.g., a common ID or timestamp) and a numeric threshold. The application then processes these files by:
1.  Reading and parsing the CSVs, attempting to handle various delimiters and encodings.
2.  Validating the specified operation column for existence and numeric type.
3.  Comparing numeric columns (other than the operation column) between the first uploaded CSV (as a reference) and subsequent CSVs, based on aligned rows from the operation column.
4.  Calculating absolute differences for these numeric columns.
5.  Generating a downloadable Excel report that includes:
    *   A summary of the operations.
    *   Individual sheets for each uploaded CSV, with original data.
    *   Rows highlighted in the Excel sheets where the calculated differences for any compared column exceed the user-defined threshold.

## Features

*   **Multiple CSV File Upload:** Upload one or more CSV files for processing.
*   **Configurable Processing:**
    *   Specify an "Operation Column" used for joining/aligning data across files.
    *   Define a "Threshold Value" for highlighting significant differences.
*   **Automated CSV Parsing:** Attempts to auto-detect delimiters and handles common encodings (UTF-8, UTF-8-SIG, Latin-1).
*   **Column Comparison:** Compares numeric data columns between the first CSV and subsequent ones, row by row, based on the operation column.
*   **Difference Calculation:** Calculates absolute differences for the compared numeric columns.
*   **Excel Report Generation:** Produces a downloadable Excel (`.xlsx`) file.
    *   Includes a summary sheet with input parameters and overview.
    *   Contains individual sheets for each input CSV with its original data.
    *   Highlights rows in data sheets where calculated differences exceed the specified threshold.
*   **Unique Report Filenames:** Generated reports have timestamped unique filenames to prevent overwrites.
*   **Automatic Cleanup:** Uploaded CSV files are automatically deleted from the server after processing.

## Directory Structure

*   `backend/`: Contains the Python Flask backend application.
    *   `uploads/`: Temporary storage for uploaded CSV files (auto-cleaned).
    *   `processed/`: Storage for generated Excel reports.
    *   `tests/`: Unit tests for backend logic.
*   `frontend/`: Contains the TypeScript React frontend application.
    *   `src/components/`: UI components for file upload, controls, etc.
    *   `src/services/`: API communication logic.
*   `docs/`: Contains additional documentation, like `architecture.md`.
*   `sample_test_data/`: Contains sample CSV files for testing and demonstration.

## Backend Setup & Running

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```
2.  **Create and activate a Python virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the Flask development server:**
    ```bash
    flask run
    # Or, for more control (e.g., specifying port if needed):
    # python app.py 
    ```
5.  The backend server will typically run on `http://localhost:5000`.

## Frontend Setup & Running

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```
3.  **Start the React development server:**
    ```bash
    npm start
    ```
4.  The frontend development server will typically run on `http://localhost:3000` and open automatically in your browser.

## Usage

1.  Open the application in your web browser (usually `http://localhost:3000`).
2.  Use the "Upload CSV Files" section to select one or more CSV files.
3.  Enter the "Operation Column Name" (a column common to all files, used for matching rows).
4.  Enter a numeric "Threshold Value".
5.  Click the "Process Files" button.
6.  The application will upload, process the files, and perform comparisons.
7.  If successful, a download link for the generated Excel report will appear. Click this link to download the report.
8.  Any errors or warnings encountered during processing will be displayed on the UI.

## API Endpoints

The backend provides the following main API endpoints:

*   **`/upload`**
    *   **Method:** `POST`
    *   **Description:** Uploads one or more CSV files.
    *   **Request:** `FormData` containing files under the key `files`.
    *   **Response:** JSON indicating status, names of uploaded files, and any upload errors.
*   **`/process`**
    *   **Method:** `POST`
    *   **Description:** Processes the uploaded CSV files based on provided parameters.
    *   **Request:** JSON body with `file_names: string[]`, `operation_column: string`, `threshold_value: number`.
    *   **Response:** JSON containing processing status, summary of parsing/validation, comparison results, warnings, errors, and the filename of the generated Excel report.
*   **`/download/<filename>`**
    *   **Method:** `GET`
    *   **Description:** Downloads a generated Excel report.
    *   **Request:** `filename` as a path parameter (e.g., `/download/comparison_report_20231027_123456.xlsx`).
    *   **Response:** The Excel file as an attachment.

For more detailed information on the architecture and data flow, please see `docs/architecture.md`.

## Running Tests

Backend unit tests are implemented using `pytest`. For instructions on how to run these tests, please refer to the "Testing" section in `docs/architecture.md`.

## Sample Data

Sample CSV files for testing and demonstration purposes are available in the `sample_test_data/` directory at the root of the project. These can be used to quickly test the application's functionality. The sample files include:
* `sample1_students_grades.csv`: Comma-separated student grades data.
* `sample2_students_attendance.csv`: Semicolon-separated student attendance data.
* `sample3_class_info.csv`: Comma-separated student advisory information.

## Known Issues/Limitations

*   **Backend Unit Tests:** One unit test for `perform_column_comparison`'s specific warning message (`test_perform_comparison_comparable_col_missing_in_other`) is currently adjusted to pass against a known incorrect warning from `backend/csv_handler.py`. This highlights a remaining bug in `perform_column_comparison` that needs further debugging. The other critical failures in `read_csv_files` were addressed in the previous subtask.

This application is a proof-of-concept and may require further enhancements for production use, particularly in areas of error handling, scalability, and security.
