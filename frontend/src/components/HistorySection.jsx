import React, { useState, useEffect } from 'react';
import { format, parseISO } from 'date-fns'; // Import parseISO to convert ISO string to Date object

// This component fetches and displays the history of analysis reports.
function HistorySection({ showAlert, navigateTo }) {
  // State to hold the list of history entries
  const [history, setHistory] = useState([]);
  // State to manage loading status
  const [isLoading, setIsLoading] = useState(true);
  // State to keep track of any polling interval for status updates
  const [pollingIntervalId, setPollingIntervalId] = useState(null);

  // Function to fetch the history data from the backend
  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/history'); // GET request to Flask backend
      const data = await response.json();

      if (response.ok) {
        setHistory(data); // Update history state with fetched data
      } else {
        showAlert('error', data.error || 'Failed to load analysis history.');
      }
    } catch (error) {
      console.error('Error fetching history:', error);
      showAlert('error', `Network error while loading history: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Function to check the status of pending reports and re-fetch if needed
  const checkPendingStatuses = async () => {
    const pendingReports = history.filter(entry => entry.status === 'Pending');
    if (pendingReports.length > 0) {
      // Re-fetch the entire history if there are pending reports
      // This ensures the UI updates when a background task completes
      await fetchHistory();
    } else {
      // If no pending reports, clear any active polling interval
      if (pollingIntervalId) {
        clearInterval(pollingIntervalId);
        setPollingIntervalId(null);
        console.log("Cleared polling interval: No pending reports.");
      }
    }
  };


  // useEffect Hook to fetch history on component mount
  useEffect(() => {
    fetchHistory(); // Initial fetch

    // Set up polling for status updates if there are potentially pending tasks
    // We start polling immediately, and clear it if no pending reports are found in subsequent checks
    const id = setInterval(checkPendingStatuses, 5000); // Poll every 5 seconds
    setPollingIntervalId(id);

    // Cleanup function: This runs when the component unmounts
    return () => {
      if (id) {
        clearInterval(id); // Clear the interval to prevent memory leaks
        console.log("Cleared polling interval on unmount.");
      }
    };
  }, [showAlert]); // Dependency array: re-run effect if showAlert changes

  // Function to handle viewing a specific report
  const handleViewReport = (reportId) => {
    navigateTo('reportDetail', reportId); // Navigate to report detail section with the report ID
  };

  // Helper to format duration for display
  const formatDuration = (seconds) => {
    if (typeof seconds !== 'number' || isNaN(seconds)) {
      return 'N/A';
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
  };

  return (
    <section id="history-section" className="main-content-section">
      <h2 className="text-3xl font-semibold text-gray-800 mb-6 border-b pb-3">Analysis History</h2>
      {isLoading ? (
        <div className="text-center py-8 text-gray-500">
          <i className="ph ph-spinner animate-spin text-4xl"></i>
          <p className="mt-2">Loading history...</p>
        </div>
      ) : (
        <div id="history-list" className="space-y-4">
          {history.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No analysis history found. Upload a file to start!</p>
          ) : (
            history.map((entry) => (
              <div
                key={entry.id} // Unique key for React list rendering
                className="bg-white p-4 rounded-lg shadow-md border-l-4 cursor-pointer hover:bg-gray-100 transition-colors duration-200"
                style={{ borderColor: entry.status === 'Completed' ? '#10B981' : '#F59E0B' }} // Green for completed, amber for pending
                onClick={() => handleViewReport(entry.id)} // Click to view details
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-semibold text-gray-800">{entry.name}</h3>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    entry.status === 'Completed' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800 animate-pulse'
                  }`}>
                    {entry.status}
                  </span>
                </div>
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Date:</span> {entry.date ? format(parseISO(entry.date), 'MMM dd, yyyy HH:mm') : 'N/A'}
                </p>
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Companies:</span> {entry.num_companies || 'N/A'}
                </p>
                {entry.status === 'Completed' && (
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Duration:</span> {formatDuration(entry.analysis_duration_seconds)}
                  </p>
                )}
                {entry.error && (
                  <p className="text-sm text-red-600 mt-2">
                    <span className="font-bold">Error:</span> {entry.error}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </section>
  );
}

export default HistorySection;