import re
import os
import time
import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI
from scraper import (
    scrape_reddit, scrape_youtube
)
from utils import extract_product_models, analyze_sentiment
import datetime
import requests

# Load environment variables
load_dotenv()

# Define timeout constants
SCRAPING_TIMEOUT = 30  # seconds per source

# Set up OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def process_and_rank_products(product, attributes):
    """
    Process and rank product recommendations from different sources.
    
    Args:
        product (str): The product type to search for
        attributes (list): List of desired attributes
        
    Returns:
        dict: Product recommendations from different sources
    """
    try:
        print(f"Starting scraping process for {product} with attributes: {attributes}")
        
        # Use concurrent processing with timeout to prevent hanging
        results = {}
        
        # Use ThreadPoolExecutor to run scraping functions concurrently with timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit scraping jobs
            reddit_future = executor.submit(scrape_reddit, product, attributes)
            youtube_future = executor.submit(scrape_youtube, product, attributes)
            
            # Get results with timeout
            try:
                reddit_data = reddit_future.result(timeout=SCRAPING_TIMEOUT)
            except (concurrent.futures.TimeoutError, Exception) as e:
                print(f"Reddit scraping timed out or failed: {str(e)}")
                reddit_data = {"threads": []}
                
            try:
                youtube_data = youtube_future.result(timeout=SCRAPING_TIMEOUT)
            except (concurrent.futures.TimeoutError, Exception) as e:
                print(f"YouTube scraping timed out or failed: {str(e)}")
                youtube_data = {"videos": []}
        
        print("Data gathering complete, processing results...")
        
        # Process each source and extract product mentions
        reddit_products = process_reddit_data(reddit_data, product, attributes)
        youtube_products = process_youtube_data(youtube_data, product, attributes)
        
        # Format the top recommendations for the frontend
        results = {
            "reddit": format_recommendation(reddit_products, "reddit") if reddit_products else None,
            "youtube": format_recommendation(youtube_products, "youtube") if youtube_products else None
        }
        
        # If results is empty, return empty dict to indicate no results found
        if not results["reddit"] and not results["youtube"]:
            print("No results found from any source")
            return {"reddit": None, "youtube": None}
            
        return results
        
    except Exception as e:
        print(f"Error processing recommendations: {e}")
        # Return empty results
        return {"reddit": None, "youtube": None}

