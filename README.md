# Gentrification Analysis Project

This repository contains the code and data for a data science project analyzing the factors of gentrification in Paris, Barcelona, and Milan.

## Current Project Status

We have successfully built a robust web scraper for collecting real estate data from **Idealista** (our source for Barcelona and Milan). The immediate next steps involve dividing tasks to acquire the remaining datasets as outlined by our mentor.

The project is now at a crucial "divide and conquer" stage.

---

## Data Acquisition Plan & To-Do List

This plan is based on our mentor's guidance. Let's use this as our checklist.

### **A. Core Socio-Economic & Demographic Data**
*   **Status:** <span style="color:red;">**To Do**</span>
*   **Owner:** **Person 2 (Data Integrator)**
*   **Objective:** Download official statistics (population, income, education) for all three cities.
*   **Action Items:**
    *   [ ] **Paris:** Explore `data.paris.fr` (INSEE data) for CSV/GeoJSON files on "revenus," "population," etc.
    *   [ ] **Barcelona:** Explore `opendata-ajuntament.barcelona.cat` for CSV files on "Població" and "Renda."
    *   [ ] **Milan:** Explore `dati.comune.milano.it` for demographic ("demografici") datasets.

### **B. Real Estate Market Data**
*   **Status:** <span style="color:orange;">**In Progress**</span>
*   **Owner:** **Person 1 (Scraper)**
*   **Objective:** Scrape property listings (price, size, rooms, etc.).
*   **Action Items:**
    *   [x] **Barcelona & Milan (Idealista):** The scraper `scrapers/idealista_scraper.py` is complete and functional.
    *   [ ] **Paris (SeLoger/Bien'ici):** Adapt the existing scraper logic to build a new scraper for a French real estate site. This is the next major scraping task.

### **C. Tourism Pressure Data**
*   **Status:** <span style="color:red;">**To Do**</span>
*   **Owner:** **Person 2 (Data Integrator)**
*   **Objective:** Get data on short-term rentals.
*   **Action Items:**
    *   [ ] Go to `insideairbnb.com` and download the `listings.csv` files for Paris, Barcelona, and Milan.

### **D. Public Policy & Infrastructure Data**
*   **Status:** <span style="color:red;">**To Do**</span>
*   **Owner:** **Person 2 (Data Integrator)**
*   **Objective:** Find data on major urban development projects.
*   **Action Items:**
    *   [ ] **(Critical Task):** Find and download the official **GeoJSON or Shapefiles for the neighborhood boundaries** of all three cities from their respective open data portals. This is essential for merging all other datasets.
    *   [ ] Search the city portals for datasets related to new metro lines ("Grand Paris Express," Milan's M4/M5) and urban renewal projects.

### **E. Commercial & Cultural Activity Data**
*   **Status:** <span style="color:red;">**To Do**</span>
*   **Owner:** **Person 2 (Data Integrator)**
*   **Objective:** Quantify the commercial character of neighborhoods.
*   **Action Items:**
    *   [ ] Research the **Overpass API** for OpenStreetMap.
    *   [ ] Write a small script using the `requests` library to query the API for the number of amenities like `cafe`, `restaurant`, `art_gallery`, etc., within the neighborhood boundaries found in task D.

---

## Immediate Next Steps

### For Person 1 (Scraper):
1.  Review the `idealista_scraper.py` to understand its logic (batching, anti-detection, etc.).
2.  Begin researching **SeLoger.com** or **Bien'ici.com** for Paris. Analyze their page structure to plan the new scraper.

### For Person 2 (Data Integrator):
1.  Your **highest priority** is to find and download the **GeoJSON/Shapefiles of the neighborhoods** for all three cities.
2.  Once you have the boundaries, download the easy datasets: start with the **Inside Airbnb** CSV files.
3.  Begin exploring the government open data portals listed in Part A.

---

## Technical Documentation

### Scraping Strategy
The `idealista_scraper.py` is designed to be robust, resilient, and difficult to detect.
- **Dynamic Scraping:** It uses `selenium` with `undetected-chromedriver` to control a real browser, allowing it to handle modern, JavaScript-heavy websites.
- **Anti-Detection:** It mimics human behavior by rotating `USER_AGENTS`, using randomized delays, and simulating page scrolling.
- **Batch Processing:** It scrapes in small, random batches, restarting the browser for each batch to avoid long sessions that can be flagged.
- **Configuration Management:** All file paths are managed in `scrapers/config.py` for easy configuration.
- **Resilience:** It saves progress incrementally and can be restarted without losing data, automatically skipping URLs that have already been processed.

### Project Structure
```
/gentrification_project
|-- /data
|   |-- /raw/barcelona/
|-- /scrapers
|   |-- _error_screenshots/
|   |-- config.py
|   |-- idealista_scraper.py
|-- /notebooks
|-- README.md
|-- requirements.txt```

### Setup & Installation

1.  **Clone the repository and create a virtual environment:**
    ```bash
    git clone <your-repo-url>
    cd gentrification_project
    python -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: `requirements.txt` includes both `selenium` (used in the current scraper) and `playwright` (recommended by our mentor for future scrapers).*

3.  **Install a browser for automation:** The current script uses **Chromium**.
    *   **On Arch/EndeavourOS:** `sudo pacman -S chromium`
    *   **On Debian/Ubuntu:** `sudo apt update && sudo apt install chromium-browser`

### How to Run the Idealista Scraper

Navigate to the `scrapers` directory and run the script from there.

```bash
cd scrapers
python idealista_scraper.py
```

The script will handle the rest, saving its output to the `/data/raw/barcelona` directory as defined in `config.py`.