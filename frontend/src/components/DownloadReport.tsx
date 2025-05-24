import React from 'react';

interface DownloadReportProps {
  filename: string | null;
  // baseUrl could be passed if it's dynamic, otherwise, it can be hardcoded
  // or fetched from an environment variable within the component if preferred.
  // For now, let's assume the App component constructs the full URL.
  // Or, we can make baseUrl a prop.
  downloadUrl?: string; // Allow passing the full URL directly
}

const DownloadReport: React.FC<DownloadReportProps> = ({ filename, downloadUrl }) => {
  if (!filename) {
    return null;
  }

  const url = downloadUrl || `${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000'}/download/${filename}`;

  return (
    <div className="component-section download-section">
      <h2>Download Report</h2>
      <a 
        href={url} 
        download={filename} // This attribute suggests the filename to the browser
        className="button" // Style as button
      >
        Download {filename}
      </a>
      <p style={{fontSize: '0.8em', color: '#555', marginTop: '5px'}}>
        Note: Ensure your backend is running at {process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000'}.
      </p>
    </div>
  );
};

export default DownloadReport;
