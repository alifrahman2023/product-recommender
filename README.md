# Product Recommender App

A web application that recommends specific products based on product type and desired attributes by scraping recommendations from Reddit, YouTube, and Quora.

## Project Structure

```
/frontend                 # React frontend
  /public                 # Static assets
  /src
    /components           # Reusable React components
    /pages                # Page components
    App.jsx               # Main React component
    index.js              # Entry point

/backend                  # Flask backend
  app.py                  # Flask API server
  scraper.py              # Web scraping modules
  recommender.py          # Product extraction and ranking
  utils.py                # Helper utilities
```

## Prerequisites

- Node.js (v14+)
- Python (v3.8+)
- pip
- npm

## Setup and Installation

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd product-recommender/backend
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the backend directory with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   YOUTUBE_API_KEY=your_youtube_api_key
   GOOGLE_SEARCH_API_KEY=your_google_search_api_key
   GOOGLE_SEARCH_ENGINE_ID=your_google_search_engine_id
   ```

5. Start the Flask server:
   ```
   python app.py
   ```
   The server will run on http://localhost:5000

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd product-recommender/frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the React development server:
   ```
   npm start
   ```
   The application will be available at http://localhost:3000

## Future Enhancements

- Add user accounts and saved searches
- Integrate with Amazon Affiliate API for accurate product links
- Add more sources for recommendations 
