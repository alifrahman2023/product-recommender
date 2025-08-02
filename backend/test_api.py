import requests
import json

def test_search_endpoint():
    """Test the /search endpoint of the API"""
    url = "http://localhost:5001/search"
    
    payload = {
        "product": "noise cancelling headphones",
        "attributes": ["comfortable", "long battery"]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("Sending search request to API...")
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response Data:")
            print(json.dumps(data, indent=2))
            
            # Request to get raw product list before final selection
            debug_url = "http://localhost:5001/debug"
            try:
                debug_response = requests.post(debug_url, json=payload, headers=headers)
                if debug_response.status_code == 200:
                    debug_data = debug_response.json()
                    
                    if 'reddit_products' in debug_data:
                        print("\nAll Reddit products before selection:")
                        reddit_products = debug_data['reddit_products']
                        for i, product in enumerate(reddit_products):
                            print(f"{i+1}. {product.get('product')} - Score: {product.get('score')}, Validity: {product.get('validity_score')}")
                    
                    if 'youtube_products' in debug_data:
                        print("\nAll YouTube products before selection:")
                        youtube_products = debug_data['youtube_products']
                        for i, product in enumerate(youtube_products):
                            print(f"{i+1}. {product.get('product')} - Score: {product.get('score')}, Validity: {product.get('validity_score')}")
            except:
                print("Debug endpoint not available")
            
            # Check Reddit sources specifically
            if data.get("reddit") and data["reddit"].get("sources"):
                reddit_sources = data["reddit"]["sources"]
                print(f"\nReddit Sources ({len(reddit_sources)}):")
                for i, source in enumerate(reddit_sources):
                    print(f"{i+1}. {source}")
                    
                if len(reddit_sources) > 1:
                    print("\nTest PASSED: Multiple Reddit sources included")
                else:
                    print("\nTest NOTE: Only one Reddit source found")
            
            # Check if we have data from at least one source
            if data.get("reddit") or data.get("youtube"):
                print("\nTest PASSED: Received product recommendations")
            else:
                print("\nTest FAILED: No product recommendations found")
        else:
            print(f"\nTest FAILED: Received status code {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\nTest FAILED: Could not connect to the API. Make sure the Flask server is running.")
    except Exception as e:
        print(f"\nTest FAILED: {str(e)}")

if __name__ == "__main__":
    print("Testing /search endpoint...\n")
    test_search_endpoint() 
