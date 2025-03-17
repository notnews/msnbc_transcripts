#!/usr/bin/env python
# coding: utf-8
import os
import logging
import scrapelib
from bs4 import BeautifulSoup
from dateutil import parser
import csv
from datetime import datetime
import re
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("msnbc_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define columns for the CSV output
columns = [
    'air_date', 'show_name', 'headline', 'guests', 'url',
    'channel.name', 'program.name', 'uid', 'duration',
    'year', 'month', 'date', 'time', 'timezone', 'path',
    'wordcount', 'subhead', 'summary', 'text'
]

def extract_date_from_url(url):
    """Extract date from URL when time tag is missing or invalid."""
    # Look for patterns like 'august-12-2020' in the URL
    date_match = re.search(r'(?:january|february|march|april|may|june|july|august|september|october|november|december)-(\d{1,2})-(\d{4})', url, re.IGNORECASE)
    if date_match:
        month_name = date_match.group(0).split('-')[0]
        day = date_match.group(1)
        year = date_match.group(2)
        date_str = f"{month_name} {day} {year}"
        try:
            return parser.parse(date_str)
        except:
            pass
    return None

def extract_transcript(html, data):
    """Extract transcript content and metadata from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Try to get date from time tag
    time_tag = soup.find('time')
    date_obj = None
    
    if time_tag and time_tag.text.strip():
        try:
            # Try parsing the date from time tag
            date_obj = parser.parse(time_tag.text, fuzzy=True)
            logger.info(f"Date parsed from time tag: {date_obj}")
        except Exception as e:
            logger.warning(f"Could not parse date from time tag: {e}")
    
    # If date parsing from time tag failed, try extract from URL
    if not date_obj and 'url' in data:
        date_obj = extract_date_from_url(data['url'])
        if date_obj:
            logger.info(f"Date extracted from URL: {date_obj}")
    
    # If still no date, try using air_date
    if not date_obj and 'air_date' in data and data['air_date']:
        try:
            date_obj = parser.parse(data['air_date'], fuzzy=True)
            logger.info(f"Date parsed from air_date: {date_obj}")
        except Exception as e:
            logger.warning(f"Could not parse date from air_date: {e}")
    
    # If all date parsing methods failed, use current date
    if not date_obj:
        date_obj = datetime.now()
        logger.warning(f"Using current date as fallback: {date_obj}")
    
    # Get content
    content_div = soup.find("div", {"class": "article-body__content"})
    if not content_div:
        logger.warning("Could not find article body content")
        return data
    
    # Extract summary if available
    summary = ""
    summary_anchor = content_div.find('a', {'id': 'anchor-Summary'})
    if summary_anchor and summary_anchor.next_sibling:
        summary = summary_anchor.next_sibling.text.strip()
    
    # Extract transcript
    content_text = ""
    transcript_anchor = content_div.find('a', {'id': 'anchor-Transcript'})
    if transcript_anchor:
        # Get all siblings after the transcript anchor
        siblings = []
        for sibling in transcript_anchor.next_siblings:
            if sibling.name and sibling.get_text().strip():
                siblings.append(sibling.get_text().strip())
        content_text = '\n'.join(siblings)
    else:
        # If no transcript anchor, use the whole content
        content_text = content_div.get_text().strip()
    
    # Calculate word count
    word_count = len(content_text.split()) if content_text else 0
    
    # Prepare the data
    data['channel.name'] = 'MSNBC'
    data['program.name'] = data.get('headline', '')
    data['year'] = date_obj.year
    data['month'] = date_obj.month
    data['date'] = date_obj.day
    data['time'] = f"{date_obj.hour:02d}:{date_obj.minute:02d}"
    data['timezone'] = 'UTC'
    data['subhead'] = ''
    data['summary'] = summary
    data['text'] = content_text
    data['wordcount'] = word_count
    
    # Generate UID from URL if not present
    if 'url' in data and not 'uid' in data:
        data['uid'] = data['url'].split('/')[-1] if '/' in data['url'] else data['url']
    
    return data

def find_max_page():
    """Find the maximum page number to ensure we scrape up to today."""
    try:
        s = scrapelib.Scraper(requests_per_minute=60)
        # Start with a high page number and check if it exists
        page = 1000  # A high number to start with
        
        # Binary search to find the highest valid page
        low, high = 1, page
        max_page = 1
        
        while low <= high:
            mid = (low + high) // 2
            logger.info(f"Checking if page {mid} exists...")
            
            try:
                url = f'https://www.msnbc.com/transcripts?sort=datePublished:asc&page={mid}'
                res = s.get(url)
                soup = BeautifulSoup(res.text, "html.parser")
                
                # Check if the page has transcript cards
                cards = soup.find_all("div", {"class": "transcript-card"})
                
                if cards:
                    # This page exists, try a higher page
                    max_page = mid
                    low = mid + 1
                    logger.info(f"Page {mid} exists with {len(cards)} transcripts")
                else:
                    # No cards found, try a lower page
                    high = mid - 1
                    logger.info(f"Page {mid} has no transcripts")
                
                # Add a small delay to avoid hitting rate limits
                time.sleep(1)
                
            except Exception as e:
                # Error accessing the page, try a lower page
                logger.warning(f"Error checking page {mid}: {e}")
                high = mid - 1
                time.sleep(2)  # Longer delay after an error
        
        logger.info(f"Maximum page found: {max_page}")
        return max_page
        
    except Exception as e:
        logger.error(f"Error finding max page: {e}")
        return 485  # Default to the original max page if there's an error

def main():
    """Main function to run the scraper."""
    OUTPUT_FILE = "msnbc_transcripts.csv"
    new_file = not os.path.exists(OUTPUT_FILE)
    
    # Create directory if needed
    os.makedirs(os.path.dirname(OUTPUT_FILE) if os.path.dirname(OUTPUT_FILE) else '.', exist_ok=True)
    
    # Find the maximum page number to ensure we get everything up to today
    end_page = find_max_page()
    
    # Open file for appending
    with open(OUTPUT_FILE, "a", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, dialect='excel')
        if new_file:
            writer.writeheader()
        
        # Initialize scraper with rate limiting
        s = scrapelib.Scraper(requests_per_minute=60)
        
        # Define page range to scrape
        start_page = 1
        
        # Track progress
        total_pages = end_page - start_page + 1
        total_transcripts = 0
        successful_transcripts = 0
        
        try:
            # Process each page
            for p in range(start_page, end_page + 1):
                logger.info(f"Processing page {p}/{end_page} ({p-start_page+1}/{total_pages})")
                
                try:
                    # Get the page with transcript links
                    page_url = f'https://www.msnbc.com/transcripts?sort=datePublished:asc&page={p}'
                    res = s.get(page_url)
                    soup = BeautifulSoup(res.text, "html.parser")
                    
                    # Find all transcript cards
                    transcript_cards = soup.find_all("div", {"class": "transcript-card"})
                    logger.info(f"Found {len(transcript_cards)} transcripts on page {p}")
                    
                    # Process each transcript
                    for a in transcript_cards:
                        total_transcripts += 1
                        
                        try:
                            # Extract data from transcript card
                            air_date_div = a.find("div", {"class": "transcript-card__air-date"})
                            air_date = air_date_div.text.strip() if air_date_div else ""
                            
                            link = a.find("a", {"class": "transcript-card__show-name"})
                            if not link:
                                logger.warning("Could not find show name link")
                                continue
                                
                            show_name = link.text.strip()
                            url = link['href']
                            
                            headline_link = a.find("a", {"class": "transcript-card__headline"})
                            headline = headline_link.text.strip() if headline_link else ""
                            
                            guests_span = a.find("span", {"class": "transcript-card__guests"})
                            guests = guests_span.text.strip() if guests_span else ""
                            
                            logger.info(f"Processing transcript: {air_date} - {url}")
                            
                            # Initialize data
                            data = {
                                'air_date': air_date,
                                'show_name': show_name,
                                'headline': headline,
                                'guests': guests,
                                'url': url
                            }
                            
                            # Get and process the transcript page
                            try:
                                res2 = s.get(url)
                                data = extract_transcript(res2.text, data)
                                
                                # Write to CSV
                                writer.writerow(data)
                                f.flush()  # Ensure data is written immediately
                                
                                successful_transcripts += 1
                                logger.info(f"Successfully processed: {headline}")
                                
                            except Exception as e:
                                logger.error(f"Error processing transcript {url}: {e}")
                                
                        except Exception as e:
                            logger.error(f"Error extracting transcript card data: {e}")
                    
                except Exception as e:
                    logger.error(f"Error processing page {p}: {e}")
            
            logger.info(f"Scraping completed. Processed {successful_transcripts}/{total_transcripts} transcripts.")
            
        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        logger.info(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()