def is_valid_product(product_name, context_text='', product_type=''):
    """
    Validate if an extracted name is likely a genuine complete product model 
    rather than a component, generic term, or non-existent product.
    
    Args:
        product_name (str): The product name to validate
        context_text (str): Surrounding text for context
        product_type (str): Type of product being searched for
        
    Returns:
        tuple: (is_valid, confidence_score, reason)
    """
    # Initialize score and reason
    confidence_score = 0
    reason = []
    
    # Normalize for comparisons
    product_lower = product_name.lower()
    product_type_lower = product_type.lower() if product_type else ''
    
    # 1. Check for sufficient length and complexity
    if len(product_name) < 6:
        confidence_score -= 3
        reason.append("Too short for a complete product name")
    else:
        confidence_score += 1
        
    # 2. Verify product contains both letters and numbers (most real products do)
    has_letters = bool(re.search(r'[a-zA-Z]', product_name))
    has_numbers = bool(re.search(r'\d', product_name))
    
    if has_letters and has_numbers:
        confidence_score += 2
        reason.append("Contains both letters and numbers")
    elif not has_numbers:
        confidence_score -= 1
        reason.append("Missing model numbers")
    
    # 3. Check for brand + model pattern
    # Look for major product brand names
    brands = [
        'samsung', 'apple', 'sony', 'lg', 'microsoft', 'dell', 'hp',
        'lenovo', 'asus', 'acer', 'alienware', 'msi', 'gigabyte', 'dyson',
        'intel', 'amd', 'nvidia', 'corsair', 'logitech', 'razer', 'bose',
        'sony', 'jbl', 'shure', 'shark', 'bosch', 'miele', 'canon', 'nikon'
    ]
    
    has_brand = any(brand in product_lower for brand in brands)
    
    if has_brand:
        confidence_score += 2
        reason.append("Contains known brand name")
    else:
        # Check for capitalized words which may be unrecognized brands
        if re.search(r'[A-Z][a-z]+', product_name):
            confidence_score += 1
            reason.append("Contains capitalized brand-like words")
        else:
            confidence_score -= 1
            reason.append("No identifiable brand")
    
    # 4. Product-specific validation
    if 'graphics' in product_type_lower or 'gpu' in product_type_lower or 'gaming' in product_type_lower:
        # Validate GPU model pattern
        is_gpu = re.search(r'(rtx|gtx|radeon rx|arc)\s*[a-b]?\d{3,4}', product_lower)
        if is_gpu:
            # Check for non-existent future GPU models
            # NVIDIA RTX/GTX
            nvidia_match = re.search(r'(rtx|gtx)\s*(\d{4})', product_lower)
            if nvidia_match:
                model_num = int(nvidia_match.group(2))
                # As of 2025, RTX 4000 series is current, 5000 would be future
                if model_num >= 5000:
                    confidence_score -= 3
                    reason.append(f"Likely future/non-existent NVIDIA GPU model: {model_num}")
                else:
                    confidence_score += 2
                    reason.append("Valid NVIDIA GPU model number range")
            
            # Intel Arc - current models are Arc A-series (A770, A750, A580, etc) not B-series
            intel_match = re.search(r'arc\s*([a-z])?(\d{3})', product_lower)
            if intel_match:
                series = intel_match.group(1).upper() if intel_match.group(1) else ""
                if series and series != 'A':
                    confidence_score -= 3
                    reason.append(f"Likely non-existent Intel Arc series: {series}-series")
                elif not series:
                    confidence_score -= 1
                    reason.append("Missing Intel Arc series letter (should be A-series)")
                else:
                    model_num = int(intel_match.group(2))
                    valid_arc_models = [770, 750, 580, 380, 350, 325, 310]
                    if model_num not in valid_arc_models:
                        confidence_score -= 2
                        reason.append(f"Unusual Intel Arc model number: {model_num}")
                    else:
                        confidence_score += 2
                        reason.append("Valid Intel Arc GPU model")
            
            # AMD Radeon
            amd_match = re.search(r'(radeon rx|rx)\s*(\d{4})', product_lower)
            if amd_match:
                model_num = int(amd_match.group(2))
                # As of 2025, RX 7000 series are current, 8000+ would be future
                if model_num >= 8000:
                    confidence_score -= 3
                    reason.append(f"Likely future/non-existent AMD GPU model: {model_num}")
                else:
                    confidence_score += 2
                    reason.append("Valid AMD GPU model number range")
            
            # Check for proper GPU naming convention
            if 'gb' in product_lower:
                confidence_score += 1
                reason.append("Includes memory specification")
    
    elif 'computer' in product_type_lower or 'pc' in product_type_lower or 'desktop' in product_type_lower or 'gaming pc' in product_type_lower:
        # For computers, look for complete system names vs components
        if any(term in product_lower for term in ['system', 'desktop', 'tower', 'pc', 'computer', 'gaming pc']):
            confidence_score += 2
            reason.append("Contains system-level terms")
        
        # Check for known prebuilt system brands
        prebuilt_brands = ['alienware', 'hp omen', 'corsair', 'lenovo legion', 'asus rog', 'msi', 'acer predator']
        if any(brand in product_lower for brand in prebuilt_brands):
            confidence_score += 3
            reason.append("Known prebuilt system brand")
        
        # Look for standalone GPU components (RTX/GTX/etc without system terms)
        if re.search(r'(rtx|gtx|radeon)\s*\d{4}', product_lower) and not re.search(r'(system|desktop|tower|pc|computer|gaming pc)', product_lower):
            if len(product_name) < 20:  # Short product names with GPU model are likely just the GPU
                confidence_score -= 3
                reason.append("Appears to be just a GPU, not a complete system")
        
        # Check if it's just a component
        if any(component in product_lower for component in ['ryzen', 'core i', 'intel', 'processor', 'gpu', 'card', 'ram']):
            if len(product_name) < 15 and not re.search(r'(system|desktop|tower|pc|computer|gaming pc)', product_lower):
                confidence_score -= 2
                reason.append("Appears to be just a component, not a complete system")
    
    # 5. Context-based validation 
    if context_text:
        context_lower = context_text.lower()
        
        # Check for ownership language around the product
        ownership_terms = ['i bought', 'i own', 'i use', 'i have', 'purchased', 'using']
        if any(term in context_lower for term in ownership_terms):
            product_index = context_lower.find(product_lower)
            if product_index >= 0:
                # Look at text before the product mention
                pre_text = context_lower[max(0, product_index-50):product_index]
                if any(term in pre_text for term in ownership_terms):
                    confidence_score += 3
                    reason.append("Product mentioned in ownership context")
        
        # Check for recommendation language
        recommend_terms = ['recommend', 'suggested', 'best', 'top', 'great', 'excellent']
        if any(term in context_lower for term in recommend_terms):
            confidence_score += 1
            reason.append("Product mentioned in recommendation context")
    
    # Final validation
    is_valid = confidence_score >= 3  # Threshold for validity
    
    return (is_valid, confidence_score, ', '.join(reason))

