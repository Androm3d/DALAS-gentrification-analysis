from pathlib import Path

# This makes the paths work on any operating system (Windows, Mac, Linux)

# The root directory of the project is two levels up from this config file
# (scrapers/ -> gentrification_project/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Data Output Paths ---
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
BARCELONA_DATA_DIR = RAW_DATA_DIR / "barcelona"


# --- File Paths ---
# We use .joinpath() to create the full file path
URL_FILE = BARCELONA_DATA_DIR.joinpath('idealista_listings.csv')
DETAILS_FILE = BARCELONA_DATA_DIR.joinpath('idealista_details.csv')

# --- Error Screenshot Path ---
# It's good practice to save temporary files like screenshots in a separate folder
ERROR_DIR = PROJECT_ROOT / "scrapers" / "_error_screenshots"