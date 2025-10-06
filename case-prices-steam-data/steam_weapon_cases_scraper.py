import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
import random

class SteamMarketWeaponCasesScraper:
    def __init__(self, app_id=730):
        """
        Initialize the Steam Market weapon cases scraper
        
        Args:
            app_id: Steam App ID (730 for CS:GO/CS2)
        """
        self.app_id = app_id
        self.base_url = "https://steamcommunity.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://steamcommunity.com/'
        })
        
        # Calculate date threshold for last year
        self.one_year_ago = datetime.now() - timedelta(days=365)
        
        # Delay settings to avoid getting blocked
        self.delay_between_items = (5.0, 10.0)  # Random delay between items (min, max) in seconds
        self.delay_between_pages = (10.0, 15.0)  # Random delay between pages (min, max) in seconds
        self.rate_limit_backoff = 60  # Seconds to wait when hitting rate limit
    
    def get_items_from_page(self, page_url):
        """
        Get list of items from a specific page URL
        
        Args:
            page_url: Full URL of the page to scrape
            
        Returns:
            List of dictionaries with 'name' and 'url' keys
        """
        print(f"   Fetching items from page...")
        print(f"   URL: {page_url}")
        
        all_items = []
        
        try:
            # Add random delay to look more human
            delay = random.uniform(1.0, 2.0)
            print(f"Initial delay: {delay:.1f}s...")
            time.sleep(delay)
            
            response = self.session.get(page_url, timeout=20)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all item listings
                items = soup.find_all('a', class_='market_listing_row_link')
                
                if not items:
                    # Try alternative selector
                    print("Trying alternative selector...")
                    items = soup.find_all('a', href=re.compile(r'/market/listings/'))
                
                print(f"Found {len(items)} items on this page")
                
                for item in items:
                    try:
                        # Extract item URL
                        item_url = item.get('href', '')
                        
                        # Extract item name from URL
                        if '/market/listings/' in item_url:
                            # Get name from URL
                            item_name = item_url.split('/market/listings/' + str(self.app_id) + '/')[1]
                            item_name = unquote(item_name)
                            
                            # Clean up any query parameters
                            if '?' in item_name:
                                item_name = item_name.split('?')[0]
                            
                            all_items.append({
                                'name': item_name,
                                'url': item_url
                            })
                                
                    except Exception as e:
                        print(f"Error parsing item: {e}")
                        continue
                
                return all_items
            else:
                print(f"  HTTP Error {response.status_code}")
                return all_items
                
        except Exception as e:
            print(f"    Error fetching page: {e}")
            import traceback
            traceback.print_exc()
            return all_items
    
    def get_price_history(self, item_name, retry_count=0, max_retries=3):
        """
        Fetch price history for a specific item
        
        Args:
            item_name: Name of the item
            retry_count: Current retry attempt
            max_retries: Maximum number of retries
            
        Returns:
            List of dictionaries with date, price, volume
        """
        # First, visit the market page
        market_page_url = f"{self.base_url}/market/listings/{self.app_id}/{quote(item_name)}"
        
        try:
            # Get the main page to establish cookies
            page_response = self.session.get(market_page_url, timeout=20)
            
            if page_response.status_code == 429:
                # Rate limited - back off
                if retry_count < max_retries:
                    backoff_time = self.rate_limit_backoff * (retry_count + 1)
                    print(f"      Rate limited (429). Backing off for {backoff_time}s...")
                    time.sleep(backoff_time)
                    return self.get_price_history(item_name, retry_count + 1, max_retries)
                else:
                    print(f"      Max retries reached for rate limiting")
                    return None
            
            if page_response.status_code != 200:
                print(f"     Market page returned status {page_response.status_code}")
                return None
            
            time.sleep(random.uniform(1.0, 2.0))  # Random delay after successful request
            
            # Extract data from page source
            return self.extract_from_page_source(page_response.text, item_name)
                
        except Exception as e:
            print(f"      Error fetching price history for {item_name}: {e}")
            return None
    
    def extract_from_page_source(self, html, item_name):
        """
        Extract price history data from the HTML page source
        
        Args:
            html: HTML source of the market page
            item_name: Name of the item
            
        Returns:
            List of dictionaries with date, price, volume (filtered to last year)
        """
        try:
            # Look for the line_data variable in JavaScript
            pattern = r'var line1=(\[\[.*?\]\]);'
            match = re.search(pattern, html, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                
                try:
                    # Parse the JSON array
                    price_data = json.loads(json_str)
                    
                    if not price_data:
                        return None
                    
                    parsed_data = []
                    for entry in price_data:
                        try:
                            # Entry format: ["Mon, 01 Jan 2024 01:00:00 GMT", 1.23, "456"]
                            date_str = entry[0]
                            price = float(entry[1])
                            volume = int(entry[2]) if len(entry) > 2 else 0
                            
                            # Parse the date
                            date_obj = datetime.strptime(date_str, "%b %d %Y %H: +0")
                            
                            # Filter: only keep data from last year
                            if date_obj >= self.one_year_ago:
                                parsed_data.append({
                                    'item_name': item_name,
                                    'date': date_obj,
                                    'price': price,
                                    'volume': volume
                                })
                        except Exception as e:
                            continue
                    
                    if parsed_data:
                        print(f"      Extracted {len(parsed_data)} price points (last year)")
                        return parsed_data
                    else:
                        print(f"        No data from last year found")
                        return None
                        
                except json.JSONDecodeError as e:
                    print(f"      JSON parse error: {e}")
                    return None
            else:
                print(f"       Price data pattern not found in page")
                return None
            
        except Exception as e:
            print(f"        Error extracting from page source: {e}")
            return None
    
    def scrape_multiple_pages(self, page_urls, output_filename=None):
        """
        Scrape price history for items from multiple pages
        Saves data progressively after each item to avoid data loss
        
        Args:
            page_urls: List of page URLs to scrape
            output_filename: CSV filename to save progressively (auto-generated if None)
            
        Returns:
            pandas DataFrame with all price data
        """
        print("=" * 80)
        print("🎮 Steam Market Weapon Cases Price Scraper - CS:GO/CS2")
        print("=" * 80)
        print(f"\n  Configuration:")
        print(f"   Pages to scrape: {len(page_urls)}")
        print(f"   Delay between items: {self.delay_between_items[0]}-{self.delay_between_items[1]}s")
        print(f"   Delay between pages: {self.delay_between_pages[0]}-{self.delay_between_pages[1]}s")
        print(f"   Date filter: Last 365 days (from {self.one_year_ago.strftime('%Y-%m-%d')})")
        print(f"   Progressive saving:  ENABLED (saves after each item)")
        
        # Generate output filename
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"steam_weapon_cases_{timestamp}.csv"
        
        print(f"   Output file: {output_filename}")
        
        all_items = []
        
        # Step 1: Collect items from all pages
        print("\n" + "=" * 80)
        print(" Step 1: Collecting items from all pages...")
        print("=" * 80)
        
        for page_num, page_url in enumerate(page_urls, 1):
            print(f"\n[Page {page_num}/{len(page_urls)}]")
            items = self.get_items_from_page(page_url)
            
            if items:
                # Remove duplicates
                new_items = []
                existing_names = {item['name'] for item in all_items}
                for item in items:
                    if item['name'] not in existing_names:
                        new_items.append(item)
                        existing_names.add(item['name'])
                
                all_items.extend(new_items)
                print(f"    Added {len(new_items)} new items (Total: {len(all_items)})")
            
            # Delay before next page (except for last page)
            if page_num < len(page_urls):
                delay = random.uniform(*self.delay_between_pages)
                print(f"    Waiting {delay:.1f}s before next page...")
                time.sleep(delay)
        
        if not all_items:
            print("\n No items found!")
            return None
        
        print(f"\n Total unique items collected: {len(all_items)}")
        
        # Step 2: Scrape price history for each item with progressive saving
        print("\n" + "=" * 80)
        print(f" Step 2: Scraping price history for {len(all_items)} items...")
        print(f" Saving progressively to: {output_filename}")
        print("=" * 80)
        
        all_price_data = []
        scraped_items = []
        
        for idx, item in enumerate(all_items, 1):
            item_name = item['name']
            print(f"\n   [{idx}/{len(all_items)}]  {item_name}")
            
            price_data = self.get_price_history(item_name)
            
            if price_data:
                all_price_data.extend(price_data)
                scraped_items.append(item_name)
                print(f"      Total data points collected: {len(all_price_data):,}")
                
                # Save progressively after each successful scrape
                if all_price_data:
                    temp_df = pd.DataFrame(all_price_data)
                    temp_df = temp_df[['item_name', 'date', 'price']]
                    temp_df = temp_df.sort_values(['item_name', 'date']).reset_index(drop=True)
                    temp_df.to_csv(output_filename, index=False)
                    print(f"      Saved! ({len(scraped_items)} items, {len(all_price_data):,} records)")
            else:
                print(f"       No price data available (skipped)")
            
            # Delay before next item (except for last item)
            if idx < len(all_items):
                delay = random.uniform(*self.delay_between_items)
                print(f"      Waiting {delay:.1f}s before next item...")
                time.sleep(delay)
        
        # Step 3: Create final DataFrame
        if all_price_data:
            print("\n" + "=" * 80)
            print(" Step 3: Creating final dataset...")
            print("=" * 80)
            
            df = pd.DataFrame(all_price_data)
            
            # Select and order columns as requested: item_name, date, price
            df = df[['item_name', 'date', 'price']]
            df = df.sort_values(['item_name', 'date']).reset_index(drop=True)
            
            # Final save
            df.to_csv(output_filename, index=False)
            
            print(f"\n Dataset created successfully!")
            print(f"   Total records: {len(df):,}")
            print(f"   Unique items: {df['item_name'].nunique()}")
            print(f"   Successfully scraped items: {len(scraped_items)}/{len(all_items)}")
            print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"   Price range: ${df['price'].min():.2f} to ${df['price'].max():.2f}")
            
            return df
        else:
            print("\n❌ No price data collected")
            return None


