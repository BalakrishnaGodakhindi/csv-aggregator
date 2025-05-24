import pandas as pd
import os
import numpy as np
from datetime import datetime

def _get_file_lines(filepath, encoding, max_lines=5):
    lines = []
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line.strip())
    except Exception:
        return None 
    return lines

def _is_likely_binary_from_chunk(filepath, chunk_size=1024) -> bool:
    """Checks for null bytes in a chunk of the file."""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(chunk_size)
            # Null bytes are a strong indicator of binary
            if b'\x00' in chunk:
                return True
    except Exception: # If reading as binary fails, it's problematic
        return True 
    return False

def _try_parse_csv_with_encoding(filepath: str, encoding: str, common_delimiters: list) -> pd.DataFrame | None:
    """
    Attempts to parse a CSV file with a specific encoding using various strategies.
    Returns a DataFrame if successful, None otherwise.
    """
    df_candidate = None
    
    # Strategy 1: Try with sep=None (auto-detection by Python engine)
    try:
        df_attempt = pd.read_csv(filepath, sep=None, engine='python', on_bad_lines='warn', encoding=encoding)
        if df_attempt is not None:
            if len(df_attempt.columns) > 1: # Good multi-column parse
                return df_attempt
            # Handle header-only CSV that might be misread as single column.
            if len(df_attempt) == 0 and len(df_attempt.columns) == 1 and isinstance(df_attempt.columns[0], str):
                header_str = df_attempt.columns[0]
                for delim_char in common_delimiters:
                    if delim_char in header_str and len(header_str.split(delim_char)) > 1 :
                        try:
                            df_reparsed_header = pd.read_csv(filepath, sep=delim_char, on_bad_lines='warn', encoding=encoding)
                            if df_reparsed_header is not None and len(df_reparsed_header.columns) > 1:
                                return df_reparsed_header 
                        except Exception:
                            pass
            if df_candidate is None: # Store if it's a valid DF, even if single column or empty with columns
                 df_candidate = df_attempt
    except pd.errors.ParserError:
        raise 
    except Exception:
        pass 

    # Strategy 2: Try with common delimiters if sep=None wasn't definitively multi-column
    current_best_df = df_candidate 
    for delim in common_delimiters:
        try:
            df_try = pd.read_csv(filepath, sep=delim, on_bad_lines='warn', encoding=encoding)
            if df_try is not None:
                if len(df_try.columns) > 1: 
                    return df_try 
                if current_best_df is None : 
                    current_best_df = df_try
                elif len(current_best_df.columns) == 1 and current_best_df.empty and not df_try.empty:
                    current_best_df = df_try
        except Exception:
            pass 
    return current_best_df


