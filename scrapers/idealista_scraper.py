import time
import random
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
import os
import re
import platform
import os
from pathlib import Path
# Import the configuration variables from our new config file
import config



USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
]


# --- HELPER FUNCTIONS ---

def random_delay(min_seconds=2, max_seconds=5):
    """Waits for a random amount of time to mimic human behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    print(f"Waiting {delay:.1f} seconds...")
    time.sleep(delay)

def human_like_scroll(driver):
    """Simulate human-like scrolling behavior."""
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight*0.1);")
    time.sleep(random.uniform(0.6, 1.2))
    total_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(1, int(random.uniform(3, 6))):
        scroll_to = total_height * (i / 5) + random.randint(-150, 150)
        driver.execute_script(f"window.scrollTo(0, {scroll_to});")
        time.sleep(random.uniform(0.8, 1.8))


def get_chrome_path():
    """
    Automatically detect Chrome/Chromium installation path based on OS.
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            str(Path.home() / "Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
    elif system == "Linux":
        paths = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/snap/bin/chromium",
        ]
    elif system == "Windows":
        paths = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            str(Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe"),
        ]
    else:
        paths = []
    
    for path in paths:
        if os.path.exists(path):
            print(f"✓ Found browser at: {path}")
            return path
    
    return None

# --- SCRAPING LOGIC ---

def scrape_idealista_undetected(start_url: str, max_pages: int = 10):
    """
    Scrapes property listing URLs from Idealista and returns them as a list.
    """
    print(f"Starting URL scrape for: {start_url}")
    
    options = uc.ChromeOptions()
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    chrome_path = get_chrome_path()
    
    try:
        if chrome_path:
            options.binary_location = chrome_path
            driver = uc.Chrome(options=options, use_subprocess=True)
        else:
            print("! No Chrome/Chromium found. Trying default installation...")
            driver = uc.Chrome(options=options, use_subprocess=True)
    except Exception as e:
        print(f"Error initializing driver: {e}")
        return []

    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32")
    
            
    try:
        listing_urls = []
        current_url = start_url
        
        for page_num in range(1, max_pages + 1):
            print(f"\n{'='*60}\nScraping search results page {page_num}...\n{'='*60}")
            
            try:
                driver.get(current_url)
                if page_num == 1:
                    try:
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))).click()
                        print("✓ Accepted cookies.")
                        time.sleep(random.uniform(1, 2))
                    except TimeoutException:
                        print("! No cookie banner found or it timed out.")
                
                random_delay(5, 10)
                human_like_scroll(driver)
                random_delay(2, 4)
                
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'article.item')))
                articles = driver.find_elements(By.CSS_SELECTOR, 'article.item a.item-link')
                urls_on_page = [a.get_attribute('href') for a in articles if a.get_attribute('href')]
                
                listing_urls.extend(urls_on_page)
                print(f"✓ Found {len(urls_on_page)} listings on this page.")
                
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, 'li.next a')
                    current_url = next_button.get_attribute('href')
                    if not current_url.startswith('http'):
                        current_url = f"https://www.idealista.com{current_url}"
                except NoSuchElementException:
                    print("✓ No 'Next' button found. Reached the last page.")
                    break
                
                random_delay(15, 25)
                
            except Exception as e:
                print(f"✗ Error on page {page_num}: {e}")
                # Use the new config path for error screenshots
                os.makedirs(config.ERROR_DIR, exist_ok=True)
                driver.save_screenshot(config.ERROR_DIR / f'error_page_{page_num}.png')
                break
        
        unique_urls = list(set(listing_urls))
        print(f"\n{'='*60}\n✓ URL scraping function complete!\n✓ Collected {len(unique_urls)} unique URLs in memory.\n{'='*60}")
        return unique_urls
        
    finally:
        driver.quit()
        print("\n✓ Browser for URL scraping closed.")

