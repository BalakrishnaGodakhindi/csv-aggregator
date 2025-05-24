import React, { useState, useCallback } from 'react';
import './App.css';
import FileUpload from './components/FileUpload.tsx';
import Controls from './components/Controls.tsx';
import DownloadReport from './components/DownloadReport.tsx'; // Import the new component
import { uploadAndProcessFiles } from './services/api.ts'; 

// Define a type for API errors for better state management
interface ApiError {
  type: 'UploadError' | 'ProcessError' | 'NetworkError' | 'UnexpectedError';
  message: string;
  details?: any;
}

// Define a type for the backend's process response for clarity
interface ProcessResponseData {
  status: string;
  message: string;
  excel_report_filename?: string;
  errors?: any[] | null;
  warnings?: any[] | null;
  // include other fields from backend response if needed by UI
  comparison_summary?: any[]; 
  validated_files_summary?: any[];
}


function App() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  // operationColumn and threshold are now primarily managed by Controls component,
  // but they are passed to handleProcess, so no need to duplicate state here unless for display.
  
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [userMessage, setUserMessage] = useState<string | null>(null); // For feedback like "Uploading..."
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [processData, setProcessData] = useState<ProcessResponseData | null>(null);
  const [excelReportFilename, setExcelReportFilename] = useState<string | null>(null);


  const handleFilesSelected = useCallback((files: File[]) => {
    setSelectedFiles(files);
    setExcelReportFilename(null); // Reset report filename when new files are selected
    setApiError(null);
    setUserMessage(null);
    setProcessData(null);
  }, []);

  const handleProcess = useCallback(async (opCol: string, thresh: number) => {
    if (selectedFiles.length === 0) {
      setApiError({ type: 'UnexpectedError', message: 'Please select files to process.' });
      return;
    }

    setIsProcessing(true);
    setApiError(null);
    setUserMessage('Uploading and processing files...'); // General message
    setExcelReportFilename(null);
    setProcessData(null);

    try {
      const response = await uploadAndProcessFiles(selectedFiles, opCol, thresh);
      // The backend response itself might contain errors or warnings in its body
      // even with a 2xx HTTP status (e.g., status: "partial_success_with_issues")
      
      setProcessData(response); // Store the full response for potential display

      if (response.excel_report_filename) {
        setExcelReportFilename(response.excel_report_filename);
        setUserMessage(`Processing successful! Report generated: ${response.excel_report_filename}`);
      } else {
        // Handle cases where processing completed but no report filename (e.g. due to errors in backend logic)
        setUserMessage(response.message || 'Processing completed, but no report was generated.');
         if (response.errors || response.warnings) {
             // Construct a more specific error message if needed
             let detailedMessage = 'Processing finished with issues: ';
             if(response.errors) detailedMessage += `Errors: ${JSON.stringify(response.errors)}. `;
             if(response.warnings) detailedMessage += `Warnings: ${JSON.stringify(response.warnings)}. `;
             setApiError({type: 'ProcessError', message: detailedMessage, details: {errors: response.errors, warnings: response.warnings}});
         }
      }

      // If backend uses specific status fields to indicate failure even on 2xx HTTP response
      if (response.status === 'failed' || (response.status === 'partial_success_with_issues' && !response.excel_report_filename)) {
         const errorMsg = response.message || 'Processing failed or completed with critical errors.';
         setApiError({type: 'ProcessError', message: errorMsg, details: response.errors || response.warnings});
         setUserMessage(null); // Clear general message, error will be shown
      }

    } catch (err: any) {
      // err should be the ApiError thrown by api.ts
      if (err.type && err.message) {
        setApiError(err);
      } else {
        setApiError({ type: 'UnexpectedError', message: 'An unexpected error occurred during processing.' });
      }
      setUserMessage(null); // Clear general message
      console.error("Processing error details:", err);
    } finally {
      setIsProcessing(false);
      // Do not clear userMessage here if it's a success message.
      // It will be cleared on new file selection or new process attempt.
    }
  }, [selectedFiles]);

  return (
    <div className="App">
      <header>
        <h1>CSV Comparison Tool</h1>
      </header>
      <main>
        <FileUpload onFilesSelected={handleFilesSelected} />
        <Controls 
          onProcess={handleProcess} 
          isProcessing={isProcessing || selectedFiles.length === 0} 
        />
        
        {isProcessing && <div className="feedback-message component-section">{userMessage || 'Processing...'}</div>}
        
        {apiError && (
          <div className="error-message component-section">
            <p><strong>Error Type:</strong> {apiError.type}</p>
            <p><strong>Message:</strong> {apiError.message}</p>
            {apiError.details && (
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                Details: {typeof apiError.details === 'string' ? apiError.details : JSON.stringify(apiError.details, null, 2)}
              </pre>
            )}
          </div>
        )}

        {!isProcessing && !apiError && userMessage && ( // Display success message if not processing and no error
             <div className="feedback-message component-section">{userMessage}</div>
        )}

        {excelReportFilename && !isProcessing && !apiError && ( // Only show download if no fresh error
          <DownloadReport filename={excelReportFilename} />
        )}

        {/* Display details from processData if available and useful */}
        {processData && !apiError && ( // Avoid showing old data if there's a new error
           <div className="component-section results-summary">
             <h3>Processing Details:</h3>
             <p><strong>Status:</strong> {processData.status}</p>
             <p><strong>Backend Message:</strong> {processData.message}</p>
             
             {processData.validated_files_summary && processData.validated_files_summary.length > 0 && (
                <div>
                    <h4>Validated Files:</h4>
                    <ul>
                        {processData.validated_files_summary.map((item: any, index: number) => (
                            <li key={index}>
                                {item.filename} (Shape: {item.validated_shape.join('x')}, OpCol Dtype: {item.operation_column_dtype})
                                <br/>Numeric Cols: {item.numeric_columns_for_comparison.join(', ')}
                            </li>
                        ))}
                    </ul>
                </div>
             )}

             {processData.comparison_summary && processData.comparison_summary.length > 0 && (
                <div>
                    <h4>Comparison Summary:</h4>
                    <ul>
                        {processData.comparison_summary.map((item: any, index: number) => (
                            <li key={index}>
                                Compared '<strong>{item.compared_column}</strong>' between '<em>{item.reference_file}</em>' and '<em>{item.other_file}</em>': 
                                Rows: {item.rows_compared}, Mean Diff: {item.mean_difference?.toFixed(3)}, Std Diff: {item.std_difference?.toFixed(3)}, 
                                Min: {item.min_difference?.toFixed(3)}, Max: {item.max_difference?.toFixed(3)}
                            </li>
                        ))}
                    </ul>
                </div>
             )}

            {/* Display backend errors and warnings clearly if they exist in processData */}
            {processData.errors && processData.errors.length > 0 && (
                <div className="error-message">
                    <h4>Backend Reported Errors:</h4>
                    <pre>{JSON.stringify(processData.errors, null, 2)}</pre>
                </div>
            )}
            {processData.warnings && processData.warnings.length > 0 && (
                 <div className="feedback-message" style={{border: '1px solid orange', padding: '10px', marginTop: '10px'}}>
                    <h4>Backend Reported Warnings:</h4>
                    <pre>{JSON.stringify(processData.warnings, null, 2)}</pre>
                </div>
            )}
           </div>
        )}
        
        {/* Fallback for when processData itself is null but there might be an error */}
        {apiError && !processData && (
           <div className="component-section">
                <p>No detailed processing data to display. Check errors above if any.</p>
           </div>
        )}
      </main>
    </div>
  );
}

export default App;
