import json
from scraper import scrape_reddit
from recommender import process_reddit_data, format_recommendation

def test_reddit_scraping():
    """
    Test the Reddit scraping functionality directly without going through the API
    """
    print("Testing Reddit scraping functionality...\n")
    
    # Test case: Vacuum cleaner with attributes
    product = "vacuum cleaner"
    attributes = ["cheap", "cordless"]
    
    print(f"Scraping for: {product} with attributes: {attributes}\n")
    
    # Call the scrape_reddit function directly
    reddit_data = scrape_reddit(product, attributes)
    
    # Print the threads found
    threads = reddit_data.get("threads", [])
    print(f"\nFound {len(threads)} Reddit threads:")
    
    for i, thread in enumerate(threads):
        print(f"\n{i+1}. {thread.get('title')}")
        print(f"   URL: {thread.get('url')}")
        print(f"   Comments: {len(thread.get('comments', []))}")
    
    # Process the Reddit data to extract products
    products = process_reddit_data(reddit_data, product, attributes)
    
    print(f"\nExtracted {len(products)} products:")
    for i, product_data in enumerate(products):
        print(f"\n{i+1}. {product_data.get('product')}")
        print(f"   Score: {product_data.get('score')}")
        print(f"   Sentiment: {product_data.get('sentiment')}")
        print(f"   Source: {product_data.get('source')}")
    
    # Format the recommendation
    if products:
        recommendation = format_recommendation(products, "reddit")
        
        print("\nFinal recommendation:")
        print(f"Product: {recommendation.get('product')}")
        
        print(f"Sources ({len(recommendation.get('sources', []))}):")
        for i, source in enumerate(recommendation.get('sources', [])):
            print(f"{i+1}. {source}")
    else:
        print("\nNo products found to recommend")

if __name__ == "__main__":
    test_reddit_scraping() 