def read_csv_files(relative_file_paths: list, base_upload_folder: str) -> dict:
    dataframes_data = []
    errors_data = []
    
    common_delimiters = [',', ';', '\t', '|']
    encodings_to_try = ['utf-8-sig', 'utf-8', 'latin-1'] 

    for filename in relative_file_paths:
        full_path = os.path.join(base_upload_folder, filename)

        if not os.path.exists(full_path):
            errors_data.append({'filename': filename, 'error': f"File not found: {full_path}"})
            continue

        if _is_likely_binary_from_chunk(full_path):
            # If binary check is positive, directly add error and skip parsing attempts for this file.
            errors_data.append({'filename': filename, 'error': "File appears to be binary or contains null bytes, making it unparseable as CSV."})
            continue
            
        best_df_for_file = None
        parse_error_messages = []
        successfully_parsed_this_file = False # Flag to indicate if a good parse was found

        for encoding in encodings_to_try:
            try:
                current_attempt_df = _try_parse_csv_with_encoding(full_path, encoding, common_delimiters)
                if current_attempt_df is not None:
                    # Manual BOM strip for column names if pandas didn't, only for utf-8-sig
                    # This needs to happen before column count checks if BOM affects column name.
                    if encoding == 'utf-8-sig' and current_attempt_df.columns.size > 0 and \
                       current_attempt_df.columns[0].startswith('\ufeff'):
                        current_attempt_df.columns = [col.replace('\ufeff', '', 1) for col in current_attempt_df.columns]

                    if best_df_for_file is None or \
                       (len(current_attempt_df.columns) > len(best_df_for_file.columns)) or \
                       (encoding == 'utf-8-sig' and (best_df_for_file is None or len(current_attempt_df.columns) >= len(best_df_for_file.columns))):
                        best_df_for_file = current_attempt_df
                    
                    # If this parse is multi-column, it's good enough to stop.
                    # utf-8-sig is preferred if it results in same number of columns as another encoding.
                    if len(best_df_for_file.columns) > 1 :
                        successfully_parsed_this_file = True
                        break 
            
            except pd.errors.EmptyDataError:
                parse_error_messages.append(f"Encoding '{encoding}': File is empty.")
                if best_df_for_file is None: 
                     best_df_for_file = pd.DataFrame() 
                successfully_parsed_this_file = True 
                break 
            except Exception as e:
                parse_error_messages.append(f"Encoding '{encoding}': Error {type(e).__name__} - {str(e)}")
        
        # Post-parsing evaluation for this file
        if best_df_for_file is not None:
            # Check for over-splitting simple text files (single_col_text.txt case)
            if len(best_df_for_file.columns) > 1 and best_df_for_file.shape[0] > 0:
                first_few_lines_content = " ".join(_get_file_lines(full_path, encodings_to_try[0], 5) or [])
                has_no_common_delimiters_in_content = not any(delim in first_few_lines_content for delim in common_delimiters)
                
                # If it was split into multiple columns but no common delimiters are evident in content sample
                if has_no_common_delimiters_in_content:
                    try: # Attempt to re-parse as a single column
                        # Using a very unlikely delimiter character (e.g., ASCII Bell or non-printable)
                        # or force no delimiter interpretation if possible.
                        # header=None ensures first line isn't taken as column names.
                        single_col_df = pd.read_csv(full_path, header=None, names=['data'], sep="\a", engine='python', encoding=encodings_to_try[0], on_bad_lines='warn', skipinitialspace=False)
                        if single_col_df is not None and single_col_df.shape[1] == 1:
                            best_df_for_file = single_col_df
                    except: 
                        pass # Stick with previous best_df_for_file if this re-parse fails

            if best_df_for_file.empty and len(best_df_for_file.columns) == 0: # Empty file, no columns
                errors_data.append({'filename': filename, 'error': "Parsed as an empty table with no columns. Content might be invalid or truly empty."})
            else:
                dataframes_data.append({'filename': filename, 'dataframe': best_df_for_file})
        else: # No successful parse at all
            final_error_msg = f"Could not parse CSV. Tried encodings {encodings_to_try}."
            if parse_error_messages:
                final_error_msg += " Specific errors: " + "; ".join(parse_error_messages)
            errors_data.append({'filename': filename, 'error': final_error_msg})
            
    return {'dataframes': dataframes_data, 'errors': errors_data}


def validate_dataframes_for_processing(dataframes_data: list, operation_column: str) -> dict:
    validated_dfs = []
    validation_errors = []

    for item in dataframes_data:
        filename = item['filename']
        df = item['dataframe'].copy() 

        if operation_column not in df.columns:
            validation_errors.append({
                'filename': filename,
                'error': f"Operation column '{operation_column}' not found."
            })
            continue

        if not pd.api.types.is_numeric_dtype(df[operation_column]):
            original_non_na_count = df[operation_column].notna().sum()
            converted_op_col = pd.to_numeric(df[operation_column], errors='coerce')
            
            if converted_op_col.isna().all() and original_non_na_count > 0:
                validation_errors.append({
                    'filename': filename,
                    'error': f"Operation column '{operation_column}' could not be converted to a numeric type without significant data loss (all values became NaN)."
                })
                continue
            
            df[operation_column] = converted_op_col
            if df[operation_column].isna().any():
                 validation_errors.append({
                    'filename': filename,
                    'error': f"Operation column '{operation_column}' contains non-numeric values that were converted to NaN, or it originally contained NaNs. This column must be purely numeric for merging."
                })
                 continue
        
        if df[operation_column].isna().any(): 
            validation_errors.append({
                'filename': filename,
                'error': f"Operation column '{operation_column}' contains NaN values. Files must not have NaNs in this column for merging."
            })
            continue
            
        numeric_cols = [
            col for col in df.columns 
            if col != operation_column and pd.api.types.is_numeric_dtype(df[col])
        ]
        
        if not numeric_cols:
            validation_errors.append({
                'filename': filename,
                'error': f"No numeric columns found for comparison (excluding operation column '{operation_column}')."
            })
            continue

        validated_dfs.append({
            'filename': filename,
            'dataframe': df,
            'numeric_columns': numeric_cols
        })

    return {'validated_dataframes': validated_dfs, 'errors': validation_errors}


