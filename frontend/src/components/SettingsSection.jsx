import React, { useState, useEffect } from 'react';

// This component handles displaying and updating application settings.
function SettingsSection({ showAlert }) {
  // State for the Gemini API Key input field
  const [geminiApiKey, setGeminiApiKey] = useState('');
  // State for the Private Equity Firms list (textarea)
  const [peFirms, setPeFirms] = useState('');
  // State to manage loading status of settings
  const [isLoading, setIsLoading] = useState(true);
  // State to track if changes have been made (to enable/disable Save button)
  const [hasChanges, setHasChanges] = useState(false);
  // Store initial settings to compare for changes
  const [initialSettings, setInitialSettings] = useState(null);

  // useEffect Hook to fetch settings when the component mounts
  useEffect(() => {
    const fetchSettings = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('/settings'); // GET request to Flask backend
        const data = await response.json();

        if (response.ok) {
          // Set state with fetched values
          setGeminiApiKey(data.gemini_api_key || '');
          // PE firms are an array in backend, convert to newline-separated string for textarea
          setPeFirms((data.pe_firms || []).join('\n'));
          // Store initial settings to detect changes
          setInitialSettings({
            gemini_api_key: data.gemini_api_key || '',
            pe_firms: (data.pe_firms || []).join('\n')
          });
          setHasChanges(false); // No changes initially after loading
        } else {
          showAlert('error', data.error || 'Failed to load settings.');
        }
      } catch (error) {
        console.error('Error fetching settings:', error);
        showAlert('error', `Network error while loading settings: ${error.message}`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSettings();
  }, [showAlert]); // Dependency array: re-run effect if showAlert changes (unlikely)

  // useEffect to detect changes in input fields
  useEffect(() => {
    if (initialSettings) { // Only compare once initial settings are loaded
      const currentSettings = {
        gemini_api_key: geminiApiKey,
        pe_firms: peFirms
      };
      // Check if current settings differ from initial loaded settings
      setHasChanges(
        currentSettings.gemini_api_key !== initialSettings.gemini_api_key ||
        currentSettings.pe_firms !== initialSettings.pe_firms
      );
    }
  }, [geminiApiKey, peFirms, initialSettings]); // Re-run when these states change

  // Event handler for form submission (saving settings)
  const handleSubmit = async (event) => {
    event.preventDefault(); // Prevent default form submission

    setIsLoading(true); // Show loading indicator while saving
    showAlert('info', 'Saving settings...');

    try {
      const response = await fetch('/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json', // Specify JSON content type
        },
        body: JSON.stringify({
          gemini_api_key: geminiApiKey,
          // Convert newline-separated string back to an array for the backend
          pe_firms: peFirms.split('\n').map(line => line.trim()).filter(line => line !== ''),
        }),
      });

      const result = await response.json();

      if (response.ok) {
        showAlert('success', result.message || 'Settings saved successfully!');
        // Update initial settings after successful save to reflect new "clean" state
        setInitialSettings({
            gemini_api_key: geminiApiKey,
            pe_firms: peFirms
        });
        setHasChanges(false); // No pending changes after save
      } else {
        showAlert('error', result.error || 'Failed to save settings.');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      showAlert('error', `Network error or unexpected issue: ${error.message}`);
    } finally {
      setIsLoading(false); // Hide loading indicator
    }
  };

  return (
    <section id="settings-section" className="main-content-section">
      <h2 className="text-3xl font-semibold text-gray-800 mb-6 border-b pb-3">Application Settings</h2>
      {isLoading ? (
        <div className="text-center py-8 text-gray-500">
          <i className="ph ph-spinner animate-spin text-4xl"></i>
          <p className="mt-2">Loading settings...</p>
        </div>
      ) : (
        <div className="bg-white p-6 rounded-lg shadow-md mb-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="gemini-api-key" className="block text-sm font-medium text-gray-700 mb-2">Gemini API Key</label>
              <input
                type="password" // Use type="password" to hide the key input
                id="gemini-api-key"
                placeholder="Enter your Gemini API Key"
                className="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={geminiApiKey} // Controlled component: input value is tied to state
                onChange={(e) => setGeminiApiKey(e.target.value)} // Update state on change
                disabled={isLoading}
              />
              <p className="mt-2 text-xs text-gray-500">Your API key is stored locally and used for company analysis. Keep it confidential.</p>
            </div>
            <div>
              <label htmlFor="pe-firms-list" className="block text-sm font-medium text-gray-700 mb-2">Private Equity Firms (one per line)</label>
              <textarea
                id="pe-firms-list"
                rows="10"
                className="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="e.g.,&#10;Blackstone&#10;KKR&#10;Bain Capital"
                value={peFirms} // Controlled component
                onChange={(e) => setPeFirms(e.target.value)} // Update state on change
                disabled={isLoading}
              ></textarea>
              <p className="mt-2 text-xs text-gray-500">Enter known Private Equity firm names, one per line. These are used to identify PE-owned companies.</p>
            </div>
            <button
              type="submit"
              className={`w-full bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${!hasChanges || isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-700'}`}
              disabled={!hasChanges || isLoading} // Disable if no changes or loading
            >
              {isLoading ? (
                <>
                  <i className="ph ph-spinner animate-spin mr-2"></i>
                  Saving...
                </>
              ) : (
                <>
                  <i className="ph ph-floppy-disk mr-2"></i>
                  Save Settings
                </>
              )}
            </button>
          </form>
        </div>
      )}
    </section>
  );
}

export default SettingsSection;
