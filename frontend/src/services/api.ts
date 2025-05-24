// Base URL for the backend API
// In a real app, this should come from an environment variable
const API_BASE_URL = 'http://localhost:5000'; // Assuming backend runs on port 5000

interface UploadResponse {
  status: 'success' | 'partial_success' | 'failed';
  uploaded_files?: string[];
  errors?: Array<{ filename: string; error: string }>;
  message?: string; // General message for overall status
}

interface ProcessResponse {
  status: string; // e.g., 'success', 'failed', 'partial_success_with_issues'
  message: string;
  initial_parsing_summary?: any[];
  validated_files_summary?: any[];
  comparison_summary?: any[];
  excel_report_filename?: string;
  errors?: any[] | null;
  warnings?: any[] | null;
}

interface ApiError {
  type: 'UploadError' | 'ProcessError' | 'NetworkError' | 'UnexpectedError';
  message: string;
  details?: any; // Could be errors from backend's 'errors' array
}

export const uploadAndProcessFiles = async (
  files: File[],
  operationColumn: string,
  threshold: number
): Promise<ProcessResponse> => {
  // Step 1: File Upload
  const uploadFormData = new FormData();
  files.forEach(file => {
    uploadFormData.append('files', file);
  });

  let uploadedFileNames: string[];

  try {
    const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: uploadFormData,
    });

    if (!uploadResponse.ok) {
      // Attempt to parse error from backend, otherwise use status text
      let errorBody;
      try {
        errorBody = await uploadResponse.json();
      } catch (e) {
        // Ignore if error body is not JSON
      }
      throw { 
        type: 'UploadError', 
        message: errorBody?.error || errorBody?.message || `Upload failed: ${uploadResponse.statusText}`,
        details: errorBody?.errors 
      } as ApiError;
    }

    const uploadResult: UploadResponse = await uploadResponse.json();

    if (uploadResult.status === 'failed' || !uploadResult.uploaded_files || uploadResult.uploaded_files.length === 0) {
      throw { 
        type: 'UploadError', 
        message: uploadResult.message || 'No files were successfully uploaded.',
        details: uploadResult.errors 
      } as ApiError;
    }
    if (uploadResult.status === 'partial_success' && (!uploadResult.uploaded_files || uploadResult.uploaded_files.length === 0)) {
        // This case should ideally be handled by backend sending 'failed'
         throw { 
            type: 'UploadError', 
            message: 'Partial upload success, but no files were listed as uploaded.',
            details: uploadResult.errors 
        } as ApiError;
    }
    
    uploadedFileNames = uploadResult.uploaded_files;
    // Optionally, could return partial success info here if needed by UI for more granular feedback

  } catch (error: any) {
    if (error.type === 'UploadError') throw error; // Re-throw specific ApiError
    throw { type: 'NetworkError', message: `Network error during upload: ${error.message || 'Unknown network error'}` } as ApiError;
  }

  // Step 2: Trigger Processing
  try {
    const processResponse = await fetch(`${API_BASE_URL}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_names: uploadedFileNames,
        operation_column: operationColumn,
        threshold_value: threshold, // Ensure backend handles this as number
      }),
    });

    if (!processResponse.ok) {
      let errorBody;
      try {
        errorBody = await processResponse.json();
      } catch(e) { /* ignore */ }
      throw { 
        type: 'ProcessError', 
        message: errorBody?.message || errorBody?.error || `Processing request failed: ${processResponse.statusText}`,
        details: errorBody?.errors || errorBody?.warnings
      } as ApiError;
    }

    const processResult: ProcessResponse = await processResponse.json();
    
    // The backend's /process might return 200 or 207 even with errors/warnings in the body
    // So, we return the full processResult for the UI to handle based on its 'status' field.
    return processResult;

  } catch (error: any) {
    if (error.type === 'ProcessError') throw error; // Re-throw specific ApiError
    throw { type: 'NetworkError', message: `Network error during processing: ${error.message || 'Unknown network error'}` } as ApiError;
  }
};
