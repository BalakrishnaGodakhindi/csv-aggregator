import os
from flask import Flask, request, jsonify, send_from_directory
from .csv_handler import (
    read_csv_files, 
    validate_dataframes_for_processing, 
    perform_column_comparison,
    generate_excel_output
)
import pandas as pd # For isinstance checks

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed' # For storing processed files
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part in the request'}), 400
    
    files = request.files.getlist('files')
    
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No selected files'}), 400

    uploaded_filenames = []
    errors = []

    for file in files:
        if file and file.filename.endswith('.csv'):
            try:
                filename = file.filename
                # Note: In a real app, you'd want to secure the filename
                # For example, using werkzeug.utils.secure_filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                uploaded_filenames.append(filename)
            except Exception as e:
                errors.append({'filename': file.filename, 'error': str(e)})
        elif file:
            errors.append({'filename': file.filename, 'error': 'Invalid file type. Only CSV files are allowed.'})

    if not uploaded_filenames and errors:
         return jsonify({'status': 'failed', 'errors': errors}), 400
    elif uploaded_filenames and errors:
        return jsonify({'status': 'partial_success', 'uploaded_files': uploaded_filenames, 'errors': errors}), 207
    elif uploaded_filenames:
        return jsonify({'status': 'success', 'uploaded_files': uploaded_filenames}), 200
    else: # Should not happen if initial checks are correct
        return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    # Note: This runs the app in development mode. 
    # For production, use a proper WSGI server like Gunicorn.
    app.run(debug=True)


