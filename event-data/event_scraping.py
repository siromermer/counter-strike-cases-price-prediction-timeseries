

"""
CS:GO/CS2 S-Tier Tournament Scraper
Scrapes tournament data from Liquipedia for the last year
This data can be used to correlate major events with price spikes
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re
import time

def parse_date_range(date_str):
    """
    Parse date strings like 'Nov 24 - Dec 14, 2025' or 'Jan 22 - 28, 2024'
    Returns start_date and end_date as datetime objects
    """
    try:
        # Handle cases like "Nov 24 - Dec 14, 2025" or "Nov 19 - 23, 2025"
        if ' - ' in date_str:
            parts = date_str.split(' - ')
            year = parts[1].split(', ')[-1].strip()
            
            # Start date
            start_parts = parts[0].strip().split()
            if len(start_parts) == 2:  # e.g., "Nov 24"
                start_month = start_parts[0]
                start_day = start_parts[1]
                start_date_str = f"{start_month} {start_day}, {year}"
            else:
                start_date_str = parts[0].strip() + f", {year}"
            
            # End date
            end_str = parts[1].strip()
            
            # Check if end has full date (Month Day, Year) or just (Day, Year)
            if ',' in end_str:
                end_parts_before_comma = end_str.split(',')[0].strip().split()
                
                if len(end_parts_before_comma) == 2:  # Has month and day e.g., "Dec 14"
                    end_date_str = end_str
                elif len(end_parts_before_comma) == 1:  # Only day e.g., "23"
                    # Use the same month as start date
                    end_day = end_parts_before_comma[0]
                    end_date_str = f"{start_month} {end_day}, {year}"
                else:
                    return None, None
            else:
                end_date_str = end_str + f", {year}"
            
            start_date = datetime.strptime(start_date_str, '%b %d, %Y')
            end_date = datetime.strptime(end_date_str, '%b %d, %Y')
            
            return start_date, end_date
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None, None
    
    return None, None

def scrape_tournaments():
    """
    Scrape S-Tier tournaments from Liquipedia
    Returns list of tournaments with name, date range, prize pool, location
    """
    url = "https://liquipedia.net/counterstrike/S-Tier_Tournaments"
    
    print(" Fetching tournament data from Liquipedia...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    tournaments = []
    
    # Find all gridRow divs (each row represents one tournament)
    tournament_rows = soup.find_all('div', class_='gridRow')
    
    print(f" Found {len(tournament_rows)} tournament rows")
    
    for row in tournament_rows:
        try:
            # Get all text content from the row
            text_content = row.get_text(separator='|', strip=True)
            
            # Only process 2024 and 2025 tournaments
            if '2024' not in text_content and '2025' not in text_content:
                continue
            
            # Extract tournament name from the Tournament Header div
            header_div = row.find('div', class_='Tournament')
            if not header_div:
                continue
            
            # Get all links and find the one with actual tournament name
            name_links = header_div.find_all('a', href=re.compile(r'/counterstrike/'))
            tournament_name = None
            
            for link in name_links:
                text = link.get_text(strip=True)
                if text and len(text) > 3:  # Avoid empty or very short names
                    tournament_name = text
            
            if not tournament_name:
                continue
            
            # Extract date using regex
            date_match = re.search(r'([A-Z][a-z]{2}\s+\d{1,2}(?:\s*-\s*(?:[A-Z][a-z]{2}\s+)?\d{1,2})?,\s*202[45])', text_content)
            
            if not date_match:
                continue
                
            date_str = date_match.group(1)
            
            # Parse dates
            start_date, end_date = parse_date_range(date_str)
            
            if not start_date or not end_date:
                continue
            
            # Extract prize pool
            prize_match = re.search(r'\$[\d,]+', text_content)
            prize_pool = prize_match.group(0) if prize_match else 'Unknown'
            
            # Extract location from flag image
            location = 'Unknown'
            flag_img = row.find('img', src=re.compile(r'.*hd\.png'))
            if flag_img and 'alt' in flag_img.attrs:
                location = flag_img['alt']
            
            tournaments.append({
                'tournament_name': tournament_name,
                'start_date': start_date,
                'end_date': end_date,
                'date_range': date_str,
                'prize_pool': prize_pool,
                'location': location
            })
            
        except Exception as e:
            # Continue silently as some rows may not have all data
            continue
    
    return tournaments

def filter_last_year(tournaments):
    """
    Filter tournaments to only include those from the last year
    """
    one_year_ago = datetime.now() - timedelta(days=365)
    
    filtered = [
        t for t in tournaments 
        if t['end_date'] >= one_year_ago
    ]
    
    # Sort by start date
    filtered.sort(key=lambda x: x['start_date'])
    
    return filtered

def main():
    print("=" * 80)
    print("CS:GO/CS2 S-Tier Tournament Scraper")
    print("=" * 80)
    
    # Scrape tournaments
    tournaments = scrape_tournaments()
    
    if not tournaments:
        print("\n❌ No tournaments found. The page structure might have changed.")
        print("Trying alternative parsing method...")
        
        # Alternative: Parse from tables directly
        # This will be implemented if the first method fails
        return
    
    print(f"\n Successfully extracted {len(tournaments)} tournaments")
    
    # Filter to last year
    one_year_ago = datetime.now() - timedelta(days=365)
    print(f"\n Filtering tournaments from {one_year_ago.date()} onwards...")
    
    last_year_tournaments = filter_last_year(tournaments)
    
    print(f" Found {len(last_year_tournaments)} tournaments in the last year")
    
    # Create DataFrame
    df = pd.DataFrame(last_year_tournaments)
    
    # Display summary
    print("\n" + "=" * 80)
    print(" TOURNAMENT SUMMARY (Last 12 Months)")
    print("=" * 80)
    
    for idx, tournament in enumerate(last_year_tournaments, 1):
        print(f"\n{idx}. {tournament['tournament_name']}")
        print(f"    Date: {tournament['start_date'].strftime('%Y-%m-%d')} to {tournament['end_date'].strftime('%Y-%m-%d')}")
        print(f"    Prize: {tournament['prize_pool']}")
        print(f"    Location: {tournament['location']}")
    
    # Save to CSV (with readable column names)
    df_to_save = df.copy()
    df_to_save['start_date'] = df_to_save['start_date'].dt.strftime('%Y-%m-%d')
    df_to_save['end_date'] = df_to_save['end_date'].dt.strftime('%Y-%m-%d')
    
    filename = f"csgo_stier_tournaments_last_year_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_to_save.to_csv(filename, index=False)
    
    print("\n" + "=" * 80)
    print(f" Saved to: {filename}")
    print(f" Total tournaments: {len(last_year_tournaments)}")
    print(f" Date range: {last_year_tournaments[0]['start_date'].date()} to {last_year_tournaments[-1]['end_date'].date()}")
    print("=" * 80)

if __name__ == "__main__":
    main()