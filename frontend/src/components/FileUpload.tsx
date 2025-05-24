import React, { useState, useCallback } from 'react';

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFilesSelected }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState<string>('');

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setError('');
    const files = event.target.files;
    if (files) {
      const fileList = Array.from(files);
      const csvFiles = fileList.filter(file => file.name.toLowerCase().endsWith('.csv'));
      
      if (csvFiles.length !== fileList.length) {
        setError('Only .csv files are allowed.');
      } else {
        setError('');
      }
      
      setSelectedFiles(csvFiles);
      onFilesSelected(csvFiles);
    }
  }, [onFilesSelected]);

  return (
    <div className="component-section">
      <h2>Upload CSV Files</h2>
      <input 
        type="file" 
        multiple 
        onChange={handleFileChange} 
        accept=".csv" 
      />
      {error && <p className="error-message">{error}</p>}
      {selectedFiles.length > 0 && (
        <div>
          <h3>Selected files:</h3>
          <ul className="file-list">
            {selectedFiles.map((file, index) => (
              <li key={index}>{file.name} ({Math.round(file.size / 1024)} KB)</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