def perform_column_comparison(validated_dataframes_data: list, operation_column: str) -> dict:
    comparison_results = {}
    comparison_warnings = []

    if len(validated_dataframes_data) < 2:
        comparison_warnings.append({
            'type': 'SetupWarning',
            'message': 'At least two DataFrames are required for comparison.'
        })
        return {'comparison_results': comparison_results, 'warnings': comparison_warnings}

    ref_df_data = validated_dataframes_data[0]
    ref_df = ref_df_data['dataframe']
    ref_filename = ref_df_data['filename']
    ref_numeric_cols = ref_df_data['numeric_columns'] 

    if not ref_numeric_cols:
        comparison_warnings.append({
            'type': 'DataWarning',
            'message': f"Reference DataFrame '{ref_filename}' has no numeric columns to compare (excluding operation column)."
        })

    for i in range(1, len(validated_dataframes_data)):
        other_df_data = validated_dataframes_data[i]
        other_df = other_df_data['dataframe']
        other_filename = other_df_data['filename']
        other_df_numeric_cols = other_df_data['numeric_columns']

        # Columns to select from other_df for merge: operation_column + its own numeric columns
        # Ensure columns actually exist in other_df before trying to select them
        cols_to_merge_other = [operation_column] + [col for col in other_df_numeric_cols if col in other_df.columns and col != operation_column]
        cols_to_merge_other = list(set(cols_to_merge_other)) # Ensure unique

        # Columns to select from ref_df for merge
        cols_to_merge_ref = [operation_column] + [col for col in ref_numeric_cols if col in ref_df.columns and col != operation_column]
        cols_to_merge_ref = list(set(cols_to_merge_ref))


        try:
            # Use .copy() on selections to avoid SettingWithCopyWarning if DataFrames are slices
            merged_df = pd.merge(
                ref_df[cols_to_merge_ref].copy(), 
                other_df[cols_to_merge_other].copy(), 
                on=operation_column, 
                suffixes=('_REF', '_OTH'),
                how='inner' 
            )
        except Exception as e:
            comparison_warnings.append({
                'type': 'MergeError',
                'message': f"Could not merge '{ref_filename}' and '{other_filename}' on '{operation_column}'. Error: {str(e)}"
            })
            continue 

        if merged_df.empty:
            comparison_warnings.append({
                'type': 'MergeWarning',
                'message': f"Merge of '{ref_filename}' and '{other_filename}' on '{operation_column}' resulted in an empty DataFrame. No common '{operation_column}' values."
            })
            continue

        for col_name in ref_numeric_cols: # Iterate over numeric columns of the reference DataFrame
            ref_col = col_name + '_REF'
            other_col = col_name + '_OTH' 

            if ref_col not in merged_df.columns:
                # This means col_name from ref_df (which was in ref_numeric_cols) was not in the merged result.
                # This can happen if ref_df itself didn't actually have col_name, despite it being in ref_numeric_cols.
                # This implies an issue with how ref_numeric_cols was constructed or if ref_df was modified.
                comparison_warnings.append({ 
                    'type': 'InternalLogicWarning', 
                    'message': f"Reference column '{col_name}' (expected as '{ref_col}') was not found in merged data between '{ref_filename}' and '{other_filename}'. Check consistency of numeric_columns list."
                })
                continue

            if other_col not in merged_df.columns:
                # This is the correct warning for when the 'other' df doesn't have the column for comparison.
                comparison_warnings.append({
                    'type': 'ColumnMissingInOtherWarning',
                    'message': f"Column '{col_name}' (from '{ref_filename}') did not have a corresponding numeric column in '{other_filename}' for comparison (expected as '{other_col}' in merged data)."
                })
                continue
            
            if not pd.api.types.is_numeric_dtype(merged_df[ref_col]) or \
               not pd.api.types.is_numeric_dtype(merged_df[other_col]):
                comparison_warnings.append({
                    'type': 'DataTypeWarning',
                    'message': f"Columns for '{col_name}' ('{ref_col}' or '{other_col}') are not consistently numeric in merged data for '{ref_filename}' vs '{other_filename}'. Skipping difference calculation."
                })
                continue
            
            diff_series = (merged_df[ref_col] - merged_df[other_col]).abs()
            result_key = (col_name, ref_filename, other_filename)
            comparison_results[result_key] = pd.DataFrame({
                operation_column: merged_df[operation_column],
                'difference': diff_series
            })

    return {'comparison_results': comparison_results, 'warnings': comparison_warnings}


