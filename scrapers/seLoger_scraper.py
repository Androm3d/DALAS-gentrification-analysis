import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright

# --- Same anti-blocking helpers as before ---
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"

def random_delay(min_seconds=3, max_seconds=6):
    """Waits for a random amount of time. Longer default for SeLoger."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def scrape_seloger(start_url: str, max_pages: int = 2):
    """Scrapes property listings from SeLoger."""
    print(f"Starting scrape for SeLoger with URL: {start_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        # --- Part 1: Get listing URLs ---
        listing_urls = []
        current_url = start_url
        
        for page_num in range(1, max_pages + 1):
            # SeLoger pagination is often done by adding &page=N to the URL
            paginated_url = f"{current_url}&page={page_num}"
            print(f"Scraping search results page {page_num}: {paginated_url}")
            page.goto(paginated_url, timeout=90000)
            random_delay()

            # SeLoger often has a cookie banner to handle
            cookie_banner = page.locator('#onetrust-accept-btn-handler')
            if cookie_banner.count() > 0:
                print("Cookie banner found, accepting...")
                cookie_banner.click()
                random_delay(1,2)

            # SeLoger uses data-testid attributes which are more stable than class names
            page.wait_for_selector('[data-testid="listing-card-link"]')
            
            urls_on_page = page.locator('[data-testid="listing-card-link"]').evaluate_all(
                "elements => elements.map(element => element.href)"
            )
            listing_urls.extend(urls_on_page)
            print(f"Found {len(urls_on_page)} listings on this page.")

        print(f"\nFinished crawling. Found a total of {len(listing_urls)} unique listing URLs.")
        listing_urls = list(set(listing_urls)) # Remove duplicates

        # --- Part 2: Scrape details ---
        all_properties_data = []
        for i, url in enumerate(listing_urls):
            print(f"Scraping details from listing {i+1}/{len(listing_urls)}: {url}")
            try:
                page.goto(url, timeout=60000)
                random_delay(2, 4)

                page.wait_for_selector('[data-testid="sl.price-container"]')
                
                price = page.locator('[data-testid="sl.price-container"]').inner_text()
                
                # SeLoger characteristics are often in a div with this test id
                details_container = page.locator('[data-testid="sl.property-features-container"]')
                
                # These might not exist, so we use a helper function
                def get_detail_text(text_to_find):
                    element = details_container.locator(f'text=/{text_to_find}/')
                    return element.first.inner_text() if element.count() > 0 else "N/A"

                size_m2 = get_detail_text("m²")
                num_rooms = get_detail_text("pièce") # French for room
                num_bedrooms = get_detail_text("chambre") # French for bedroom
                location = page.locator('[data-testid="sl.address-container"]').inner_text()

                property_data = {
                    "url": url,
                    "price": price,
                    "size_m2": size_m2,
                    "num_rooms": num_rooms,
                    "num_bedrooms": num_bedrooms,
                    "location": location,
                }
                all_properties_data.append(property_data)

            except Exception as e:
                print(f"  -> Error scraping {url}: {e}")
                continue

        # --- Part 3: Save to CSV ---
        print("\nSaving data to CSV...")
        df = pd.DataFrame(all_properties_data)
        df.to_csv("seloger_listings.csv", index=False)
        print("Data saved to seloger_listings.csv")

        browser.close()

if __name__ == "__main__":
    # Example URL for buying a property in the 3rd arrondissement of Paris
    paris_3e_url = "https://www.seloger.com/list.htm?projects=2&types=1,2&places=[{ci:750103}]&sort=d_dt_crea&enterprise=0&qsVersion=1.0"
    scrape_seloger(paris_3e_url, max_pages=2)