def extract_listing_details(driver):
    """
    Parses the detail page using multiple selector strategies for robustness.
    """
    data = {
        'price': None,
        'location_street': None,
        'location_neighborhood': None,
        'location_district': None,
        'surface_m2': None,
        'rooms': None,
        'bathrooms': None,
        'property_status': None,
        'year_built': None,
        'floor_level': None,
        'has_elevator': None,
        'energy_cert_consumption': None,
        'advertiser_type': None,
        'advertiser_name': None
    }
    
    # Check if listing still exists
    try:
        # Look for "not available" or error messages
        page_source = driver.page_source.lower()
        if 'no disponible' in page_source or 'not available' in page_source or 'error' in driver.title.lower():
            print("  ! Listing no longer available or page error")
            return data
    except:
        pass
    
    # Extract price
    try:
        data['price'] = driver.find_element(By.CSS_SELECTOR, "span.info-data-price span.txt-bold").text
    except NoSuchElementException:
        try:
            # Alternative price selector
            data['price'] = driver.find_element(By.CSS_SELECTOR, ".info-data-price").text.strip()
        except:
            print("  ! Price not found.")
    
    # Extract location details
    try:
        loc_elements = driver.find_elements(By.CSS_SELECTOR, "#headerMap ul li")
        if len(loc_elements) >= 3:
            data.update({
                'location_street': loc_elements[0].text,
                'location_neighborhood': loc_elements[1].text.replace('Barrio ', '').replace('Subdistrict ', ''),
                'location_district': loc_elements[2].text.replace('Distrito ', '').replace('District ', '')
            })
        elif len(loc_elements) == 2:
            data['location_neighborhood'] = loc_elements[0].text.replace('Barrio ', '').replace('Subdistrict ', '')
            data['location_district'] = loc_elements[1].text.replace('Distrito ', '').replace('District ', '')
    except Exception as e:
        print(f"  ! Location extraction error: {e}")
    
    # Extract property features - Try multiple selectors
    try:
        # First, try the main features section
        features_elements = driver.find_elements(By.CSS_SELECTOR, "div.details-property_features ul li")
        
        # If not found, try alternative selector
        if not features_elements:
            features_elements = driver.find_elements(By.CSS_SELECTOR, ".details-property-feature-one")
        
        # If still not found, try getting all text from details section
        if not features_elements:
            features_elements = driver.find_elements(By.CSS_SELECTOR, ".details-property_features span")
        
        print(f"  → Found {len(features_elements)} feature elements")
        
        for element in features_elements:
            try:
                text = element.text.lower().strip()
                if not text:
                    continue
                    
                print(f"  → Processing feature: {text}")
                
                # Extract number from text
                match = re.search(r'(\d+)', text)
                num = match.group(1) if match else None
                
                # Surface area
                if ('m²' in text or 'm2' in text or 'built' in text) and data['surface_m2'] is None and num:
                    data['surface_m2'] = int(num)
                    print(f"    ✓ Found surface: {num} m²")
                
                # Rooms/Bedrooms
                elif ('habitación' in text or 'bedroom' in text or 'room' in text) and data['rooms'] is None and num:
                    data['rooms'] = int(num)
                    print(f"    ✓ Found rooms: {num}")
                
                # Bathrooms
                elif ('baño' in text or 'bathroom' in text) and data['bathrooms'] is None and num:
                    data['bathrooms'] = int(num)
                    print(f"    ✓ Found bathrooms: {num}")
                
                # Property status
                elif any(s in text for s in ['segunda mano', 'second hand', 'buen estado', 'good condition', 'reformar', 'to reform', 'new development', 'obra nueva']) and data['property_status'] is None:
                    data['property_status'] = element.text
                    print(f"    ✓ Found status: {element.text}")
                
                # Year built
                elif ('construido' in text or 'built in' in text) and data['year_built'] is None and num:
                    data['year_built'] = int(num)
                    print(f"    ✓ Found year: {num}")
                
                # Floor level
                elif ('planta' in text or 'floor' in text) and data['floor_level'] is None and 'exterior' not in text:
                    data['floor_level'] = element.text
                    print(f"    ✓ Found floor: {element.text}")
                
                # Elevator
                elif 'ascensor' in text or 'elevator' in text or 'lift' in text:
                    data['has_elevator'] = 'con' in text or 'with' in text or text.startswith('elevator')
                    print(f"    ✓ Found elevator: {data['has_elevator']}")
                    
            except Exception as e:
                print(f"  ! Error processing feature element: {e}")
                continue
                
    except Exception as e:
        print(f"  ! Features section error: {e}")
    
    # Extract energy certificate
    try:
        cert_element = driver.find_element(By.CSS_SELECTOR, "div.details-property_features span[class*='icon-energy-c-']")
        cert_class = cert_element.get_attribute('class')
        match = re.search(r'icon-energy-c-([a-g])', cert_class)
        if match:
            data['energy_cert_consumption'] = match.group(1).upper()
            print(f"  ✓ Found energy cert: {data['energy_cert_consumption']}")
    except NoSuchElementException:
        # Try alternative selector
        try:
            cert_text = driver.find_element(By.CSS_SELECTOR, ".energy-certificate").text
            match = re.search(r'\b([A-G])\b', cert_text)
            if match:
                data['energy_cert_consumption'] = match.group(1)
        except:
            pass
    
    # Extract advertiser info
    try:
        data['advertiser_type'] = driver.find_element(By.CSS_SELECTOR, "div.professional-name .name").text
        data['advertiser_name'] = driver.find_element(By.CSS_SELECTOR, "div.professional-name span").text
        print(f"  ✓ Found advertiser: {data['advertiser_type']} - {data['advertiser_name']}")
    except NoSuchElementException:
        try:
            # Alternative selector for advertiser
            advertiser_elem = driver.find_element(By.CSS_SELECTOR, ".advertiser-data")
            data['advertiser_type'] = advertiser_elem.text
        except:
            data['advertiser_type'] = 'Particular'
            print(f"  ✓ Defaulting to Particular")
    
    return data


