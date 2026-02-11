import requests
from bs4 import BeautifulSoup
from datetime import datetime
import email.utils
import re
from urllib.parse import urljoin
import sys
import html

def fetch_html(url):
    """Fetches the HTML content from the given URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        return None

def parse_date(date_str):
    """Attempts to parse a date string into a datetime object."""
    # Try YYYY-MM-DD
    match_iso = re.search(r'\((\d{4}-\d{2}-\d{2})\)', date_str)
    if match_iso:
        try:
            return datetime.strptime(match_iso.group(1), '%Y-%m-%d')
        except ValueError:
            pass
            
    # Try Month YYYY (e.g., December 2021)
    match_month_year = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', date_str, re.IGNORECASE)
    if match_month_year:
        try:
            return datetime.strptime(match_month_year.group(0), '%B %Y')
        except ValueError:
            pass
    
    return datetime.now() # Fallback

def extract_articles(base_url, html_content):
    """Parses the HTML and extracts article information."""
    soup = BeautifulSoup(html_content, 'html.parser')
    articles = []
    seen_links = set()

    # The site typically lists papers in a container. 
    # Based on analysis, articles are often links inside specific blocks or lists.
    # We look for links that contain a year pattern like '/2021/', '/2022/', etc.
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        absolute_url = urljoin(base_url, href)
        
        # Filter for likely article links (contains year)
        if not re.search(r'/20\d{2}/', absolute_url):
            continue
            
        if absolute_url in seen_links:
            continue
        seen_links.add(absolute_url)

        title = a_tag.get_text(" ", strip=True)
        if not title:
            continue
            
        # Context extraction: 
        # The date is often in the surrounding text (parent or previous sibling)
        # Example: "(2021-12-22) Title"
        
        # Check parent text for date
        parent_text = a_tag.parent.get_text(" ", strip=True) if a_tag.parent else ""
        
        # Check for description in the next sibling or parent
        description = ""
        possible_desc_node = a_tag.find_next_sibling(['p', 'div', 'span'])
        if possible_desc_node:
            description = possible_desc_node.get_text(" ", strip=True)
        
        # If description is empty, use parent text but remove title
        if not description and parent_text:
             description = parent_text.replace(title, "").strip()

        # Extract date from parent text or description
        pub_date = parse_date(parent_text + " " + description)
        
        # Format RFC 822 Date
        rfc_date = email.utils.format_datetime(pub_date)

        articles.append({
            'title': title,
            'link': absolute_url,
            'description': description,
            'pubDate': rfc_date
        })

    return articles

def generate_rss(articles):
    """Generates a valid RSS 2.0 XML string."""
    rss_template = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
 <title>Transformer Circuits</title>
 <description>Unofficial RSS feed for Transformer Circuits Thread (transformer-circuits.pub)</description>
 <link>https://transformer-circuits.pub/</link>
 <lastBuildDate>{build_date}</lastBuildDate>
 <pubDate>{build_date}</pubDate>
{items}
</channel>
</rss>"""

    item_template = """ <item>
  <title>{title}</title>
  <description>{description}</description>
  <link>{link}</link>
  <guid>{link}</guid>
  <pubDate>{pubDate}</pubDate>
 </item>"""

    items_xml = ""
    for article in articles:
        items_xml += item_template.format(
            title=html.escape(article['title']),
            description=html.escape(article['description']),
            link=article['link'],
            pubDate=article['pubDate']
        )

    return rss_template.format(
        build_date=email.utils.format_datetime(datetime.now()),
        items=items_xml
    )

def main():
    base_url = "https://transformer-circuits.pub/"
    html_content = fetch_html(base_url)
    
    if html_content:
        articles = extract_articles(base_url, html_content)
        rss_feed = generate_rss(articles)
        print(rss_feed)

if __name__ == "__main__":
    main()
