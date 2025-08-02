# Product Recommender: Technical Documentation

## Architecture Overview

The Product Recommender is a full-stack web application built with a React frontend and a Flask backend. It uses web scraping techniques to extract product recommendations from social media platforms (Reddit and YouTube), processes this data, and presents the most relevant product recommendations to users.

## System Components

### Backend Components

1. **Flask API Server (`app.py`)**
   - Provides a RESTful API endpoint `/search` that accepts POST requests
   - Processes user queries by product name and attributes
   - Coordinates the data collection, processing, and recommendation pipeline

2. **Scraper Module (`scraper.py`)**
   - Implements specialized scraping functions for different data sources:
     - `scrape_reddit()`: Extracts data from Reddit using multiple approaches
     - `scrape_youtube()`: Extracts data from YouTube videos
   - Uses various fallback mechanisms to ensure data retrieval
   - Implements request caching and error handling for robustness

3. **Recommender Module (`recommender.py`)**
   - `process_and_rank_products()`: Main entry point for the recommendation pipeline
   - Implements concurrent processing with timeouts for efficient data collection
   - Contains product extraction, validation, and ranking algorithms
   - Generates formatted recommendations for the frontend

4. **Utilities Module (`utils.py`)**
   - Provides helper functions for text processing and data extraction
   - Implements product model extraction using regex patterns
   - Provides sentiment analysis for recommendation context

### Frontend Components

1. **Home Page (`Home.jsx`)**
   - Landing page with search form interface
   - Captures user input for product type and desired attributes

2. **Search Form Component (`SearchForm.jsx`)**
   - Processes user input and sends requests to the backend API
   - Handles form validation and loading states
   - Stores search results in session storage for state persistence

3. **Results Page (`Results.jsx`)**
   - Displays processed recommendations from different sources
   - Implements conditional rendering based on available data
   - Provides links to purchase products and view source recommendations

4. **Source-specific Components**
   - `RedditComponent`: Renders Reddit-sourced recommendations
   - `YouTubeComponent`: Renders YouTube-sourced recommendations

## Technical Workflow

1. **Data Collection Flow**
   - User submits a product search query with optional attributes
   - Backend concurrently scrapes multiple sources (Reddit, YouTube) with timeouts
   - For Reddit: Uses Google Custom Search API with fallback to direct Reddit search
   - For YouTube: Searches for review videos and extracts transcripts

2. **Data Processing Flow**
   - Extracted content is analyzed to identify product mentions
   - Product models are validated using regex patterns and contextual analysis
   - Product sentiment is evaluated based on surrounding text
   - Products are ranked based on mention frequency, context, and attribute match

3. **Recommendation Engine**
   - Uses rule-based filtering to identify valid product models
   - Implements scoring algorithms to rank product mentions
   - Generates formatted recommendations with descriptions and links
   - Creates Amazon affiliate links for monetization

4. **Response Handling**
   - Backend returns structured JSON with recommendations by source
   - Frontend parses response and renders recommendations
   - Handles error states and empty results gracefully

## Technologies Used

### Backend
- **Python**: Core programming language
- **Flask**: Web framework for API endpoints
- **Concurrent Processing**: ThreadPoolExecutor for parallel scraping
- **Web Scraping**: Requests and BeautifulSoup4 for HTML parsing
- **API Integration**: Google Custom Search, YouTube Data API
- **Text Processing**: Regex pattern matching, sentiment analysis

### Frontend
- **React**: JavaScript library for UI components
- **React Router**: For client-side routing
- **CSS3**: For styling and responsive design
- **Session Storage**: For state persistence between pages

## Key Technical Features

1. **Parallel Data Collection**
   - Concurrent scraping with timeouts prevents hangs
   - Multiple fallback mechanisms ensure robust data collection

2. **Product Validation**
   - Sophisticated regex patterns identify real product models
   - Rule-based filtering removes false positives
   - Product-specific validation (e.g., GPU model validation)

3. **Stateless Architecture**
   - Backend is fully stateless for scalability
   - Frontend uses session storage for temporary state

4. **Error Handling**
   - Graceful degradation when sources are unavailable
   - Timeout mechanisms prevent blocking operations

## Security Considerations

- **API Key Management**: Environment variables for sensitive keys
- **Input Validation**: Backend validation prevents injection attacks
- **CORS Protection**: Configured for secure cross-origin requests

## Performance Optimizations

- **Concurrent Processing**: Parallel scraping of multiple sources
- **Timeout Mechanisms**: Prevent hanging on unresponsive sources
- **Response Caching**: Session storage prevents redundant API calls 
