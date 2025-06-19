import os
import json
import logging
from typing import Any, Callable, Optional, Set

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_json_file(filepath: str, default_value_func: Optional[Callable[[], Any]] = None) -> Any:
    """
    Load JSON data from a file, with fallback to a default value if the file is missing or corrupt.

    Args:
        filepath: Path to the JSON file.
        default_value_func: Optional callable that returns a default value if the file
                           is missing or corrupt. If None, returns an empty dict.

    Returns:
        The loaded JSON data (typically dict or list), or the default value/empty dict.

    Raises:
        TypeError: If filepath is not a string.
        OSError: If file access fails due to permissions or other OS-related issues.
    """
    if not isinstance(filepath, str):
        raise TypeError(f"filepath must be a string, got {type(filepath).__name__}")

    try:
        if os.path.isfile(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logging.info(f"File not found: {filepath}. Initializing with default.")
            return _handle_default(filepath, default_value_func)
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {filepath}: {e}")
        return _handle_default(filepath, default_value_func)
    except OSError as e:
        logging.error(f"OS error while accessing {filepath}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while reading {filepath}: {e}")
        return _handle_default(filepath, default_value_func)

def _handle_default(filepath: str, default_value_func: Optional[Callable[[], Any]]) -> Any:
    """
    Handle default value creation and file initialization.

    Args:
        filepath: Path to the JSON file.
        default_value_func: Optional callable that returns a default value.

    Returns:
        The default value, either from the callable or an empty dict.
    """
    default_value = default_value_func() if default_value_func else {}
    try:
        save_json_file(filepath, default_value)
        logging.info(f"Initialized {filepath} with default value.")
    except OSError as e:
        logging.error(f"Failed to save default value to {filepath}: {e}")
    return default_value

def save_json_file(filepath: str, data: Any) -> None:
    """
    Save data to a JSON file.

    Args:
        filepath: Path to the JSON file.
        data: Data to serialize as JSON.

    Raises:
        TypeError: If filepath is not a string.
        OSError: If file writing fails.
    """
    if not isinstance(filepath, str):
        raise TypeError(f"filepath must be a string, got {type(filepath).__name__}")

    try:
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logging.error(f"Failed to write JSON to {filepath}: {e}")
        raise

def load_settings() -> Any:
    """
    Load application settings from settings.json.

    Returns:
        The loaded settings data, or default/empty dict if file is missing or corrupt.
    """
    from . import config  # Lazy import to avoid circular imports
    return load_json_file(config.SETTINGS_FILE)

def save_settings(settings: Any) -> None:
    """
    Save application settings to settings.json.

    Args:
        settings: The settings data to save.

    Raises:
        OSError: If file writing fails.
    """
    from . import config
    save_json_file(config.SETTINGS_FILE, settings)
    logging.info("Settings updated.")

def load_history() -> list:
    """
    Load analysis history from history.json.

    Returns:
        The loaded history data, or an empty list if file is missing or corrupt.
    """
    from . import config
    return load_json_file(config.HISTORY_FILE, default_value_func=lambda: [])

def save_history(history: list) -> None:
    """
    Save analysis history to history.json.

    Args:
        history: The history data to save.

    Raises:
        OSError: If file writing fails.
    """
    from . import config
    save_json_file(config.HISTORY_FILE, history)
    logging.info("History updated.")

def load_pe_firms() -> Any:
    """
    Load the list of private equity firms from pe_firms.json.

    Returns:
        The loaded private equity firms data, or default value if file is missing or corrupt.
    """
    from . import config
    return load_json_file(config.PE_LIST_FILE, default_value_func=config.get_default_pe_firms)

def save_pe_firms(pe_firms: Any) -> None:
    """
    Save the list of private equity firms to pe_firms.json.

    Args:
        pe_firms: The private equity firms data to save.

    Raises:
        OSError: If file writing fails.
    """
    from . import config
    save_json_file(config.PE_LIST_FILE, pe_firms)
    logging.info("Private equity firms list updated.")

def load_nations() -> list:
    """
    Load the list of nations from nations.json.

    Returns:
        The loaded nations list, or an empty list if file is missing or corrupt.
    """
    from . import config
    # The default function here is set to None, assuming nations.json will be created manually.
    # For a truly robust system, you could define a get_default_nations in config.py.
    data = load_json_file(config.NATIONS_FILE, default_value_func=lambda: {"nations": []})
    return data.get("nations", [])

def allowed_file(filename: str) -> bool:
    """
    Check if the uploaded file has an allowed extension.

    Args:
        filename: The name of the file to check.

    Returns:
        True if the file extension is allowed, False otherwise.

    Raises:
        TypeError: If filename is not a string.
    """
    from . import config
    if not isinstance(filename, str):
        raise TypeError(f"filename must be a string, got {type(filename).__name__}")
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

def ensure_dirs() -> None:
    """
    Ensure necessary directories (upload and reports) exist.

    Raises:
        OSError: If directory creation fails.
    """
    from . import config
    try:
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(config.REPORTS_FOLDER, exist_ok=True)
        logging.info("Ensured upload and reports directories exist.")
    except OSError as e:
        logging.error(f"Failed to create directories: {e}")
        raise