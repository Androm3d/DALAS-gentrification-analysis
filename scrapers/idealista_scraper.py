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
import math
from pathlib import Path

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

def scrape_idealista_undetected(start_url: str, target_count: int = 0):
    """
    Scrapes property listing URLs.
    Args:
        start_url: The search page URL.
        target_count: How many new listings we aim to find (controls max_pages).
    """
    print(f"Starting URL scrape for: {start_url}")
    
    # Calculate pages needed (approx 30 listings per page on Idealista)
    # We add a 20% buffer because of potential duplicates or ads
    if target_count > 0:
        est_pages = math.ceil((target_count / 30) * 1.2)
        # Idealista usually caps at ~60 pages for a single query
        max_pages = min(est_pages, 60) 
        print(f"Aiming for {target_count} listings. Will scrape approx {max_pages} pages.")
    else:
        max_pages = 5 # Default fallback
    
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
            driver = uc.Chrome(options=options, use_subprocess=True)
    except Exception as e:
        print(f"Error initializing driver: {e}")
        return []

    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32")
    
    unique_urls = set()
    
    try:
        current_url = start_url
        
        for page_num in range(1, max_pages + 1):
            print(f"\n{'='*60}\nScraping search results page {page_num}/{max_pages}...\n{'='*60}")
            
            try:
                driver.get(current_url)
                
                # Cookie Banner Handling (Page 1 only)
                if page_num == 1:
                    try:
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))).click()
                        print("✓ Accepted cookies.")
                        time.sleep(random.uniform(1, 2))
                    except TimeoutException:
                        print("! No cookie banner found or it timed out.")
                
                random_delay(3, 5)
                human_like_scroll(driver)
                
                # Wait for items to load
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'article.item')))
                articles = driver.find_elements(By.CSS_SELECTOR, 'article.item a.item-link')
                
                # Extract URLs
                urls_on_page = [a.get_attribute('href') for a in articles if a.get_attribute('href')]
                new_urls_count = 0
                
                # --- INCREMENTAL SAVE ---
                # We save immediately so we don't lose progress during the next long sleep
                if urls_on_page:
                    # Append to file immediately
                    header_needed = not os.path.exists(config.MILAN_URL_FILE)
                    df_page = pd.DataFrame({'listing_url': urls_on_page})
                    df_page.to_csv(config.MILAN_URL_FILE, mode='a', header=header_needed, index=False)
                    
                    unique_urls.update(urls_on_page)
                    new_urls_count = len(urls_on_page)
                    print(f"✓ Found and SAVED {new_urls_count} listings on this page.")
                
                # Check if we should stop
                if len(unique_urls) >= target_count and target_count > 0:
                    print(f"✓ Hit target of {target_count} new listings. Stopping.")
                    break

                # Pagination
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, 'li.next a')
                    current_url = next_button.get_attribute('href')
                    if not current_url.startswith('http'):
                        current_url = f"https://www.idealista.com{current_url}"
                except NoSuchElementException:
                    print("✓ No 'Next' button found. Reached the last page.")
                    break
                
                random_delay(7, 15)
                
            except Exception as e:
                print(f"✗ Error on page {page_num}: {e}")
                os.makedirs(config.ERROR_DIR, exist_ok=True)
                driver.save_screenshot(config.ERROR_DIR / f'error_page_{page_num}.png')
                break
        
        return list(unique_urls)
        
    finally:
        driver.quit()
        print("\n✓ Browser for URL scraping closed.")