def process_reddit_data(reddit_data, product, attributes):
    """
    Process Reddit data to extract and rank product mentions.
    
    Args:
        reddit_data (dict): Data scraped from Reddit
        product (str): The product type
        attributes (list): Desired attributes
        
    Returns:
        list: Ranked product mentions
    """
    product_mentions = []
    product_type_terms = [product.lower()] + [attr.lower() for attr in attributes if attr]
    
    # Print debug info
    print(f"Processing Reddit data with {len(reddit_data.get('threads', []))} threads")
    
    for thread in reddit_data.get("threads", []):
        thread_title = thread.get("title", "").lower()
        thread_url = thread.get("url", "")
        
        # Get all comments from the thread
        all_comments = thread.get("comments", [])
        print(f"Thread '{thread_title[:30]}...' has {len(all_comments)} comments")
        
        # First try to extract specific product models using AI/regex
        for comment in all_comments:
            text = comment.get("text", "")
            upvotes = comment.get("upvotes", 0)
            
            # Try AI extraction first for more accurate product models
            models = extract_product_models(text)
            
            if models:
                print(f"Found {len(models)} product models in comment: {models}")
                
                # Analyze sentiment for positive mentions
                sentiment = analyze_sentiment(text)
                
                # Add each product with metrics
                for model in models:
                    # Validate product name
                    is_valid, validity_score, validity_reason = is_valid_product(model, text, product)
                    
                    # Skip if this is clearly not a valid product
                    if validity_score < 0:
                        print(f"Skipping likely invalid product: {model} ({validity_reason})")
                        continue
                    
                    product_mentions.append({
                        "product": model,
                        "upvotes": upvotes,
                        "sentiment": sentiment,
                        "source": thread_url,
                        "description": generate_description(text, model, attributes),
                        "validity_score": validity_score,
                        "validity_reason": validity_reason,
                        "product_type": product,
                        "attributes": attributes
                    })
        
        # If no specific products were found or too few, try to find product mentions using regex patterns
        if len(product_mentions) < 2:
            for comment in all_comments:
                text = comment.get("text", "")
                upvotes = comment.get("upvotes", 0)
                
                model_name = extract_model_from_text(text, product)
                if model_name:
                    print(f"Extracted model from text: {model_name}")
                    
                    # Validate product name
                    is_valid, validity_score, validity_reason = is_valid_product(model_name, text, product)
                    
                    # Skip if this is clearly not a valid product
                    if validity_score < 0:
                        print(f"Skipping likely invalid product: {model_name} ({validity_reason})")
                        continue
                    
                    sentiment = analyze_sentiment(text)
                    
                    # Check if model name already exists in product_mentions
                    if not any(mention["product"].lower() == model_name.lower() for mention in product_mentions):
                        product_mentions.append({
                            "product": model_name,
                            "upvotes": upvotes,
                            "sentiment": sentiment,
                            "source": thread_url,
                            "description": generate_description(text, model_name, attributes),
                            "validity_score": validity_score,
                            "validity_reason": validity_reason,
                            "product_type": product,
                            "attributes": attributes
                        })
    
    # Score products based on multiple factors
    for mention in product_mentions:
        # Base score from original calculation
        base_score = (mention["sentiment"] * 5) + min(5, mention["upvotes"] / 10)
        
        # Add validity score impact (0-5 points)
        validity_impact = min(5, max(0, mention.get("validity_score", 0)))
        
        # Combine scores, heavily weighting valid products
        mention["score"] = base_score + (validity_impact * 2)
        
        # Bonus points for products that match the search terms
        product_name = mention["product"].lower()
        for term in product_type_terms:
            if term in product_name:
                mention["score"] += 1
                
        # Bonus for products with longer names (usually more specific/legitimate)
        if len(mention["product"]) > 8:  # Longer names tend to be more specific product models
            mention["score"] += 1
            
        print(f"Product '{mention['product']}' scored {mention['score']:.1f} (sentiment: {mention['sentiment']:.1f}, upvotes: {mention['upvotes']}, validity: {mention.get('validity_score', 0)})")
    
    # Sort by combined score, sentiment, and upvotes
    product_mentions.sort(key=lambda x: (x.get("score", 0), x["sentiment"], x["upvotes"]), reverse=True)
    
    # Remove duplicates (keeping highest scored version)
    unique_products = {}
    for mention in product_mentions:
        # Normalize product names for better duplicate detection
        product_key = re.sub(r'[^a-zA-Z0-9]', '', mention["product"].lower())
        
        if product_key not in unique_products or mention.get("score", 0) > unique_products[product_key].get("score", 0):
            unique_products[product_key] = mention
    
    # Convert back to list and return
    result = list(unique_products.values())
    print(f"Final Reddit product count: {len(result)}")
    return result

