import os
import requests
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv
import re
import time
import random
import warnings
import urllib3
import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('scraper')

# Suppress SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Load environment variables
load_dotenv()

# Set default request timeout
REQUEST_TIMEOUT = 15  # Increased timeout for reliability

# Get current year for better search results
CURRENT_YEAR = datetime.datetime.now().year

# API keys from environment variables
GOOGLE_SEARCH_API_KEY = os.getenv('GOOGLE_SEARCH_API_KEY')
GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

def scrape_reddit(product, attributes):
    """
    Scrape Reddit for product recommendations.
    Uses Google Custom Search API and direct Reddit search as a fallback.
    
    Args:
        product (str): The product to search for
        attributes (list): List of desired attributes
        
    Returns:
        dict: Scraped data from Reddit
    """
    logger.info(f"========== Starting Reddit scraping for: {product} with attributes: {' '.join(attributes if attributes else [])} ==========")
    
    try:
        # Debug: Check if API keys exist
        api_keys_present = bool(GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID)
        logger.info(f"Google Search API keys available: {api_keys_present}")
        
        # Try Google Custom Search first
        if api_keys_present:
            reddit_data = search_reddit_via_google(product, attributes)
            logger.info(f"Google Search found {len(reddit_data.get('threads', []))} Reddit threads")
        else:
            logger.warning("Google Search API keys not available, skipping Google search")
            reddit_data = {"threads": []}
        
        # If Google search didn't find anything useful, try direct Reddit search
        if not reddit_data["threads"]:
            logger.info("Google search found no useful threads, trying direct Reddit search")
            reddit_data = search_reddit_directly(product, attributes)
            logger.info(f"Direct Reddit search found {len(reddit_data.get('threads', []))} threads")
        
        # If still no threads, try with a simplified product name
        if not reddit_data["threads"] and ' ' in product:
            simplified_product = product.split()[0]  # Use first word of product
            logger.info(f"No threads found, trying with simplified product term: {simplified_product}")
            
            if api_keys_present:
                reddit_data = search_reddit_via_google(simplified_product, attributes)
            
            if not reddit_data["threads"]:
                reddit_data = search_reddit_directly(simplified_product, attributes)
                
            logger.info(f"Search with simplified term found {len(reddit_data.get('threads', []))} threads")
            
        # If we still have no results, try with fallback search URLs
        if not reddit_data["threads"]:
            logger.info("Trying fallback searches...")
            
            # Construct search queries with various combinations
            fallback_urls = []
            
            # 1. Product + attributes + recommendation
            if attributes:
                attrs_query = '+'.join(attr.replace(' ', '+') for attr in attributes)
                url1 = f"https://www.reddit.com/search/?q={product.replace(' ', '+')}+{attrs_query}+recommendation"
                fallback_urls.append((url1, f"Search for {product} with attributes and recommendation"))
                
                # 2. Product + first attribute + recommendation
                url2 = f"https://www.reddit.com/search/?q={product.replace(' ', '+')}+{attributes[0].replace(' ', '+')}+recommendation"
                fallback_urls.append((url2, f"Search for {product} with {attributes[0]} recommendation"))
            
            # 3. Just product + recommendation (as final fallback)
            url3 = f"https://www.reddit.com/search/?q={product.replace(' ', '+')}+recommendation"
            fallback_urls.append((url3, f"Search for {product} recommendations"))
            
            # 4. Product + "best" (alternative query)
            url4 = f"https://www.reddit.com/search/?q={product.replace(' ', '+')}+best"
            fallback_urls.append((url4, f"Search for best {product}"))
            
            # Try each fallback URL in sequence
            for fallback_url, title in fallback_urls:
                logger.info(f"Trying fallback URL: {fallback_url}")
                
                # Extract posts from the search page
                search_page_html = None
                try:
                    # Get the search page HTML
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
                    }
                    response = requests.get(fallback_url, headers=headers, timeout=REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        search_page_html = response.text
                except Exception as e:
                    logger.error(f"Error fetching search page: {str(e)}")
                    continue  # Try the next URL if this one fails
                
                # Extract post URLs from search page
                post_urls = []
                if search_page_html:
                    # Try to extract post URLs using regex
                    post_url_matches = re.findall(r'href="(/r/[^"]+/comments/[^"]+)"', search_page_html)
                    if post_url_matches:
                        post_urls = [f"https://reddit.com{url}" for url in post_url_matches]
                        logger.info(f"Found {len(post_urls)} post URLs from search page")
                
                # If we found posts, use them
                if post_urls:
                    reddit_data = {"threads": []}
                    
                    # Process the first few posts
                    for post_url in post_urls[:3]:  # Limit to 3 posts
                        logger.info(f"Processing post URL: {post_url}")
                        
                        # Extract title from URL
                        title_match = re.search(r'/comments/[^/]+/([^/]+)/?', post_url)
                        post_title = title_match.group(1).replace('_', ' ').title() if title_match else "Reddit Thread"
                        
                        # Create a thread for this post
                        thread_data = {
                            "title": post_title,
                            "url": post_url,
                            "comments": []
                        }
                        
                        # Try to scrape comments using both methods
                        post_comments = scrape_reddit_thread(post_url)
                        if not post_comments:
                            post_comments = scrape_reddit_thread_json(post_url)
                            
                        if post_comments:
                            thread_data["comments"] = post_comments
                            reddit_data["threads"].append(thread_data)
                    
                    # If we found threads with comments, return them
                    if reddit_data["threads"]:
                        logger.info(f"Successfully extracted {len(reddit_data['threads'])} threads from search results")
                        break  # Exit the fallback URL loop if we found results
                    
                # If no posts gave us usable content, try the next fallback URL
                logger.info(f"No usable results from {fallback_url}, trying next fallback URL")
            
            # If we've tried all fallback URLs and still have no results,
            # try the first URL directly as a last resort
            if not reddit_data.get("threads") and fallback_urls:
                fallback_url, title = fallback_urls[0]
                logger.info(f"Trying direct scraping of search URL as last resort: {fallback_url}")
                
                comments = scrape_reddit_thread(fallback_url)
                if comments:
                    reddit_data = {
                        "threads": [{
                            "title": title,
                            "url": fallback_url,
                            "comments": comments
                        }]
                    }
                    logger.info(f"Final fallback search found {len(comments)} comments")
        
        # Log the final result
        if reddit_data["threads"]:
            total_comments = sum(len(thread.get("comments", [])) for thread in reddit_data["threads"])
            logger.info(f"========== Reddit scraping complete: Found {len(reddit_data['threads'])} threads with {total_comments} total comments ==========")
        else:
            logger.warning("========== Reddit scraping complete: No relevant Reddit threads found ==========")
                
        return reddit_data
    
    except Exception as e:
        logger.error(f"Error in scrape_reddit: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Always return a valid structure even on error
        return {"threads": []}

def search_reddit_via_google(product, attributes):
    """
    Search for Reddit threads using Google Custom Search API.
    
    Args:
        product (str): The product to search for
        attributes (list): List of desired attributes
        
    Returns:
        dict: Scraped Reddit data
    """    
    # If API keys are not available, return empty results
    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_ENGINE_ID:
        logger.error("Google Search API keys not found, cannot search Reddit via Google")
        return {"threads": []}
    
    try:
        # Debug: Log API key validity (partial key to avoid exposing full key)
        if GOOGLE_SEARCH_API_KEY:
            key_preview = GOOGLE_SEARCH_API_KEY[:4] + "..." + GOOGLE_SEARCH_API_KEY[-4:] if len(GOOGLE_SEARCH_API_KEY) > 8 else "****"
            logger.info(f"Using Google Search API key: {key_preview}")
            logger.info(f"Using Google Search Engine ID: {GOOGLE_SEARCH_ENGINE_ID[:4]}...")
        
        # Prepare search query - use recommendation-oriented keywords with current year
        attributes_str = ' '.join(attributes) if attributes else ''
        
        # Try multiple search query formats for better results
        search_queries = [
            f"best {product} {attributes_str} reddit review {CURRENT_YEAR}",
            f"recommended {product} {attributes_str} reddit thread",
            f"{product} recommendations reddit {CURRENT_YEAR}"
        ]
        
        reddit_links = []
        
        # Try each search query until we find something useful
        for search_query in search_queries:
            logger.info(f"Google search query: '{search_query}'")
            
            # Call Google Custom Search API
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': GOOGLE_SEARCH_API_KEY,
                'cx': GOOGLE_SEARCH_ENGINE_ID,
                'q': search_query,
                'num': 10,  # Results per query
                'sort': 'relevance',  # Use relevance sorting for better results
                'siteSearch': 'reddit.com',  # Restrict to Reddit
                'dateRestrict': 'y1'  # Restrict to past year for fresh results
            }
            
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                
                logger.info(f"Google API response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"Google API returned status code: {response.status_code}")
                    logger.error(f"Response content: {response.text[:500]}")
                    continue
                    
                search_results = response.json()
                
                # Log search info
                search_info = search_results.get('searchInformation', {})
                total_results = search_info.get('totalResults', '0')
                logger.info(f"Google search found {total_results} total results")
                
                # Extract Reddit links from search results
                if 'items' in search_results:
                    for item in search_results['items']:
                        if 'link' in item and 'reddit.com/r/' in item['link']:
                            # Make sure we're getting comment threads not just subreddits
                            link = item['link']
                            # Fix common issues with Reddit URLs
                            if '/comments/' not in link:
                                # Skip links to subreddits without specific threads
                                continue
                                
                            # Normalize the URL
                            if 'www.reddit.com' in link:
                                link = link.replace('www.reddit.com', 'reddit.com')
                                
                            # Only add unique Reddit links
                            link_data = {
                                'url': link,
                                'title': item.get('title', ''),
                                'snippet': item.get('snippet', '')
                            }
                            
                            # Debug info for each link
                            logger.info(f"Found Reddit thread: {link_data['title']}")
                            logger.info(f"URL: {link_data['url']}")
                            
                            if not any(existing['url'] == link_data['url'] for existing in reddit_links):
                                reddit_links.append(link_data)
                else:
                    logger.warning(f"No items in Google search results. Response structure: {list(search_results.keys())}")
                    if 'error' in search_results:
                        error_info = search_results['error']
                        logger.error(f"Google API error: {error_info.get('message', 'Unknown error')}")
                
                # If we found enough links, no need to try more search queries
                if len(reddit_links) >= 5:
                    break
                    
            except Exception as e:
                logger.error(f"Error during Google search request: {str(e)}")
                continue
                
            # Add a small delay between queries
            if search_query != search_queries[-1]:
                time.sleep(1)
        
        # Log overall results
        logger.info(f"Found {len(reddit_links)} Reddit threads from Google Search")
        
        # If we have Reddit links, sort and process them
        if reddit_links:
            # Sort links by relevance (based on keyword presence)
            keywords = [product.lower()] + [attr.lower() for attr in attributes if attr]
            keywords.extend(['best', 'recommend', 'review', 'top', 'comparison', f'{CURRENT_YEAR}', f'{CURRENT_YEAR-1}'])
            
            def relevance_score(link):
                score = 0
                text = (link['title'] + ' ' + link['snippet']).lower()
                for keyword in keywords:
                    if keyword in text:
                        score += 1
                return score
            
            # Sort by relevance score
            reddit_links.sort(key=relevance_score, reverse=True)
            
            # Take the top 3 most relevant links
            top_links = reddit_links[:3]
            logger.info(f"Selected top {len(top_links)} Reddit links for processing:")
            for i, link in enumerate(top_links):
                logger.info(f"{i+1}. {link['title']} - {link['url']}")
            
            # Process thread links
            return process_reddit_links(top_links)
        else:
            logger.warning("No Reddit links found from Google search")
            return {"threads": []}
            
    except Exception as e:
        logger.error(f"Error in Google Reddit search: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"threads": []}

def search_reddit_directly(product, attributes):
    """
    Search Reddit directly using their search URL.
    This is used as a fallback when Google search doesn't yield results.
    
    Args:
        product (str): The product to search for
        attributes (list): List of desired attributes
        
    Returns:
        dict: Scraped Reddit data
    """
    try:
        # Prepare search terms
        attributes_str = '+'.join(attributes) if attributes else ''
        product_term = product.replace(' ', '+')
        
        # Different search URLs to try
        search_urls = [
            f"https://old.reddit.com/search/?q={product_term}+{attributes_str}+recommendation&sort=relevance&t=year",
            f"https://old.reddit.com/search/?q={product_term}+best&sort=relevance&t=year",
            f"https://old.reddit.com/search/?q={product_term}+review&sort=relevance&t=year"
        ]
        
        reddit_links = []
        
        # Try each search URL
        for search_url in search_urls:
            logger.info(f"Searching Reddit directly: {search_url}")
            
            # Make request to Reddit search
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code != 200:
                logger.error(f"Reddit search returned status code: {response.status_code}")
                continue
                
            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search results
            search_results = soup.select('.search-result')
            
            for result in search_results:
                # Get thread link and title
                link_elem = result.select_one('.search-title a')
                if not link_elem:
                    continue
                    
                thread_url = link_elem.get('href')
                thread_title = link_elem.get_text()
                
                # Make sure it's a comment thread in a subreddit
                if thread_url and '/comments/' in thread_url and thread_url.startswith('/r/'):
                    full_url = f"https://old.reddit.com{thread_url}"
                    
                    # Extract snippet from search result
                    snippet_elem = result.select_one('.search-result-body')
                    snippet = snippet_elem.get_text() if snippet_elem else ''
                    
                    link_data = {
                        'url': full_url,
                        'title': thread_title,
                        'snippet': snippet
                    }
                    
                    # Only add unique Reddit links
                    if not any(existing['url'] == link_data['url'] for existing in reddit_links):
                        reddit_links.append(link_data)
            
            # If we found enough links, no need to try more search URLs
            if len(reddit_links) >= 3:
                break
                
            # Add a small delay between searches
            if search_url != search_urls[-1]:
                time.sleep(1)
        
        # If we have Reddit links, process them
        if reddit_links:
            # Take the top 3 links
            top_links = reddit_links[:3]
            
            # Process thread links
            return process_reddit_links(top_links)
        else:
            logger.warning("No Reddit links found from direct search")
            return {"threads": []}
            
    except Exception as e:
        logger.error(f"Error in direct Reddit search: {str(e)}")
        return {"threads": []}

def process_reddit_links(links):
    """
    Process a list of Reddit thread links by scraping each thread.
    
    Args:
        links (list): List of dictionaries with thread URL and title
        
    Returns:
        dict: Processed Reddit data with threads and comments
    """
    reddit_data = {"threads": []}
    
    # Process each thread link
    for link_data in links:
        thread_url = link_data['url']
        thread_title = link_data['title']
        
        logger.info(f"Scraping Reddit thread: {thread_title}")
        
        # Try multiple scraping methods for each thread
        thread_comments = []
        
        # Try first with old.reddit.com parsing
        thread_comments = scrape_reddit_thread(thread_url)
        
        # If that didn't work, try with JSON approach
        if not thread_comments:
            thread_comments = scrape_reddit_thread_json(thread_url)
        
        if thread_comments:
            # Store original thread URL and title
            thread_data = {
                "title": thread_title,
                "url": thread_url,
                "comments": []
            }
            
            # Process comments and capture their source URLs
            for comment in thread_comments:
                # Create a copy of the comment data
                comment_data = dict(comment)
                
                # If comment has a source_url, store it
                if "source_url" in comment_data:
                    # Save the original source URL but remove it from comment dict
                    source_url = comment_data.pop("source_url")
                    
                    # Check if we need to create a new thread for this comment
                    if source_url != thread_url:
                        # Look for an existing thread with this URL
                        existing_thread = next((t for t in reddit_data["threads"] if t["url"] == source_url), None)
                        
                        if existing_thread:
                            # Add to existing thread
                            existing_thread["comments"].append(comment_data)
                        else:
                            # Create a new thread for this comment
                            # Try to extract title from URL
                            title_match = re.search(r'/comments/[^/]+/([^/]+)/?', source_url)
                            source_title = title_match.group(1).replace('_', ' ').title() if title_match else "Reddit Thread"
                            
                            reddit_data["threads"].append({
                                "title": source_title,
                                "url": source_url,
                                "comments": [comment_data]
                            })
                        continue
                
                # If no source_url or same as thread URL, add to current thread
                thread_data["comments"].append(comment_data)
            
            # Only add thread if it has comments
            if thread_data["comments"]:
                reddit_data["threads"].append(thread_data)
        
        # Add a delay between thread scraping
        time.sleep(random.uniform(1.0, 2.0))
    
    # Filter out threads with no comments
    reddit_data["threads"] = [thread for thread in reddit_data["threads"] if thread["comments"]]
    
    return reddit_data

def scrape_reddit_thread(thread_url):
    """
    Scrape comments from a Reddit thread using HTML parsing.
    
    Args:
        thread_url (str): URL of the Reddit thread
        
    Returns:
        list: Comments from the thread with upvotes
    """
    try:
        # Convert regular URL to old.reddit.com for easier scraping
        if 'old.reddit.com' not in thread_url:
            thread_url = thread_url.replace('reddit.com', 'old.reddit.com')
            
        # Fix: Remove www. prefix to avoid SSL certificate mismatch
        thread_url = thread_url.replace('www.old.reddit.com', 'old.reddit.com')
        
        logger.info(f"Scraping comments from: {thread_url}")
            
        # Make request to thread URL with increased timeout
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
        }
        
        try:
            # First try with SSL verification
            response = requests.get(thread_url, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.SSLError:
            # If SSL fails, try without verification
            logger.warning(f"SSL verification failed for {thread_url}, retrying without verification")
            response = requests.get(thread_url, headers=headers, verify=False, timeout=REQUEST_TIMEOUT)
        
        # Check if request was successful
        if response.status_code != 200:
            logger.error(f"Failed to retrieve Reddit thread: {response.status_code}")
            
            # Try one more time with the new.reddit.com URL as a fallback
            fallback_url = thread_url.replace('old.reddit.com', 'new.reddit.com')
            logger.info(f"Trying fallback URL: {fallback_url}")
            
            try:
                response = requests.get(fallback_url, headers=headers, timeout=REQUEST_TIMEOUT)
                if response.status_code != 200:
                    logger.error(f"Fallback request failed with status code: {response.status_code}")
                    return []
            except Exception as e:
                logger.error(f"Fallback request failed: {str(e)}")
                return []
            
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Save a sample of the HTML to help diagnose parsing issues
        html_preview = response.text[:500].replace('\n', ' ')
        logger.info(f"HTML preview: {html_preview}")
        
        # Extract comments (each comment is in a div with class 'entry')
        comments_data = []
        
        # Check if this is a search results page
        is_search_page = '/search/' in thread_url or 'search?' in thread_url
        
        # Try multiple selectors to find comments - old Reddit format
        comments = soup.select('.entry')
        
        if not comments or len(comments) < 2:  # First entry is usually the post itself
            # If .entry selector doesn't work, try new Reddit format selectors
            comments = soup.select('.Comment')
            
            # Still no comments, try other selectors
            if not comments:
                comments = soup.select('div[data-testid="comment"]')
                
            if not comments:
                logger.warning(f"Could not find comments with any selector on {thread_url}")
                
                # Check if there's any content that might indicate comments
                if "comments" in response.text.lower() and "points" in response.text.lower():
                    logger.info("Page contains comment-related text but selectors failed")
                    
                    # If this is a search page, try to extract posts first
                    if is_search_page:
                        logger.info("This is a search page, extracting post URLs")
                        
                        # Extract search results (posts) with their URLs
                        post_elements = soup.select('.search-result')
                        post_urls = []
                        
                        # Extract post URLs from search results
                        for post in post_elements:
                            title_link = post.select_one('.search-title a')
                            if title_link and title_link.has_attr('href'):
                                post_url = title_link['href']
                                if post_url.startswith('/r/') and '/comments/' in post_url:
                                    full_url = f"https://reddit.com{post_url}"
                                    post_urls.append(full_url)
                        
                        logger.info(f"Found {len(post_urls)} post URLs from search results")
                        
                        # If we found post URLs, extract a snippet from each
                        if post_urls:
                            # Only process first 3 posts for efficiency
                            for post_url in post_urls[:3]:
                                logger.info(f"Fetching content from post: {post_url}")
                                try:
                                    # Get content from each post
                                    post_comments = scrape_reddit_thread(post_url)
                                    if post_comments:
                                        # Add post URL to each comment
                                        for comment in post_comments:
                                            comment['source_url'] = post_url
                                        comments_data.extend(post_comments)
                                except Exception as e:
                                    logger.error(f"Error extracting from post {post_url}: {str(e)}")
                            
                            if comments_data:
                                logger.info(f"Extracted {len(comments_data)} comments from actual posts")
                                return comments_data[:5]
                    
                    # Try to extract with regex as a last resort
                    # Example: Look for common patterns in Reddit comments
                    comment_blocks = re.findall(r'<div[^>]*class="[^"]*md[^"]*"[^>]*>(.*?)</div>', response.text, re.DOTALL)
                    if comment_blocks:
                        logger.info(f"Found {len(comment_blocks)} potential comments using regex")
                        
                        # For search pages, try to extract individual post URLs
                        post_urls = []
                        if is_search_page:
                            # Extract post URLs using regex
                            post_url_matches = re.findall(r'href="(/r/[^"]+/comments/[^"]+)"', response.text)
                            if post_url_matches:
                                post_urls = [f"https://reddit.com{url}" for url in post_url_matches]
                                logger.info(f"Found {len(post_urls)} post URLs with regex")
                        
                        # Process comment blocks
                        for i, block in enumerate(comment_blocks[:10]):  # Limit to first 10 to prevent excessive processing
                            # Clean HTML tags
                            text = re.sub(r'<[^>]+>', ' ', block)
                            text = re.sub(r'\s+', ' ', text).strip()
                            
                            if len(text) > 50:  # Only include if substantial content
                                if has_product_context(text):
                                    comment_data = {
                                        "text": text,
                                        "upvotes": 1  # Default value since we can't extract accurately
                                    }
                                    
                                    # Add source URL if available
                                    if i < len(post_urls):
                                        comment_data["source_url"] = post_urls[i]
                                    
                                    comments_data.append(comment_data)
                        
                        if comments_data:
                            logger.info(f"Extracted {len(comments_data)} comments with regex")
                            return comments_data[:5]
                return []
        
        # Process comments from selectors
        for comment in comments:
            try:
                # Skip if this is the original post (for old Reddit format)
                parent_thing = comment.find_parent('div', class_='thing')
                if parent_thing and parent_thing.get('data-type') == 'link':
                    continue
                    
                # Extract comment text - try multiple selectors
                comment_text = ""
                
                # Try old Reddit format first
                comment_text_div = comment.select_one('.usertext-body')
                
                if comment_text_div:
                    comment_text = comment_text_div.get_text(strip=True)
                else:
                    # Try new Reddit format
                    comment_text_div = comment.select_one('.RichTextJSON-root')
                    if comment_text_div:
                        comment_text = comment_text_div.get_text(strip=True)
                    else:
                        # Try any paragraph elements
                        paragraphs = comment.select('p')
                        if paragraphs:
                            comment_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
                
                # Skip empty comments or comments that are too short (likely not useful)
                if not comment_text or len(comment_text) < 20:
                    continue
                
                # Extract upvotes - try multiple selectors
                upvotes = 0
                
                # Old Reddit format
                upvotes_span = comment.select_one('.score')
                
                if upvotes_span:
                    upvotes_text = upvotes_span.get_text()
                    # Parse upvotes (handle "point", "points", and number format)
                    if 'points' in upvotes_text:
                        upvotes_match = re.search(r'(\d+)', upvotes_text)
                        if upvotes_match:
                            upvotes = int(upvotes_match.group(0))
                else:
                    # Try alternate upvote selectors
                    upvotes_span = comment.select_one('.score.unvoted')
                    if upvotes_span:
                        upvotes_text = upvotes_span.get('title', '0')
                        upvotes_match = re.search(r'(\d+)', upvotes_text)
                        if upvotes_match:
                            upvotes = int(upvotes_match.group(0))
                    else:
                        # New Reddit format - look for text with "points"
                        points_text = comment.get_text()
                        points_match = re.search(r'(\d+)\s+points', points_text)
                        if points_match:
                            upvotes = int(points_match.group(1))
                
                # Try to get the permalink to the original post
                source_url = thread_url
                permalink = None
                
                # Look for permalink in comment
                permalink_element = comment.select_one('.permalink')
                if permalink_element and permalink_element.has_attr('href'):
                    permalink = permalink_element['href']
                    if permalink.startswith('/r/'):
                        source_url = f"https://reddit.com{permalink}"
                
                # Only add comments with context about products
                if has_product_context(comment_text):
                    comment_data = {
                        "text": comment_text,
                        "upvotes": upvotes
                    }
                    
                    # Add source URL if it's different from the thread URL
                    if source_url != thread_url:
                        comment_data["source_url"] = source_url
                        
                    comments_data.append(comment_data)
            except Exception as e:
                logger.error(f"Error processing a comment: {str(e)}")
                continue
        
        # Sort comments by upvotes in descending order
        comments_data.sort(key=lambda x: x["upvotes"], reverse=True)
        
        logger.info(f"Found {len(comments_data)} relevant comments")
        
        # Return top comments (limit to 5)
        return comments_data[:5]
        
    except Exception as e:
        logger.error(f"Error scraping Reddit thread: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

def scrape_reddit_thread_json(thread_url):
    """
    Alternative method to scrape Reddit thread using .json endpoint.
    
    Args:
        thread_url (str): URL of the Reddit thread
        
    Returns:
        list: Comments from the thread with upvotes
    """
    try:
        # Create JSON URL by appending .json to the thread URL
        # First normalize the URL to reddit.com (not old or new)
        normalized_url = thread_url.replace('old.reddit.com', 'reddit.com').replace('new.reddit.com', 'reddit.com')
        
        # Then create the JSON URL
        if normalized_url.endswith('/'):
            json_url = f"{normalized_url}.json"
        else:
            json_url = f"{normalized_url}/.json"
            
        logger.info(f"Scraping thread via JSON API: {json_url}")
        
        # Make request to JSON endpoint
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        
        response = requests.get(json_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            logger.error(f"Failed to retrieve JSON data: {response.status_code}")
            return []
            
        # Parse JSON data
        try:
            data = response.json()
            logger.info(f"Successfully retrieved JSON data for {thread_url}")
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response")
            return []
            
        comments_data = []
        
        # Check if this is a search results page
        is_search_page = '/search/' in thread_url or 'search?' in thread_url
        
        # For search pages, extract and visit individual posts
        if is_search_page and isinstance(data, dict) and 'data' in data:
            try:
                # Extract post links from search results
                if 'children' in data['data']:
                    post_urls = []
                    for post in data['data']['children']:
                        if post.get('kind') == 't3' and 'data' in post:
                            post_data = post['data']
                            permalink = post_data.get('permalink')
                            if permalink and '/comments/' in permalink:
                                post_url = f"https://reddit.com{permalink}"
                                post_urls.append(post_url)
                    
                    logger.info(f"Found {len(post_urls)} post URLs from search JSON data")
                    
                    # Process each post URL (limit to 3 for efficiency)
                    for post_url in post_urls[:3]:
                        try:
                            post_comments = scrape_reddit_thread_json(post_url)
                            if post_comments:
                                # Add source URL to each comment
                                for comment in post_comments:
                                    comment['source_url'] = post_url
                                comments_data.extend(post_comments)
                        except Exception as e:
                            logger.error(f"Error scraping post {post_url}: {str(e)}")
                    
                    if comments_data:
                        logger.info(f"Extracted {len(comments_data)} comments from JSON search results")
                        return comments_data[:5]
            except Exception as e:
                logger.error(f"Error processing search JSON: {str(e)}")
        
        # Extract comments from thread JSON data (standard thread, not search)
        # Second element in the top array is usually the comments listing
        if isinstance(data, list) and len(data) > 1:
            comments_listing = data[1]
            
            if 'data' in comments_listing and 'children' in comments_listing['data']:
                logger.info(f"Found {len(comments_listing['data']['children'])} comment entries in JSON")
                
                for comment in comments_listing['data']['children']:
                    # Skip non-comment entries (like "more comments" links)
                    if comment['kind'] != 't1':
                        continue
                        
                    comment_data = comment['data']
                    
                    # Get comment text
                    comment_text = comment_data.get('body', '')
                    
                    # Skip empty or short comments
                    if not comment_text or len(comment_text) < 20:
                        continue
                        
                    # Get upvotes
                    upvotes = comment_data.get('ups', 0)
                    
                    # Get the permalink if available
                    source_url = thread_url
                    if 'permalink' in comment_data:
                        permalink = comment_data['permalink']
                        if permalink.startswith('/'):
                            source_url = f"https://reddit.com{permalink}"
                    
                    # Only add comments with product context
                    if has_product_context(comment_text):
                        comment_obj = {
                            "text": comment_text,
                            "upvotes": upvotes
                        }
                        
                        # Add source URL if different from thread URL
                        if source_url != thread_url:
                            comment_obj["source_url"] = source_url
                            
                        comments_data.append(comment_obj)
                        
                    # Recursively process replies
                    if 'replies' in comment_data and comment_data['replies']:
                        if isinstance(comment_data['replies'], dict) and 'data' in comment_data['replies']:
                            replies_data = comment_data['replies']['data']
                            
                            if 'children' in replies_data:
                                for reply in replies_data['children']:
                                    if reply['kind'] != 't1':
                                        continue
                                        
                                    reply_data = reply['data']
                                    reply_text = reply_data.get('body', '')
                                    
                                    # Skip empty or short replies
                                    if not reply_text or len(reply_text) < 20:
                                        continue
                                        
                                    reply_upvotes = reply_data.get('ups', 0)
                                    
                                    # Get the permalink for reply if available
                                    reply_source_url = thread_url
                                    if 'permalink' in reply_data:
                                        permalink = reply_data['permalink']
                                        if permalink.startswith('/'):
                                            reply_source_url = f"https://reddit.com{permalink}"
                                    
                                    # Only add replies with product context
                                    if has_product_context(reply_text):
                                        reply_obj = {
                                            "text": reply_text,
                                            "upvotes": reply_upvotes
                                        }
                                        
                                        # Add source URL if different from thread URL
                                        if reply_source_url != thread_url:
                                            reply_obj["source_url"] = reply_source_url
                                            
                                        comments_data.append(reply_obj)
        
        # Sort comments by upvotes
        comments_data.sort(key=lambda x: x["upvotes"], reverse=True)
        
        logger.info(f"Found {len(comments_data)} relevant comments via JSON")
        
        # Return top comments
        return comments_data[:5]
    
    except Exception as e:
        logger.error(f"Error scraping Reddit thread via JSON: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

def has_product_context(text):
    """
    Check if a comment has product context (mentions a product, review terms, etc.)
    
    Args:
        text (str): Comment text to analyze
        
    Returns:
        bool: True if the comment likely contains product information
    """
    product_context_terms = [
        # Purchase and ownership terms
        'bought', 'purchased', 'own', 'owned', 'got', 'received', 'acquired',
        'using', 'use', 'used', 'tried', 'tested', 'had',
        
        # Recommendation terms
        'recommend', 'recommendation', 'suggested', 'suggest', 'pick', 'choice',
        'go with', 'go for', 'consider', 'check out', 'look at',
        
        # Review/Quality terms
        'review', 'quality', 'experience', 'performance', 'rating',
        'excellent', 'amazing', 'fantastic', 'great', 'good', 'decent',
        'poor', 'terrible', 'bad', 'worst', 'disappointing',
        
        # Product-specific terms
        'model', 'brand', 'version', 'product', 'make', 'manufacturer',
        
        # Value terms
        'expensive', 'cheap', 'price', 'affordable', 'worth', 'value',
        'cost', 'overpriced', 'deal', 'budget', 'premium',
        
        # Feature terms
        'feature', 'functionality', 'battery', 'specs', 'specifications',
        'interface', 'design', 'build', 'durability', 'reliable', 'works'
    ]
    
    text_lower = text.lower()
    
    # Check if any product context terms exist in the comment
    for term in product_context_terms:
        if f" {term} " in f" {text_lower} ":  # Add spaces to ensure we match whole words
            return True
    
    # Also check if product is mentioned with a number or model designator 
    # (e.g., "iPhone 12", "Model XYZ", "the S22 Ultra")
    model_patterns = [
        r'\w+\s+\d+',       # Words followed by numbers: iPhone 12, Galaxy S21
        r'model\s+[a-z0-9]+', # Model designations: Model X, Model 3
        r'the\s+[a-z0-9]+',   # References like "the S22", "the Pro"
    ]
    
    for pattern in model_patterns:
        if re.search(pattern, text_lower):
            return True
            
    return False

def scrape_youtube(product, attributes):
    """
    Fetch YouTube video data about the product.
    Uses YouTube Data API to search for relevant videos and extract information.
    
    Args:
        product (str): The product to search for
        attributes (list): List of desired attributes
        
    Returns:
        dict: Data from YouTube videos
    """
    logger.info(f"Fetching YouTube data for: {product} with attributes: {', '.join(attributes if attributes else [])}")
    
    # If API key is not available, return empty results
    if not YOUTUBE_API_KEY:
        logger.error("YouTube API key not found, cannot fetch YouTube data")
        return {"videos": []}
    
    try:
        # Prepare search query - use comparison and recommendation keywords with current year
        attributes_str = ' '.join(attributes) if attributes else ''
        
        # Improved search query format for better recommendations
        search_query = f"best {product} {attributes_str} {CURRENT_YEAR} review comparison"
        
        # Call YouTube Data API
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'key': YOUTUBE_API_KEY,
            'q': search_query,
            'part': 'snippet',
            'maxResults': 7,  # Increased for better chances of quality results
            'type': 'video',
            'relevanceLanguage': 'en',
            'videoEmbeddable': 'true',
            'order': 'relevance',  # Use relevance for better quality results
            'publishedAfter': f"{CURRENT_YEAR-1}-01-01T00:00:00Z"  # Recent videos only
        }
        
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            logger.error(f"YouTube search API returned status code: {response.status_code}")
            return {"videos": []}
            
        search_results = response.json()
        
        youtube_data = {"videos": []}
        
        if 'items' in search_results:
            for item in search_results['items']:
                video_id = item['id']['videoId']
                video_title = item['snippet']['title']
                
                # Check if the title suggests a comparison or list of products
                title_lower = video_title.lower()
                
                # Improved keyword matching for recommendation videos
                is_comparison = any(keyword in title_lower for keyword in 
                                   ['best', 'top', 'vs', 'comparison', 'review', 'ranked',
                                    'list', 'guide', f"{CURRENT_YEAR}", f"{CURRENT_YEAR-1}",
                                    'worth buying', 'buying guide'])
                
                # Check if product is mentioned in title
                contains_product = product.lower() in title_lower
                
                # Check if any attributes are mentioned
                contains_attributes = any(attr.lower() in title_lower for attr in attributes) if attributes else True
                
                if is_comparison and (contains_product or contains_attributes):
                    # Get video statistics
                    stats_url = f"https://www.googleapis.com/youtube/v3/videos"
                    stats_params = {
                        'key': YOUTUBE_API_KEY,
                        'id': video_id,
                        'part': 'statistics,contentDetails'
                    }
                    
                    stats_response = requests.get(stats_url, params=stats_params, timeout=REQUEST_TIMEOUT)
                    
                    if stats_response.status_code != 200:
                        logger.warning(f"Failed to get video stats: {stats_response.status_code}")
                        continue
                        
                    stats_data = stats_response.json()
                    
                    if 'items' in stats_data and stats_data['items']:
                        stats = stats_data['items'][0]['statistics']
                        views = int(stats.get('viewCount', 0))
                        likes = int(stats.get('likeCount', 0))
                        
                        # Calculate view-to-like ratio as a quality indicator
                        ratio = 0
                        if views > 0:
                            ratio = likes / views
                        
                        # Only include videos with sufficient engagement
                        if views > 1000 or likes > 50 or ratio > 0.01:
                            # Get transcript
                            transcript = get_youtube_transcript(video_id, video_title, product)
                            
                            youtube_data["videos"].append({
                                "title": video_title,
                                "url": f"https://youtube.com/watch?v={video_id}",
                                "transcript": transcript,
                                "views": views,
                                "likes": likes,
                                "quality_score": ratio * 100  # Store quality score for sorting
                            })
                    
                    # Add a small delay to avoid rate limiting
                    time.sleep(random.uniform(0.5, 1.5))
        
        # Sort videos by quality score
        if youtube_data["videos"]:
            youtube_data["videos"].sort(key=lambda x: x.get("quality_score", 0), reverse=True)
            logger.info(f"Found {len(youtube_data['videos'])} relevant YouTube videos")
        
        # If we couldn't find any relevant YouTube videos, return empty results
        if not youtube_data["videos"]:
            logger.warning("No relevant YouTube videos found")
            
        return youtube_data
        
    except Exception as e:
        logger.error(f"Error scraping YouTube: {str(e)}")
        # Return empty results
        return {"videos": []}

def get_youtube_transcript(video_id, title, product):
    """
    Generate a transcript for a YouTube video.
    In a real implementation, you would use the YouTube Transcript API.
    This function uses a simple extraction from the video page.
    
    Args:
        video_id (str): YouTube video ID
        title (str): Video title
        product (str): Product being searched
        
    Returns:
        str: Transcript text or a summary based on the title
    """
    try:
        # Try to get the transcript from the video page
        # This is a simplified approach; a better solution would use YouTube Transcript API
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
        }
        
        response = requests.get(video_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            # Extract description as a fallback for transcript
            description_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', response.text)
            if description_match:
                # Clean the description
                description = description_match.group(1)
                # Unescape JSON
                description = description.replace('\\n', ' ').replace('\\', '')
                # If description is long enough, use it
                if len(description) > 50:
                    return description
                    
            # Try another pattern for getting description
            alt_desc_match = re.search(r'"description":{"simpleText":"(.*?)"},"lengthSeconds"', response.text)
            if alt_desc_match:
                # Clean the description
                description = alt_desc_match.group(1)
                # If description is long enough, use it
                if len(description) > 50:
                    return description
        
        # If we couldn't get a transcript, create a summary based on title
        return f"This video discusses {product} and provides reviews and comparisons based on its title: {title}"
        
    except Exception as e:
        logger.error(f"Error getting YouTube transcript: {str(e)}")
        return f"This video appears to be a review of {product} based on its title: {title}"
