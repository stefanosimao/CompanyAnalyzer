import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx'; // This will be your main React component
import './index.css'; // Import the global CSS (which now includes Tailwind directives)

// Find the root DOM element where your React app will be mounted
const rootElement = document.getElementById('root');

// Create a root and render your App component
ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
); 