def main():
    """Main function to run the weapon cases scraper for pages 3, 4, 5"""
    

    """ 
         Pages to scrape:
        "https://steamcommunity.com/market/search?appid=730&category_730_Type%5B%5D=tag_CSGO_Type_WeaponCase&start=0",
        "https://steamcommunity.com/market/search?appid=730&category_730_Type%5B%5D=tag_CSGO_Type_WeaponCase&start=10"
        "https://steamcommunity.com/market/search?appid=730&category_730_Type%5B%5D=tag_CSGO_Type_WeaponCase&start=20",
        "https://steamcommunity.com/market/search?appid=730&category_730_Type%5B%5D=tag_CSGO_Type_WeaponCase&start=30",
        "https://steamcommunity.com/market/search?appid=730&category_730_Type%5B%5D=tag_CSGO_Type_WeaponCase&start=40"
    """
    page_urls = [
        "https://steamcommunity.com/market/search?appid=730&category_730_Type%5B%5D=tag_CSGO_Type_WeaponCase&start=20",  # Page 3
        "https://steamcommunity.com/market/search?appid=730&category_730_Type%5B%5D=tag_CSGO_Type_WeaponCase&start=30",  # Page 4
        "https://steamcommunity.com/market/search?appid=730&category_730_Type%5B%5D=tag_CSGO_Type_WeaponCase&start=40"   # Page 5
    ]
    
    # Generate timestamped filename with page indicator
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"page345_steam_weapon_cases_{timestamp}.csv"
    
    # Initialize scraper
    scraper = SteamMarketWeaponCasesScraper(app_id=730)
    
    # Scrape all pages (data saved progressively)
    df = scraper.scrape_multiple_pages(page_urls, output_filename=output_filename)
    
    if df is not None and not df.empty:
        # Display sample data
        print("\n" + "=" * 80)
        print(" Sample data (first 10 rows):")
        print("=" * 80)
        print(df.head(10).to_string(index=False))
        
        print("\n" + "=" * 80)
        print(" Sample data (last 10 rows):")
        print("=" * 80)
        print(df.tail(10).to_string(index=False))
        
        # Show stats per item
        print("\n" + "=" * 80)
        print(" Records per item:")
        print("=" * 80)
        item_counts = df.groupby('item_name').size().sort_values(ascending=False)
        print(item_counts.to_string())
        
        print("\n" + "=" * 80)
        print(" Weapon cases scraping completed successfully!")
        print(f" Final data saved to: {output_filename}")
        print("=" * 80)
    else:
        print("\n Failed to retrieve price data")
    
    print("\n Script finished!")


if __name__ == "__main__":
    main()