def process_youtube_data(youtube_data, product, attributes):
    """
    Process YouTube data to extract and rank product mentions.
    
    Args:
        youtube_data (dict): Data from YouTube videos
        product (str): The product type
        attributes (list): Desired attributes
        
    Returns:
        list: Ranked product mentions
    """
    product_mentions = []
    product_type_terms = [product.lower()] + [attr.lower() for attr in attributes if attr]
    
    for video in youtube_data.get("videos", []):
        # Extract product models from video transcript
        transcript = video.get("transcript", "")
        video_title = video.get("title", "")
        models = extract_product_models(transcript)
        
        if models:
            # Analyze sentiment for positive mentions
            sentiment = analyze_sentiment(transcript)
            
            # Add each product with metrics
            for model in models:
                # Validate product name
                is_valid, validity_score, validity_reason = is_valid_product(model, transcript, product)
                
                # Skip if this is clearly not a valid product
                if validity_score < 0:
                    print(f"Skipping likely invalid YouTube product: {model} ({validity_reason})")
                    continue
                
                product_mentions.append({
                    "product": model,
                    "views": video.get("views", 0),
                    "likes": video.get("likes", 0),
                    "sentiment": sentiment,
                    "source": video.get("url", ""),
                    "description": generate_description(transcript, model, attributes),
                    "title": video_title,
                    "validity_score": validity_score,
                    "validity_reason": validity_reason,
                    "product_type": product,
                    "attributes": attributes
                })
    
    # Score products based on multiple factors
    for mention in product_mentions:
        # Base score calculation
        base_score = (mention["sentiment"] * 3) + min(3, mention["likes"] / 100) + min(4, mention["views"] / 10000)
        
        # Add validity score impact (0-5 points)
        validity_impact = min(5, max(0, mention.get("validity_score", 0)))
        
        # Combine scores, heavily weighting valid products
        mention["score"] = base_score + (validity_impact * 2)
        
        # Bonus points for products mentioned in video titles
        if mention["product"].lower() in mention["title"].lower():
            mention["score"] += 3
            
        # Bonus points for products that match the search terms
        product_name = mention["product"].lower()
        for term in product_type_terms:
            if term in product_name:
                mention["score"] += 1
    
    # Sort by score
    product_mentions.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Remove duplicates (keeping highest scored version)
    unique_products = {}
    for mention in product_mentions:
        product_key = mention["product"].lower().strip()
        if product_key not in unique_products or mention.get("score", 0) > unique_products[product_key].get("score", 0):
            unique_products[product_key] = mention
    
    # Convert back to list and return
    return list(unique_products.values())

