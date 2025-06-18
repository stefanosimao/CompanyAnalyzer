import React, { useState } from 'react';

// This component handles the file upload and initiates the analysis.
function UploadSection({ showAlert, navigateTo }) {
  // State to hold the selected file
  const [selectedFile, setSelectedFile] = useState(null);
  // State to manage the loading/analysis in progress indicator
  const [isUploading, setIsUploading] = useState(false);

  // Event handler for when a file is selected
  const handleFileChange = (event) => {
    // Get the first file from the input (users can only select one)
    setSelectedFile(event.target.files[0]);
  };

  // Event handler for form submission
  const handleSubmit = async (event) => {
    event.preventDefault(); // Prevent default form submission to handle it with JavaScript

    if (!selectedFile) {
      showAlert('error', 'Please select an Excel file to upload.');
      return;
    }

    setIsUploading(true); // Show loading indicator
    showAlert('info', 'Uploading file and starting analysis...');

    // Create a FormData object to send the file
    const formData = new FormData();
    formData.append('file', selectedFile); // Append the selected file under the key 'file'

    try {
      // Send the file to the Flask backend's /upload endpoint
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData, // Use FormData directly as the body
      });

      const result = await response.json(); // Parse the JSON response from the server

      if (response.ok) { // Check if the HTTP status code is in the 2xx range
        showAlert('success', result.message || 'File uploaded and analysis started successfully!');
        // Optionally navigate to history or show a link to the new report
        // For now, let's navigate to the history section after successful upload
        navigateTo('history'); 
      } else {
        // Handle server-side errors (e.g., invalid file type, missing column, API key not set)
        showAlert('error', result.error || 'An error occurred during upload or analysis.');
      }
    } catch (error) {
      console.error('Error during file upload:', error);
      showAlert('error', `Network error or unexpected issue: ${error.message}`);
    } finally {
      setIsUploading(false); // Hide loading indicator
      setSelectedFile(null); // Clear the selected file input
      document.getElementById('excel-file').value = ''; // Reset the file input element
    }
  };

  return (
    <section id="upload-section" className={`main-content-section ${isUploading ? 'pointer-events-none opacity-50' : ''}`}>
      <h2 className="text-3xl font-semibold text-gray-800 mb-6 border-b pb-3">Upload Company List</h2>
      <div className="bg-white p-6 rounded-lg shadow-md mb-8">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="excel-file" className="block text-sm font-medium text-gray-700 mb-2">Select Excel File (.xlsx or .xls)</label>
            <input
              type="file"
              id="excel-file"
              name="file"
              accept=".xlsx,.xls"
              className="mt-1 block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              onChange={handleFileChange}
              disabled={isUploading} // Disable input while uploading
            />
            <p className="mt-2 text-xs text-gray-500">Please ensure your Excel file has a column named 'Company Name'.</p>
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            disabled={isUploading} // Disable button while uploading
          >
            {isUploading ? (
              <>
                <i className="ph ph-spinner animate-spin mr-2"></i>
                Analysis in Progress...
              </>
            ) : (
              <>
                <i className="ph ph-paper-plane-tilt mr-2"></i>
                Start Analysis
              </>
            )}
          </button>
          {/* Progress indicator (always visible with opacity if uploading) */}
          {isUploading && (
            <div id="upload-progress" className="mt-4 text-center text-gray-600">
              <p>This may take a while for large lists.</p>
              <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
                  <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: '100%' }}></div> {/* Static 100% width for visual queue */}
              </div>
            </div>
          )}
        </form>
      </div>
    </section>
  );
}

export default UploadSection;
