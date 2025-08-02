import sys
import json
from recommender import process_and_rank_products, process_reddit_data, process_youtube_data
from scraper import scrape_reddit, scrape_youtube

def debug_headphones_test():
    """Test the product ranking and selection logic with noise cancelling headphones"""
    # Search parameters
    product = "noise cancelling headphones"
    attributes = ["comfortable", "long battery"]
    
    # Call API directly
    results = process_and_rank_products(product, attributes)
    
    # Print the results
    print("\n=== Final Selected Products ===")
    if results.get("reddit"):
        print(f"Reddit: {results['reddit']['product']} - Validity: {results['reddit'].get('validity_score', 0)}")
    else:
        print("No Reddit recommendation")
        
    if results.get("youtube"):
        print(f"YouTube: {results['youtube']['product']} - Validity: {results['youtube'].get('validity_score', 0)}")
    else:
        print("No YouTube recommendation")

if __name__ == "__main__":
    print("\n*** Testing noise cancelling headphones ***")
    debug_headphones_test() 