def extract_model_from_text(text, product_type):
    """
    Extract a product model name from text using regex patterns.
    
    Args:
        text (str): Text to extract from
        product_type (str): Type of product
        
    Returns:
        str: Extracted model name or None
    """
    product_type_lower = product_type.lower()
    
    # Define patterns for different product types
    if "phone" in product_type_lower or "smartphone" in product_type_lower:
        patterns = [
            r'(iPhone \d+(?:\s+Pro)?(?:\s+Max)?)',
            r'(Samsung Galaxy S\d+(?:\s+Ultra)?)',
            r'(Google Pixel \d+(?:\s+Pro)?)',
            r'(OnePlus \d+(?:\s+Pro)?)',
            r'(Xiaomi Mi \d+)',
            r'(Motorola \w+ \d+)'
        ]
    elif "vacuum" in product_type_lower:
        patterns = [
            r'(Dyson V\d+(?:\s+\w+)?)',
            r'(Shark Navigator(?:\s+\w+)*)',
            r'(Miele Complete(?:\s+\w+)*)',
            r'(Bissell \w+(?:\s+\w+){0,3})',
            r'(Hoover \w+(?:\s+\w+){0,3})',
            r'(Tineco \w+(?:\s+\w+){0,3})',
            r'(Eureka \w+(?:\s+\w+){0,3})'
        ]
    elif "laptop" in product_type_lower:
        patterns = [
            r'(MacBook (?:Air|Pro)(?: \d+)?(?:-inch)?)',
            r'(Dell XPS \d+)',
            r'(HP (?:Spectre|Envy|Pavilion|EliteBook) \w+(?:[- ]\w+)*)',
            r'(Lenovo (?:ThinkPad|Yoga|Legion|IdeaPad) \w+(?:[- ]\w+)*)',
            r'(ASUS (?:ZenBook|VivoBook|ROG|TUF) \w+(?:[- ]\w+)*)',
            r'(Acer (?:Aspire|Predator|Swift|Nitro) \w+(?:[- ]\w+)*)',
            r'(Microsoft Surface (?:Laptop|Book|Pro) \d+)'
        ]
    elif "headphone" in product_type_lower:
        patterns = [
            r'(Sony WH-\d+XM\d+)',
            r'(Bose QuietComfort \d+)',
            r'(Apple AirPods(?: Pro| Max)?)',
            r'(Sennheiser (?:HD|Momentum) \d+(?:[- ]\w+)*)',
            r'(Jabra Elite \d+[tT]?)',
            r'(Audio-Technica ATH-\w+)',
            r'(Beats(?: By Dre)? \w+(?:[- ]\w+)*)'
        ]
    elif "monitor" in product_type_lower:
        patterns = [
            r'(LG (?:UltraGear|UltraWide) \w+(?:[- ]\w+)*)',
            r'(Samsung (?:Odyssey|ViewFinity) \w+(?:[- ]\w+)*)',
            r'(ASUS (?:ROG|ProArt|TUF) \w+(?:[- ]\w+)*)',
            r'(Dell (?:Alienware|UltraSharp) \w+(?:[- ]\w+)*)',
            r'(BenQ \w+(?:[- ]\w+){0,3})',
            r'(Acer (?:Predator|Nitro) \w+(?:[- ]\w+)*)',
            r'(MSI \w+(?:[- ]\w+){0,3})',
            r'(ViewSonic \w+(?:[- ]\w+){0,3})'
        ]
    else:
        # Generic brand + model pattern
        patterns = [
            r'([A-Z][a-zA-Z0-9]+ [A-Z0-9][a-zA-Z0-9]+(?:[- ][A-Z0-9][a-zA-Z0-9]+){0,3})'
        ]
    
    # Try each pattern
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Return the first match
            return matches[0].strip()
            
    # If no match found with the patterns, look for any capitalized words
    # near the product type mention
    product_mention_index = text.lower().find(product_type_lower)
    if product_mention_index != -1:
        # Look for capitalized words near the product mention
        surrounding_text = text[max(0, product_mention_index - 30):min(len(text), product_mention_index + 50)]
        capitalized_words = re.findall(r'[A-Z][a-zA-Z0-9]+(?:\s+[A-Z0-9][a-zA-Z0-9]+){1,3}', surrounding_text)
        if capitalized_words:
            return capitalized_words[0].strip()
    
    # No model name found
    return None