def generate_excel_output(
    validated_dataframes_data: list, 
    comparison_results: dict, 
    operation_column: str, 
    threshold_value: float, 
    output_filename_base: str, 
    base_processed_folder: str
) -> str:
    # ... (rest of the function from Turn 60, assumed mostly correct for now) ...
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{output_filename_base}_{timestamp}.xlsx"
    output_filepath = os.path.join(base_processed_folder, unique_filename)

    rows_to_highlight_map = set()
    compared_columns_set = set() 

    for (col_name, ref_filename, other_filename), diff_df in comparison_results.items():
        compared_columns_set.add(col_name)
        if 'difference' in diff_df.columns: # Ensure 'difference' column exists
            exceeding_threshold_df = diff_df[diff_df['difference'].abs() > threshold_value]
            if operation_column in exceeding_threshold_df.columns: # Ensure op_col exists in diff_df
                for op_col_val in exceeding_threshold_df[operation_column]:
                    rows_to_highlight_map.add((ref_filename, op_col_val))
                    rows_to_highlight_map.add((other_filename, op_col_val))

    with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
        summary_data = {
            "Parameter": [
                "Input Files", "Operation Column", "Threshold Value", 
                "Total Highlighted Rows per File", "Compared Columns"
            ],
            "Value": [
                ", ".join([d['filename'] for d in validated_dataframes_data]),
                operation_column,
                threshold_value,
                "", 
                ", ".join(sorted(list(compared_columns_set))) if compared_columns_set else "N/A"
            ]
        }
        
        highlight_counts_summary = []
        for df_data in validated_dataframes_data:
            fname = df_data['filename']
            df = df_data['dataframe']
            if operation_column in df.columns:
                count = sum(1 for op_val in df[operation_column] if (fname, op_val) in rows_to_highlight_map)
                highlight_counts_summary.append(f"{fname}: {count}")
            else:
                highlight_counts_summary.append(f"{fname}: (op_col missing)")
        
        summary_data["Value"][3] = "; ".join(highlight_counts_summary) if highlight_counts_summary else "0"
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        def highlight_excel_rows(row, current_filename, op_col_name, highlight_map):
            style = [''] * len(row) 
            if op_col_name not in row.index:
                return style 
            op_val = row[op_col_name]
            if (current_filename, op_val) in highlight_map:
                style = ['background-color: yellow'] * len(row)
            return style

        for df_data in validated_dataframes_data:
            original_filename = df_data['filename']
            df_to_write = df_data['dataframe'].copy() 

            safe_sheet_name = "".join(c if c.isalnum() else "_" for c in original_filename)
            if len(safe_sheet_name) > 31:
                safe_sheet_name = safe_sheet_name[:27] + "_etc"
            
            if operation_column not in df_to_write.columns:
                 df_to_write.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                 continue

            styled_df = df_to_write.style.apply(
                highlight_excel_rows, 
                axis=1, 
                current_filename=original_filename, 
                op_col_name=operation_column, 
                highlight_map=rows_to_highlight_map,
            )
            styled_df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
            
    return output_filepath

if __name__ == '__main__': 
    pass
