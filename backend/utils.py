import os
import json
import re
import warnings
from openai import OpenAI
from dotenv import load_dotenv

# Suppress SSL warnings since we're using verify=False in requests
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Load environment variables
load_dotenv()

# Set up OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_product_models(text):
    """
    Use OpenAI API to extract specific product model names from text.
    
    Args:
        text (str): The text to extract product models from
        
    Returns:
        list: Extracted product model names
    """
    if not text:
        return []
        
    try:
        if not os.getenv('OPENAI_API_KEY'):
            print("Warning: OpenAI API key not found. Using regex extraction.")
            return regex_extract_product_models(text)
        
        prompt = f"""
        Given the following text, extract the names of specific product models mentioned (e.g., Dyson V15 Detect, iPhone 14, Sony WH-1000XM5).
        Ignore vague mentions like 'Apple' or 'Dyson'.
        Return only the product model names as a JSON array.
        
        Text: {text}
        """
        
        # Using v1.3.0 API format with the OpenAI client
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You extract specific product model names from text and return them as a JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            # Parse the response (format for v1.3.0)
            content = response.choices[0].message.content.strip()
            
            # Process the content to extract product names
            try:
                # Try to parse as JSON directly
                products = json.loads(content)
                if isinstance(products, list):
                    return products
            except:
                # If not valid JSON, try to extract JSON part
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        products = json.loads(json_match.group(0))
                        if isinstance(products, list):
                            return products
                    except:
                        pass
            
            # Final fallback for JSON parsing
            if '[' in content and ']' in content:
                items = content.split('[')[1].split(']')[0].split(',')
                return [item.strip().strip('"\'') for item in items if item.strip()]
            
        except Exception as e:
            print(f"Error with OpenAI API: {e}")
            # Fall back to regex extraction
            return regex_extract_product_models(text)
            
        # If we got here and have no products, use regex extraction
        return regex_extract_product_models(text)
    
    except Exception as e:
        print(f"Error extracting product models: {e}")
        return regex_extract_product_models(text)

def regex_extract_product_models(text):
    """
    Extract product models using regex patterns as a fallback.
    
    Args:
        text (str): The text to extract from
        
    Returns:
        list: Extracted product models
    """
    products = []
    
    # Phone patterns
    phone_patterns = [
        r'iPhone\s+\d+(\s+Pro)?(\s+Max)?',
        r'Samsung\s+Galaxy\s+S\d+(\s+Ultra)?',
        r'Google\s+Pixel\s+\d+(\s+Pro)?',
        r'OnePlus\s+\d+(\s+Pro)?',
        r'Xiaomi\s+Mi\s+\d+',
        r'Motorola\s+\w+\s+\d+'
    ]
    
    # Vacuum patterns
    vacuum_patterns = [
        r'Dyson\s+V\d+(\s+\w+)?',
        r'Shark\s+\w+(\s+\w+)*',
        r'Miele\s+\w+(\s+\w+)*',
        r'Bissell\s+\w+(\s+\w+){0,3}',
        r'Hoover\s+\w+(\s+\w+){0,3}',
        r'Tineco\s+\w+(\s+\w+){0,3}',
        r'Eureka\s+\w+(\s+\w+){0,3}'
    ]
    
    all_patterns = phone_patterns + vacuum_patterns
    
    for pattern in all_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                products.append(match.group(0).strip())
    
    # Generic brand-model pattern
    generic_pattern = r'([A-Z][a-zA-Z0-9]+ [A-Z0-9][a-zA-Z0-9]+(?:[- ][A-Z0-9][a-zA-Z0-9]+){0,2})'
    for match in re.finditer(generic_pattern, text):
        if match.group(0) not in products:
            products.append(match.group(0).strip())
    
    return products

def analyze_sentiment(text):
    """
    Analyze sentiment of text to determine if a product mention is positive.
    Uses OpenAI API to analyze sentiment.
    
    Args:
        text (str): The text to analyze sentiment for
        
    Returns:
        float: Sentiment score between 0 (negative) and 1 (positive)
    """
    if not text:
        return 0.5  # Neutral for empty text
    
    try:
        if not os.getenv('OPENAI_API_KEY'):
            print("Warning: OpenAI API key not found. Using basic sentiment analysis.")
            return basic_sentiment_analysis(text)
        
        prompt = f"""
        Analyze the sentiment of this text regarding a product. Score between 0 and 1:
        0 = extremely negative
        0.5 = neutral
        1 = extremely positive
        
        Return only a single number between 0 and 1.
        
        Text: {text}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You analyze sentiment and return a score between 0 and 1."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        content = response.choices[0].message.content.strip()
        
        # Extract the number
        try:
            sentiment_score = float(re.search(r'(\d+\.\d+|\d+)', content).group(0))
            # Ensure it's in range 0-1
            sentiment_score = max(0, min(1, sentiment_score))
            return sentiment_score
        except:
            print("Could not extract sentiment score from OpenAI response. Using basic analysis.")
            return basic_sentiment_analysis(text)
    
    except Exception as e:
        print(f"Error analyzing sentiment: {e}")
        return basic_sentiment_analysis(text)

def basic_sentiment_analysis(text):
    """
    Basic rule-based sentiment analysis as fallback.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        float: Sentiment score between 0 and 1
    """
    text_lower = text.lower()
    
    positive_terms = ['good', 'great', 'excellent', 'best', 'love', 'recommend', 'amazing', 'fantastic', 
                     'worth', 'quality', 'reliable', 'impressive', 'perfect', 'awesome', 'satisfied']
    
    negative_terms = ['bad', 'poor', 'terrible', 'worst', 'hate', 'avoid', 'disappointing', 'broken', 
                     'waste', 'regret', 'awful', 'horrible', 'useless', 'failed', 'cheap', 'overpriced']
    
    positive_count = sum(1 for term in positive_terms if term in text_lower)
    negative_count = sum(1 for term in negative_terms if term in text_lower)
    
    total_count = positive_count + negative_count
    
    if total_count == 0:
        return 0.5  # Neutral if no sentiment terms found
        
    return positive_count / total_count 