def generate_description(text, product_model, attributes):
    """
    Generate a descriptive text for a product based on the mention text.
    
    Args:
        text (str): Text mentioning the product
        product_model (str): Product model name
        attributes (list): Desired attributes
        
    Returns:
        str: Generated description
    """
    # Extract a relevant portion of the text that mentions the product
    product_mention_index = text.find(product_model)
    if product_mention_index != -1:
        # Get text surrounding the product mention (100 chars before and 150 after)
        start = max(0, product_mention_index - 100)
        end = min(len(text), product_mention_index + 150)
        context = text[start:end]
        
        # Only keep complete sentences
        sentences = re.split(r'(?<=[.!?])\s+', context)
        
        # If we have at least 2 sentences, use them
        if len(sentences) >= 2:
            description = ' '.join(sentences[:3])  # First 3 sentences
        else:
            description = context
            
        # Clean the description to make it more readable
        description = description.replace('  ', ' ').strip()
        
        # Add attributes to the description if they're not mentioned
        attributes_str = ', '.join(attributes) if attributes else ""
        if attributes_str and not any(attr.lower() in description.lower() for attr in attributes):
            description += f" This {product_model} is known for being {attributes_str}."
            
        return description
        
    # Fallback: Generate a generic description
    return f"The {product_model} is highly recommended by users who want a {', '.join(attributes) if attributes else 'quality'} product."

def generate_ai_description(product_name, original_description, product_type, attributes):
    """
    Generate an enhanced product description using AI that incorporates the 
    web-scraped text but presents it in a more cohesive way.
    
    Args:
        product_name (str): The product model name
        original_description (str): Original scraped description
        product_type (str): Type of product
        attributes (list): Desired attributes
        
    Returns:
        str: AI-enhanced product description
    """
    try:
        if not os.getenv('OPENAI_API_KEY'):
            print("OpenAI API key not found, using original description")
            return original_description
            
        # Format attributes as a comma-separated string
        attributes_str = ", ".join(attributes) if attributes else "high quality"
        
        # Create prompt for the AI
        prompt = f"""
        Create a concise but compelling product description for the {product_name}, which is a {product_type}.
        The description should focus on why this product is recommended and highlight these key attributes: {attributes_str}.
        
        Use these user comments/reviews as context, but write a cohesive paragraph, not just quoting them:
        "{original_description}"
        
        The description should be factual, professional, informative, and 2-3 sentences long.
        """
        
        # Use OpenAI to generate the description
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a product description writer who creates concise, informative descriptions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        # Extract the AI-generated description
        ai_description = response.choices[0].message.content.strip()
        
        print(f"Generated AI description for {product_name}")
        return ai_description
        
    except Exception as e:
        print(f"Error generating AI description: {e}")
        # Fallback to original description
        return original_description