def extract_listing_details(driver):
    """
    Parses the detail page. Updated to support both Spanish (ES) and Italian (IT) keywords.
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
        page_source = driver.page_source.lower()
        if any(x in page_source for x in ['no disponible', 'not available', 'non disponibile']) or 'error' in driver.title.lower():
            print("  ! Listing no longer available or page error")
            return data
    except:
        pass
    
    # Extract price
    try:
        data['price'] = driver.find_element(By.CSS_SELECTOR, "span.info-data-price span.txt-bold").text
    except NoSuchElementException:
        try:
            data['price'] = driver.find_element(By.CSS_SELECTOR, ".info-data-price").text.strip()
        except:
            print("  ! Price not found.")
    
    # Extract location details (Handles ES 'Barrio/Distrito' and IT 'Zona/Quartiere')
    try:
        loc_elements = driver.find_elements(By.CSS_SELECTOR, "#headerMap ul li")
        if len(loc_elements) >= 3:
            data['location_street'] = loc_elements[0].text
            data['location_neighborhood'] = loc_elements[1].text
            data['location_district'] = loc_elements[2].text
        elif len(loc_elements) == 2:
            data['location_neighborhood'] = loc_elements[0].text
            data['location_district'] = loc_elements[1].text
            
        # Cleanup common prefixes (ES & IT)
        for key in ['location_neighborhood', 'location_district']:
            if data[key]:
                data[key] = (data[key]
                             .replace('Barrio ', '').replace('Distrito ', '')  # ES
                             .replace('Quartiere ', '').replace('Zona ', '')   # IT
                             .replace('District ', '').replace('Subdistrict ', '') # EN
                             .strip())
    except Exception as e:
        print(f"  ! Location extraction error: {e}")
    
    # Extract property features
    try:
        features_elements = driver.find_elements(By.CSS_SELECTOR, "div.details-property_features ul li")
        if not features_elements:
            features_elements = driver.find_elements(By.CSS_SELECTOR, ".details-property-feature-one")
        
        print(f"  → Found {len(features_elements)} feature elements")
        
        for element in features_elements:
            try:
                text = element.text.lower().strip()
                if not text: continue
                    
                match = re.search(r'(\d+)', text)
                num = match.group(1) if match else None
                
                # Surface area
                if ('m²' in text or 'm2' in text or 'built' in text) and data['surface_m2'] is None and num:
                    data['surface_m2'] = int(num)
                    print(f"    ✓ Found surface: {num}")
                
                # Rooms (ES: habitacion, IT: locali/camere, EN: bedroom/room)
                elif any(x in text for x in ['habitación', 'bedroom', 'room', 'locali', 'camere', 'camera']) and data['rooms'] is None and num:
                    data['rooms'] = int(num)
                    print(f"    ✓ Found rooms: {num}")
                
                # Bathrooms (ES: baño, IT: bagno/bagni, EN: bathroom)
                elif any(x in text for x in ['baño', 'bathroom', 'bagno', 'bagni']) and data['bathrooms'] is None and num:
                    data['bathrooms'] = int(num)
                    print(f"    ✓ Found bathrooms: {num}")
                
                # Status (ES/IT mix)
                elif any(s in text for s in [
                    'segunda mano', 'second hand', 'buen estado', 'good condition', 'reformar', 'to reform', 'new development', 'obra nueva',
                    'buono stato', 'da ristrutturare', 'nuova costruzione' # IT keywords
                ]) and data['property_status'] is None:
                    data['property_status'] = element.text
                    print(f"    ✓ Found status: {element.text}")
                
                # Year built (ES: construido, IT: costruito)
                elif ('construido' in text or 'built' in text or 'costruito' in text) and data['year_built'] is None and num:
                    data['year_built'] = int(num)
                    print(f"    ✓ Found year: {num}")
                
                # Floor level (ES: planta, IT: piano)
                elif ('planta' in text or 'floor' in text or 'piano' in text) and data['floor_level'] is None and 'exterior' not in text:
                    data['floor_level'] = element.text
                    print(f"    ✓ Found floor: {element.text}")
                
                # Elevator (ES: ascensor, IT: ascensore)
                elif any(x in text for x in ['ascensor', 'elevator', 'lift', 'ascensore']):
                    data['has_elevator'] = 'con' in text or 'with' in text or text.startswith('elevator') or text.startswith('ascensore')
                    print(f"    ✓ Found elevator: {data['has_elevator']}")
                    
            except Exception:
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
    except NoSuchElementException:
        pass
    
    # Extract advertiser
    try:
        data['advertiser_type'] = driver.find_element(By.CSS_SELECTOR, "div.professional-name .name").text
        data['advertiser_name'] = driver.find_element(By.CSS_SELECTOR, "div.professional-name span").text
    except:
        data['advertiser_type'] = 'Particular'
    
    return data


def scrape_details_in_batches(listing_urls: list, batch_size_min: int, batch_size_max: int):
    """
    Scrapes property details with a PERSISTENT driver session.
    """
    urls_to_scrape = list(listing_urls)
    os.makedirs(config.BARCELONA_DATA_DIR, exist_ok=True)
    
    # 1. Filter already scraped URLs
    if os.path.exists(config.MILAN_DETAILS_FILE) and os.path.getsize(config.MILAN_DETAILS_FILE) > 0:
        try:
            completed_df = pd.read_csv(config.MILAN_DETAILS_FILE)
            if 'url' in completed_df.columns:
                completed_urls = set(completed_df['url'])
                print(f"✓ Found {len(completed_urls)} already scraped URLs. Skipping.")
                urls_to_scrape = [url for url in urls_to_scrape if url not in completed_urls]
        except Exception:
            pass

    print(f"Total new listings to scrape: {len(urls_to_scrape)}")
    
    chrome_path = get_chrome_path()
    if not chrome_path:
        return

    # --- 2. INITIALIZE DRIVER ONCE (OUTSIDE THE LOOP) ---
    # Pick ONE User Agent for the entire session
    selected_ua = random.choice(USER_AGENTS)
    print(f"✓ Session User Agent: {selected_ua}")

    options = uc.ChromeOptions()
    options.add_argument(f"user-agent={selected_ua}")
    options.binary_location = chrome_path
    
    # Optional: Use a persistent profile to save cookies between runs
    # options.add_argument(f"--user-data-dir={os.getcwd()}/chrome_profile") 

    driver = uc.Chrome(options=options, use_subprocess=True)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32")

    try:
        batch_num = 0
        while urls_to_scrape:
            batch_num += 1
            current_batch_size = random.randint(batch_size_min, batch_size_max)
            batch_urls = urls_to_scrape[:current_batch_size]
            urls_to_scrape = urls_to_scrape[current_batch_size:]  # Remove processed URLs from main list

            print(f"\n{'='*60}\nProcessing Batch {batch_num} ({len(batch_urls)} URLs)\n{'='*60}")
            
            batch_data = []
            
            for idx, url in enumerate(batch_urls, 1):
                print(f"\n[{idx}/{len(batch_urls)}] Scraping: {url}")
                try:
                    driver.get(url)
                    
                    # Short delays between items in a batch
                    time.sleep(random.uniform(2, 4))
                    human_like_scroll(driver)
                    time.sleep(random.uniform(1, 3))
                    
                    scraped_data = extract_listing_details(driver)
                    scraped_data['url'] = url
                    
                    if scraped_data['price']:
                        batch_data.append(scraped_data)
                        print(f"  ✓ Extracted")
                    else:
                        print(f"  ⚠ Unavailable")
                        # You might want to remove this URL from future runs even if failed
                        batch_data.append(scraped_data) 
                        
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    continue

            # Save batch data
            if batch_data:
                df = pd.DataFrame(batch_data)
                header_exists = os.path.exists(config.MILAN_DETAILS_FILE) and os.path.getsize(config.MILAN_DETAILS_FILE) > 0
                df.to_csv(config.MILAN_DETAILS_FILE, mode='a', header=not header_exists, index=False)
                print(f"✓ Saved batch to CSV")

            if urls_to_scrape:
                print("\n--- Taking a long break (Driver remains open)... ---")
                # 3. WAIT WITH DRIVER OPEN
                # This looks like a user reading a page or taking a break, 
                # rather than a bot restarting.
                
                # Optional: Visit a "safe" page during the break to keep session alive 
                # but idle, or just stay on the last listing.
                random_delay(30, 90)

    except Exception as e:
        print(f"Critical Error: {e}")
    finally:
        # Only close when EVERYTHING is done or crashed
        driver.quit()
        print("\n✓ Scraping finished. Browser closed.")
        

# --- MAIN ORCHESTRATION BLOCK ---
if __name__ == "__main__":
    # --- CONFIG FOR MILAN ---
    MIN_LISTINGS = 1000
    # ------------------------
    
    current_urls = set()
    run_url_scraper = True

    # 1. Check existing URLs
    if os.path.exists(config.MILAN_URL_FILE) and os.path.getsize(config.MILAN_URL_FILE) > 0:
        try:
            existing_df = pd.read_csv(config.MILAN_URL_FILE)
            current_urls = set(existing_df['listing_url'])
            if len(current_urls) >= MIN_LISTINGS:
                print(f"✓ Found {len(current_urls)} URLs. Skipping URL scraping.")
                run_url_scraper = False
            else:
                print(f"! Found {len(current_urls)} URLs. Need more.")
        except Exception as e:
            print(f"Error reading existing URLs: {e}")
            pass
    else:
        print("! No existing URL file found. Will run URL scraper.")

    # 2. Run URL Scraper
    if run_url_scraper:
        needed = MIN_LISTINGS - len(current_urls)
        target = needed if needed > 0 else MIN_LISTINGS
        
        print(f"\n--- Starting URL Scraping for MILAN ({target} listings) ---")
        
        # URL for Milan, sorted by newest
        base_url = "https://www.idealista.it/en/vendita-case/milano-milano/"
        url_newest = base_url + "?ordine=pubblicazione-desc"
        
        scrape_idealista_undetected(url_newest, target_count=target)
        
        if os.path.exists(config.MILAN_URL_FILE):
             current_urls = set(pd.read_csv(config.MILAN_URL_FILE)['listing_url'])

    # 3. Detail Scraping
    print("\n--- Starting Detail Scraping ---")
    listing_urls = list(current_urls)
    
    if listing_urls:
        print(f"✓ Loaded {len(listing_urls)} URLs for detail scraping.")
        scrape_details_in_batches(listing_urls, batch_size_min=5, batch_size_max=9)
    else:
        print("! No URLs found to scrape.")