def scrape_details_in_batches(listing_urls: list, batch_size_min: int, batch_size_max: int):
    """
    Scrapes property details in batches with improved error handling.
    """
    urls_to_scrape = list(listing_urls)
    os.makedirs(config.BARCELONA_DATA_DIR, exist_ok=True)
    
    # Load already scraped URLs
    if os.path.exists(config.DETAILS_FILE) and os.path.getsize(config.DETAILS_FILE) > 0:
        try:
            completed_df = pd.read_csv(config.DETAILS_FILE)
            if 'url' in completed_df.columns:
                completed_urls = set(completed_df['url'])
                print(f"✓ Found {len(completed_urls)} already scraped URLs. They will be skipped.")
                urls_to_scrape = [url for url in urls_to_scrape if url not in completed_urls]
            else:
                print(f"! Details file is malformed. Starting fresh.")
                os.remove(config.DETAILS_FILE)
        except Exception:
            print(f"! Details file is empty or malformed. Starting fresh.")
    else:
        print(f"Starting a new details scrape to {config.DETAILS_FILE}")

    print(f"Total new listings to scrape: {len(urls_to_scrape)}")
    
    # Check for Chrome
    chrome_path = get_chrome_path()
    if not chrome_path:
        print("ERROR: Could not find Chrome or Chromium browser!")
        return

    batch_num = 0
    failed_urls = []  # Track failed URLs

    while urls_to_scrape:
        batch_num += 1
        current_batch_size = random.randint(batch_size_min, batch_size_max)
        batch_urls, urls_to_scrape = urls_to_scrape[:current_batch_size], urls_to_scrape[current_batch_size:]

        print(f"\n{'='*60}\nProcessing Batch {batch_num} ({len(batch_urls)} URLs)\n{'='*60}")
        
        options = uc.ChromeOptions()
        options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        options.binary_location = chrome_path
        
        driver = uc.Chrome(options=options, use_subprocess=True)
        stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32")
        
        batch_data = []
        try:
            for idx, url in enumerate(batch_urls, 1):
                print(f"\n[{idx}/{len(batch_urls)}] Scraping: {url}")
                try:
                    driver.get(url)
                    time.sleep(random.uniform(4, 7))
                    human_like_scroll(driver)
                    time.sleep(random.uniform(3, 5))
                    
                    scraped_data = extract_listing_details(driver)
                    scraped_data['url'] = url
                    
                    # Only save if we got at least some data (price exists)
                    if scraped_data['price']:
                        batch_data.append(scraped_data)
                        print(f"  ✓ Successfully extracted listing data")
                    else:
                        print(f"  ⚠ Listing appears to be unavailable or deleted")
                        failed_urls.append(url)
                        # Still save the URL so we don't retry it
                        batch_data.append(scraped_data)
                        
                except Exception as e:
                    print(f"  ✗ UNEXPECTED ERROR scraping listing {url}: {e}")
                    os.makedirs(config.ERROR_DIR, exist_ok=True)
                    driver.save_screenshot(config.ERROR_DIR / f'error_listing_{batch_num}_{idx}.png')
                    failed_urls.append(url)
                    continue
        finally:
            driver.quit()

        # Save batch data
        if batch_data:
            df = pd.DataFrame(batch_data)
            header_exists = os.path.exists(config.DETAILS_FILE) and os.path.getsize(config.DETAILS_FILE) > 0
            df.to_csv(config.DETAILS_FILE, mode='a', header=not header_exists, index=False)
            print(f"✓ Saved {len(batch_data)} records to CSV")

        if urls_to_scrape:
            print("\n--- Taking a long break between batches... ---")
            random_delay(90, 150)
    
    # Summary
    print(f"\n{'='*60}\n✓ All scraping complete.\n{'='*60}")
    if failed_urls:
        print(f"⚠ {len(failed_urls)} URLs failed or were unavailable")
        print("Failed URLs saved in the CSV with null values")