def format_recommendation(product_mentions, source):
    """
    Format a product recommendation for the frontend.
    
    Args:
        product_mentions (list): Ranked product mentions
        source (str): Source name (reddit, youtube)
        
    Returns:
        dict: Formatted recommendation
    """
    if not product_mentions:
        return None
    
    # Log all product mentions with their scores for debugging
    print(f"\n=== Debug: All {source} products before filtering ===")
    for i, prod in enumerate(product_mentions):
        print(f"{i+1}. {prod.get('product')} - Score: {prod.get('score', 0):.1f}, Validity: {prod.get('validity_score', 0)}")
    
    # First identify if this is a product category where we should filter out components
    is_system_search = False
    product_type = ""
    if product_mentions and product_mentions[0].get("product_type"):
        product_type = product_mentions[0].get("product_type", "").lower()
        is_system_search = any(term in product_type for term in ['computer', 'pc', 'desktop', 'gaming pc', 'laptop'])
    
    # For system searches like gaming PCs, strongly prioritize complete systems over components
    if is_system_search:
        # Add extra filtering for components vs systems
        systems = []
        components = []
        
        for product in product_mentions:
            product_name = product.get("product", "").lower()
            
            # Check if this is likely a component (GPU, CPU, etc.)
            is_component = False
            
            # Check for standalone GPU
            if re.search(r'(rtx|gtx|radeon rx|arc)\s*[a-z]?\d{3,4}', product_name) and not re.search(r'(system|desktop|tower|pc|computer|gaming pc|laptop)', product_name):
                if len(product_name) < 20:  # Short with GPU model = just the GPU
                    is_component = True
            
            # Check for other components
            if any(component in product_name for component in ['ryzen', 'core i', 'intel', 'amd', 'processor', 'cpu', 'gpu', 'card', 'ram', 'memory']):
                if not re.search(r'(system|desktop|tower|pc|computer|gaming pc|laptop)', product_name):
                    is_component = True
            
            # Check for known system brands that indicate complete PCs
            system_brands = ['alienware', 'hp omen', 'dell xps', 'lenovo legion', 'asus rog', 'corsair', 'msi', 'acer predator', 'ibuypower', 'cyberpower']
            if any(brand in product_name for brand in system_brands):
                is_component = False  # Override - these are definitely systems
            
            if is_component:
                components.append(product)
            else:
                systems.append(product)
        
        # Strongly prefer systems over components for gaming PC searches
        if systems:
            valid_products = [p for p in systems if p.get("validity_score", 0) >= 3]
            if valid_products:
                selected_products = valid_products
                print(f"Debug: Using {len(valid_products)} valid system products")
            else:
                selected_products = systems
                print(f"Debug: Using {len(systems)} system products (no valid ones)")
        else:
            # Fall back to components if no systems found
            valid_products = [p for p in product_mentions if p.get("validity_score", 0) >= 3]
            if valid_products:
                selected_products = valid_products
                print(f"Debug: Using {len(valid_products)} valid component products")
            else:
                selected_products = product_mentions
                print(f"Debug: Using all {len(product_mentions)} products (no valid ones)")
    else:
        # For non-system searches (like vacuums, phones), use normal filtering
        valid_products = [p for p in product_mentions if p.get("validity_score", 0) >= 3]
        if valid_products:
            selected_products = valid_products
            print(f"Debug: Using {len(valid_products)} valid products for {product_type}")
        else:
            selected_products = product_mentions
            print(f"Debug: Using all {len(product_mentions)} products for {product_type} (no valid ones)")
    
    # Make sure we sort by score again after filtering
    selected_products.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Log selected products after filtering
    print(f"\n=== Debug: {source} products after filtering ===")
    for i, prod in enumerate(selected_products):
        print(f"{i+1}. {prod.get('product')} - Score: {prod.get('score', 0):.1f}, Validity: {prod.get('validity_score', 0)}")
    
    # Get the top-ranked product
    top_product = selected_products[0]
    product_model = top_product["product"]
    
    # Log the finally selected product
    print(f"\n=== Debug: Selected {source} product: {product_model} ===")
    
    # Make sure the product model is valid and sanitized
    if not product_model or len(product_model) < 3:
        return None
        
    # Sanitize product name - remove unwanted characters and trim excessive whitespace
    product_model = re.sub(r'[^\w\s\-]', '', product_model)
    product_model = re.sub(r'\s+', ' ', product_model).strip()
    
    # Get original description and attributes
    original_description = top_product.get("description", "")
    product_type = top_product.get("product_type", "product")
    attributes = []
    
    # Extract attributes from original product request if available
    if isinstance(product_type, str) and hasattr(product_type, 'split'):
        words = product_type.split()
        if len(words) > 1:
            # If product_type has multiple words, first word might be the actual product type
            # and rest could be attributes
            attributes = words[1:]
    
    # Add any explicit attributes
    if "attributes" in top_product and top_product["attributes"]:
        attributes.extend(top_product["attributes"])
    
    # Generate AI-enhanced description
    enhanced_description = generate_ai_description(
        product_model, 
        original_description, 
        product_type,
        attributes
    )
    
    # Format the recommendation
    result = {
        "product": product_model,
        "description": enhanced_description,
        "sources": [],
        "buy_link": generate_amazon_link(product_model),
        "image_url": generate_image_url(product_model),
        "validity_score": top_product.get("validity_score", 0),
        "attributes": top_product.get("attributes", [])
    }
    
    # Add source URLs
    # First add the top product's source
    if top_product.get("source") and top_product["source"] not in result["sources"]:
        result["sources"].append(top_product["source"])
    
    # Add additional sources from other mentions (include up to 3 sources)
    if len(product_mentions) > 1:
        for mention in product_mentions[1:5]:  # Check up to 5 more mentions to find unique sources
            if mention.get("source") and mention["source"] not in result["sources"] and len(result["sources"]) < 3:
                result["sources"].append(mention["source"])
    
    # If we still don't have any sources, use default format for the source type
    if not result["sources"]:
        if source == "reddit":
            result["sources"] = ["https://www.reddit.com"]
        elif source == "youtube":
            result["sources"] = ["https://www.youtube.com"]
    
    print(f"Final sources for {product_model} ({source}): {result['sources']}")
    return result

def generate_amazon_link(product_model):
    """
    Generate an Amazon link for a product model.
    
    Args:
        product_model (str): Product model name
        
    Returns:
        str: Amazon search link
    """
    # Clean the product name for use in URL
    clean_name = product_model.replace(' ', '+')
    
    # Create a valid-looking Amazon link that actually works
    return f"https://www.amazon.com/s?k={clean_name}&tag=allurecomreco-20"

def generate_image_url(product_model):
    """
    Generate a product image URL.
    Uses placeholder service.
    
    Args:
        product_model (str): Product model name
        
    Returns:
        str: Product image URL
    """
    # Clean the product name for use in URL
    clean_name = product_model.replace(' ', '+')
    
    # For real products, use a better placeholder service that might show the actual product
    return f"https://placehold.co/400x400/f5f5f5/333?text={clean_name}" 
