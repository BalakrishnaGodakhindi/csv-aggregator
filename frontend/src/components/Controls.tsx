import React, { useState, useCallback } from 'react';

interface ControlsProps {
  onProcess: (operationColumn: string, threshold: number) => void;
  isProcessing: boolean; // To disable button during processing
}

const Controls: React.FC<ControlsProps> = ({ onProcess, isProcessing }) => {
  const [operationColumn, setOperationColumn] = useState<string>('');
  const [threshold, setThreshold] = useState<string>(''); // Store as string to allow empty input
  const [error, setError] = useState<string>('');

  const handleProcessClick = useCallback(() => {
    setError('');
    if (!operationColumn.trim()) {
      setError('Operation column name is required.');
      return;
    }
    const thresholdNum = parseFloat(threshold);
    if (isNaN(thresholdNum)) {
      setError('Threshold value must be a number.');
      return;
    }
    onProcess(operationColumn, thresholdNum);
  }, [operationColumn, threshold, onProcess]);

  return (
    <div className="component-section">
      <h2>Processing Controls</h2>
      <div>
        <label htmlFor="opColumn">Operation Column Name:</label>
        <input 
          type="text" 
          id="opColumn" 
          value={operationColumn} 
          onChange={(e) => setOperationColumn(e.target.value)} 
          placeholder="e.g., ID, Timestamp"
        />
      </div>
      <div>
        <label htmlFor="threshold">Threshold Value:</label>
        <input 
          type="number" // Using type="text" to better control parsing and allow empty initial
          id="threshold" 
          value={threshold} 
          onChange={(e) => setThreshold(e.target.value)} 
          placeholder="e.g., 0.5, 10"
        />
      </div>
      {error && <p className="error-message">{error}</p>}
      <button onClick={handleProcessClick} disabled={isProcessing || !operationColumn.trim() || threshold === ''}>
        {isProcessing ? 'Processing...' : 'Process Files'}
      </button>
    </div>
  );
};

export default Controls;