# --- MAIN ORCHESTRATION BLOCK ---

if __name__ == "__main__":
    MIN_LISTINGS = 200
    os.makedirs(config.BARCELONA_DATA_DIR, exist_ok=True)
    existing_urls = set()
    run_url_scraper = True

    # Check if we already have enough URLs
    if os.path.exists(config.URL_FILE) and os.path.getsize(config.URL_FILE) > 0:
        try:
            existing_df = pd.read_csv(config.URL_FILE)
            existing_urls = set(existing_df['listing_url'])
            if len(existing_urls) >= MIN_LISTINGS:
                print(f"✓ Found {len(existing_urls)} URLs, which meets the minimum of {MIN_LISTINGS}.")
                run_url_scraper = False
            else:
                print(f"! Only {len(existing_urls)}/{MIN_LISTINGS} URLs found. Will scrape for more.")
        except Exception:
            print(f"! URL file is empty or corrupted. Will scrape for URLs.")
    else:
        print(f"URL file not found or is empty. Will scrape for URLs.")

    # Run URL scraper if needed
    if run_url_scraper:
        print("\n--- Starting URL Scraping ---")
        base_url = "https://www.idealista.com/en/venta-viviendas/barcelona/ciutat-vella/"
        url_price_asc = base_url + "?ordenado-por=fecha-publicacion-desc" 
        newly_scraped_urls = scrape_idealista_undetected(url_price_asc, max_pages=7)
        all_urls = existing_urls.union(set(newly_scraped_urls))
        
        if all_urls:
            print(f"\nSaving {len(all_urls)} total unique URLs to {config.URL_FILE}...")
            df = pd.DataFrame({'listing_url': list(all_urls)})
            df.to_csv(config.URL_FILE, index=False)
            print("✓ Save complete.")
        else:
            print("! No new URLs were scraped. File not updated.")

    # FIXED: Always load URLs for detail scraping, regardless of whether we just scraped them
    print("\n--- Starting Detail Scraping ---")
    try:
        print(f"DEBUG: About to read from: {config.URL_FILE}")
        listings_df = pd.read_csv(config.URL_FILE).drop_duplicates()
        print(f"DEBUG: Successfully read {len(listings_df)} rows")
        listing_urls = listings_df['listing_url'].tolist()
        print(f"DEBUG: Converted to {len(listing_urls)} URLs")
        
        if listing_urls:
            print(f"✓ Loaded {len(listing_urls)} URLs for detail scraping.")
            scrape_details_in_batches(listing_urls, batch_size_min=5, batch_size_max=9)
        else:
            print("! No URLs found in the file to scrape for details.")
            
    except FileNotFoundError as e:
        print(f"ERROR: FileNotFoundError - {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()