@app.route('/process', methods=['POST'])
def process_files():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    file_names = data.get('file_names')
    operation_column = data.get('operation_column')
    threshold_value_str = data.get('threshold_value') # Keep as string for now for validation

    if not all([file_names, operation_column, threshold_value_str is not None]):
        missing_params = []
        if not file_names: missing_params.append('file_names')
        if not operation_column: missing_params.append('operation_column')
        if threshold_value_str is None: missing_params.append('threshold_value')
        return jsonify({'error': 'Missing parameters', 'missing': missing_params}), 400

    try:
        threshold_value = float(threshold_value_str)
    except ValueError:
        return jsonify({'error': "Invalid 'threshold_value'. Must be a number."}), 400

    # --- CSV Reading Step ---
    csv_read_results = read_csv_files(file_names, app.config['UPLOAD_FOLDER'])
    parsed_dataframes_info = csv_read_results['dataframes'] # list of {'filename': str, 'dataframe': pd.DataFrame}
    all_errors = csv_read_results['errors'] # Initialize list of all errors

    # Consolidate initially parsed files info for potential partial success response
    parsed_files_summary = []
    if parsed_dataframes_info:
        for df_info in parsed_dataframes_info:
            parsed_files_summary.append({
                'filename': df_info['filename'],
                'initial_shape': df_info['dataframe'].shape,
                'initial_columns': list(df_info['dataframe'].columns)
            })

    if not parsed_dataframes_info and all_errors: # All files failed at reading stage
        return jsonify({
            'status': 'failed',
            'message': 'Failed to read or parse any CSV files.',
            'errors': all_errors,
            'operation_column': operation_column,
            'threshold_value': threshold_value # Return original parsed threshold
        }), 422

    # --- DataFrame Validation Step ---
    validation_results = validate_dataframes_for_processing(parsed_dataframes_info, operation_column)
    validated_dataframes = validation_results['validated_dataframes'] # list of {'filename', 'dataframe', 'numeric_columns'}
    validation_errors = validation_results['errors']
    all_errors.extend(validation_errors)

    if not validated_dataframes:
        return jsonify({
            'status': 'failed',
            'message': 'No DataFrames passed validation for processing (e.g., operation column missing, not numeric, or no other numeric columns).',
            'parsed_files_summary': parsed_files_summary, # Show what was initially parsed
            'errors': all_errors,
            'operation_column': operation_column,
            'threshold_value': threshold_value # Return original parsed threshold
        }), 422

    # --- Column Comparison Step ---
    comparison_output = perform_column_comparison(validated_dataframes, operation_column)
    comparison_data = comparison_output['comparison_results'] # dict of {(col, f1, f2): DataFrame_with_diff}
    comparison_warnings = comparison_output['warnings']
    # all_errors.extend(comparison_warnings) # Warnings are not strictly errors, handle separately

    # Summarize comparison results for JSON response
    summarized_comparisons = []
    for key, diff_df in comparison_data.items():
        col_name, ref_file, other_file = key
        # diff_df is a DataFrame with 'operation_column' and 'difference'
        if not diff_df.empty and 'difference' in diff_df.columns:
            differences = diff_df['difference']
            summarized_comparisons.append({
                'compared_column': col_name,
                'reference_file': ref_file,
                'other_file': other_file,
                'rows_compared': len(differences),
                'mean_difference': differences.mean(),
                'std_difference': differences.std(),
                'min_difference': differences.min(),
                'max_difference': differences.max(),
                # 'num_over_threshold': (differences > threshold_value).sum() # This will be for next step
            })
        else:
             summarized_comparisons.append({
                'compared_column': col_name,
                'reference_file': ref_file,
                'other_file': other_file,
                'rows_compared': 0,
                'message': 'No differences calculated (e.g., no common rows after merge or empty diff series).'
            })


    # --- Excel Output Generation Step ---
    excel_filename_response = None
    # Ensure `threshold_value` is float for generate_excel_output
    # It should be float already due to earlier conversion, but as a safeguard:
    float_threshold_value = threshold_value 
    try:
        float_threshold_value = float(threshold_value)
    except ValueError:
        # This case should ideally be caught earlier, but if not, use a default or raise error
        # For now, let's assume it's already a float from earlier conversion.
        pass


    if validated_dataframes and comparison_data: # Only generate if there's something to compare/report
        try:
            excel_output_basename = "comparison_report" 
            excel_filepath = generate_excel_output(
                validated_dataframes_data=validated_dataframes,
                comparison_results=comparison_data,
                operation_column=operation_column,
                threshold_value=float_threshold_value, # Ensure float is passed
                output_filename_base=excel_output_basename,
                base_processed_folder=app.config['PROCESSED_FOLDER']
            )
            excel_filename_response = os.path.basename(excel_filepath)
        except Exception as e:
            # Add to warnings or errors if Excel generation fails
            excel_gen_error_msg = f"Failed to generate Excel report: {str(e)}"
            if comparison_warnings:
                comparison_warnings.append({'type': 'ExcelGenerationError', 'message': excel_gen_error_msg})
            else:
                comparison_warnings = [{'type': 'ExcelGenerationError', 'message': excel_gen_error_msg}]
            # Potentially add to all_errors if this is considered a critical failure
            # all_errors.append({'file': 'ExcelReport', 'error': excel_gen_error_msg})


    final_status = 'success'
    if all_errors or comparison_warnings: # comparison_warnings might now include Excel error
        final_status = 'partial_success_with_issues'
        
    # Update parsed_files_summary to reflect validated state (as before)
    validated_files_summary = []
    for v_df_info in validated_dataframes:
        validated_files_summary.append({
            'filename': v_df_info['filename'],
            'validated_shape': v_df_info['dataframe'].shape,
            'numeric_columns_for_comparison': v_df_info['numeric_columns'],
            'operation_column_dtype': str(v_df_info['dataframe'][operation_column].dtype)
        })

    response_payload = {
        'status': final_status,
        'message': 'Processing pipeline completed.',
        'initial_parsing_summary': parsed_files_summary,
        'validated_files_summary': validated_files_summary,
        'comparison_summary': summarized_comparisons,
        'excel_report_filename': excel_filename_response, # Add this line
        'errors': all_errors if all_errors else None,
        'warnings': comparison_warnings if comparison_warnings else None,
        'operation_column': operation_column,
        'threshold_value': threshold_value # Return the float threshold
    }
    
    http_status_code = 200
    if all_errors: # If there were any errors collected in all_errors
        http_status_code = 207 # Multi-Status
    elif final_status == 'partial_success_with_issues' and not all_errors: # Only warnings (like Excel gen)
        http_status_code = 200 # Still OK, but with warnings in payload
    
    # --- Cleanup Uploaded Files Step (Optional) ---
    # This happens after response payload is determined, so cleanup failures won't affect client response
    # other than potentially logging a warning if that's desired.
    if file_names: # file_names is the list of original filenames from the request
        for uploaded_filename in file_names:
            try:
                file_path_to_delete = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_filename)
                if os.path.exists(file_path_to_delete):
                    os.remove(file_path_to_delete)
                    # print(f"Successfully deleted uploaded file: {file_path_to_delete}") # For server log
                # else:
                    # print(f"Uploaded file not found for deletion: {file_path_to_delete}") # For server log
            except Exception as e:
                # Log this error to the server console/log file
                print(f"Error deleting uploaded file {uploaded_filename}: {str(e)}")
                # Optionally, add to a 'cleanup_warnings' list in response_payload if critical for client to know
                # For now, keeping it as a server-side concern.

    return jsonify(response_payload), http_status_code


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    # Security: Prevent directory traversal and ensure it's an xlsx file
    if not filename.endswith(".xlsx") or \
       '..' in filename or \
       filename.startswith('/') or \
       filename.startswith('\\'): # Check for backslashes too for Windows paths
        return jsonify({'error': 'Invalid or unpermitted filename/filetype.'}), 400

    processed_folder = app.config['PROCESSED_FOLDER']
    
    # It's good practice to also check if the file actually exists before calling send_from_directory
    # although send_from_directory will raise NotFound if it doesn't.
    # This gives a slightly more controlled error message if desired.
    file_path = os.path.join(processed_folder, filename)
    if not os.path.isfile(file_path):
        return jsonify({'error': 'File not found in processed directory.'}), 404

    try:
        return send_from_directory(processed_folder, filename, as_attachment=True)
    except FileNotFoundError: # Should be caught by os.path.isfile, but as a safeguard
        return jsonify({'error': 'File not found.'}), 404
    except Exception as e:
        # Log the error e
        return jsonify({'error': 'An error occurred while trying to send the file.'}), 500
