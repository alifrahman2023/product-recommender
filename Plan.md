🛒 Product Recommender MVP — Final Project Plan (Cursor Ready)
📝 Overview

A web app where users enter a product and desired attributes (e.g., "cheap", "durable"). The app fetches product recommendations from Reddit, YouTube, and Quora using web scraping, search APIs, and OpenAI for extraction and summarization.
🎯 MVP Goal

    Input: Product name + attribute tags.

    Output: Recommended specific product models with descriptions, sources, Amazon buy links.

    Tech Stack:

        Frontend: React, JS, CSS (no Tailwind).

        Backend: Flask (Python), OpenAI API, scraping scripts.

🗺️ Pages & Components
1. Home Page (/)

    Logo button (top-left) → redirects home.

    Search form:

        Product input (e.g., "vacuum cleaner").

        Attributes input (e.g., "cheap", "cordless").

        Submit → sends POST to /search.

2. Results Page (/results)

    Logo button (top-left) → redirects home.

    Result Components:

        RedditComponent

        YouTubeComponent

        QuoraComponent

Each component shows:

    Product Name & Image.

    Description (why recommended).

    Sources (links to posts/videos/answers).

    Amazon Quick Buy link.

🔎 Data Retrieval & Processing
Input:

    { "product": "vacuum cleaner", "attributes": ["cheap", "cordless"] }

Retrieval:
Platform	Method
Reddit	Google Search (site:reddit.com) → scrape threads & comments.
YouTube	YouTube Data API → fetch video transcripts.
Quora	Google Search (site:quora.com) → scrape answers.
Product Extraction:

    Use OpenAI API with prompt:

        "Extract specific product model names mentioned in this text (e.g., Dyson V15 Detect, iPhone 10). Ignore vague brand mentions. Return JSON array."

    Run this on all scraped text.

Ranking:

    Count mentions across sources.

    Weight by popularity:

        Reddit upvotes.

        YouTube likes/views.

        Quora upvotes.

    Filter by positive sentiment (OpenAI API sentiment classification).

Output Format:

{
  "reddit": {
    "product": "Dyson V15 Detect",
    "description": "Highly recommended for its powerful suction and cordless design.",
    "sources": ["https://reddit.com/r/vacuums/..."],
    "buy_link": "https://amazon.com/dp/B08XZV3JB2"
  },
  "youtube": {
    "product": "Shark Navigator Lift-Away",
    "description": "Praised for affordability and durability in multiple reviews.",
    "sources": ["https://youtube.com/watch?v=abc123"],
    "buy_link": "https://amazon.com/dp/B004T0DW6G"
  },
  "quora": { ... }
}

🖌️ UI Design

    Color theme:

        Background: White.

        Accents: Light Gray.

        Highlights: Light Blue.

    Simple, modern layout.

    Responsive desktop & mobile.

📦 Project Structure

/frontend
  /components
    SearchForm.jsx
    ResultCard.jsx
    RedditComponent.jsx
    YouTubeComponent.jsx
    QuoraComponent.jsx
  /pages
    Home.jsx
    Results.jsx
  App.jsx
  index.css
  index.js

/backend
  app.py (Flask API)
  scraper.py (Reddit, YouTube, Quora scrapers)
  recommender.py (LLM processing, ranking logic)
  utils.py (NER extraction, sentiment analysis)

.env (OpenAI, Google, YouTube API keys)

🛠️ API Endpoints
Endpoint	Method	Description
/search	POST	Accepts product & attributes. Returns top recommended products per source.
✅ MVP Success Criteria

    User submits product query.

    App returns top 1 product per source (Reddit, YouTube, Quora).

    Each has description, sources, Amazon buy link.

    Functional, styled UI.

🔑 Key OpenAI Prompt (NER Extraction)

"Given the following text, extract the names of specific product models mentioned (e.g., Dyson V15 Detect, iPhone 10, Sony WH-1000XM5). Ignore vague mentions like 'Apple' or 'Dyson'. Return only the product model names as a JSON array."
