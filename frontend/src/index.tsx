import React from 'react';
import ReactDOM from 'react-dom/client';
import './App.css'; // General styles
import App from './App.tsx'; // Explicit .tsx extension

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
