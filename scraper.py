import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import urllib.parse
import re
import os

async def run_scraper(cities: list, categories: list, log_callback=None):
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    results_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Headless=False to avoid some bot detections/let user see visually if needed
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        for city in cities:
            for category in categories:
                log(f"\n--- Starting extraction for: {category} in {city} ---")
                search_query = f"{category} in {city}"
                encoded_query = urllib.parse.quote_plus(search_query)
                url = f"https://www.google.com/maps/search/{encoded_query}/"
                
                log(f"Navigating to {url}")
                try:
                    await page.goto(url, timeout=60000)
                except Exception as e:
                    log(f"Navigation failed for {category} in {city}: {e}")
                    continue
                
                # Wait for the feed to load
                try:
                    feed_selector = 'div[role="feed"]'
                    await page.wait_for_selector(feed_selector, timeout=60000)
                except Exception as e:
                    log(f"Could not find results for {category} in {city}. Google Maps may have blocked the request or no results found.")
                    continue
                    
                log(f"Results loaded for {category} in {city}. Scrolling to fetch more...")
                
                # Scroll logic
                previous_count = 0
                attempts = 0
                max_attempts = 15 # Guard against infinite loops
                
                while attempts < max_attempts:
                    # Look for all item containers inside the feed
                    elements = await page.query_selector_all('div[role="feed"] > div > div > a')
                    current_count = len(elements)
                    
                    # Let's scroll the feed down
                    await page.evaluate(f'''
                        const feed = document.querySelector('{feed_selector}');
                        feed.scrollTo(0, feed.scrollHeight);
                    ''')
                    
                    await asyncio.sleep(2) # Wait for new results to append
                    
                    # Check if "You've reached the end of the list." is present
                    end_of_list = await page.query_selector('text="You\'ve reached the end of the list."')
                    if end_of_list:
                        log(f"Reached the end of the results for {category} in {city}.")
                        break
                        
                    if current_count == previous_count:
                        attempts += 1
                    else:
                        attempts = 0
                        previous_count = current_count
                        log(f"Loaded {current_count} items for {category} in {city}...")
                        
                # Now collect all hrefs from the loaded list to visit them individually
                log(f"Extracting business links for {category} in {city}...")
                locators = await page.locator('div[role="feed"] > div > div > a').all()
                hrefs = []
                for loc in locators:
                    href = await loc.get_attribute('href')
                    if href and "/maps/place/" in href:
                        hrefs.append(href)
                        
                # Remove duplicates
                hrefs = list(set(hrefs))
                log(f"Found {len(hrefs)} unique businesses to extract for {category} in {city}.")
                
                # Now visit each place and extract required info
                for index, item_url in enumerate(hrefs, start=1):
                    log(f"Extracting {category} in {city} {index}/{len(hrefs)}...")
                    try:
                        # Open in a new tab or use same tab
                        await page.goto(item_url, timeout=60000)
                        await asyncio.sleep(1) # Extra buffer
                        
                        # Title
                        name_locator = page.locator('h1').first
                        name = await name_locator.inner_text() if await name_locator.count() > 0 else "Unknown"
                        
                        # Phone number usually has a specific image or format
                        # Usually it has data-item-id starting with "phone:"
                        phone_loc = page.locator('button[data-tooltip="Copy phone number"]').first
                        number = await phone_loc.inner_text() if await phone_loc.count() > 0 else "N/A"
                        if number != "N/A":
                            number = number.replace("", "").strip() # Remove material icon if present
                        
                        # Copy address 
                        address_loc = page.locator('button[data-tooltip="Copy address"]').first
                        location = await address_loc.inner_text() if await address_loc.count() > 0 else "N/A"
                        if location != "N/A":
                            location = location.replace("", "").strip()

                        # Website
                        website_loc = page.locator('a[data-tooltip="Open website"]').first
                        website = await website_loc.get_attribute('href') if await website_loc.count() > 0 else "N/A"
                        
                        results_data.append({
                            "Search City": city,
                            "Search Category": category,
                            "Name": name,
                            "Website": website,
                            "Phone Number": number,
                            "Location": location
                        })
                    except Exception as e:
                        log(f"  Error extracting detail: {e}")
                        continue
                        
        await browser.close()
        
        # Save to Excel
        if results_data:
            df = pd.DataFrame(results_data)
            categories_str = "_".join(categories)[:50] 
            safe_cat_name = "".join([c if c.isalnum() else "_" for c in categories_str])
            filename = f"Batch_Extraction_{safe_cat_name}_leads.xlsx"
            filepath = os.path.join(os.getcwd(), filename)
            df.to_excel(filepath, index=False)
            log(f"Successfully saved {len(results_data)} records to {filepath}")
            return filepath, len(results_data)
        else:
            raise Exception("No business data was extracted.")
