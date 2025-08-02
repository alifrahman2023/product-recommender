import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import RedditComponent from '../components/RedditComponent';
import YouTubeComponent from '../components/YouTubeComponent';
import './Results.css';

const Results = () => {
  const [results, setResults] = useState(null);
  const [query, setQuery] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Check if we have results in sessionStorage
    const storedResults = sessionStorage.getItem('searchResults');
    const storedQuery = sessionStorage.getItem('searchQuery');
    
    if (!storedResults || !storedQuery) {
      // No results found, redirect to home
      navigate('/');
      return;
    }
    
    try {
      const rawResults = JSON.parse(storedResults);
      setQuery(JSON.parse(storedQuery));
      
      // Debug data
      console.log("Raw Results:", rawResults);
      
      // If the searchResults is already in the new format, use it directly
      if (rawResults.reddit || rawResults.youtube) {
        setResults(rawResults);
      } else if (rawResults.products && rawResults.products.length > 0) {
        // Format the new API response to match what the components expect
        // Find products for each source
        const redditProduct = rawResults.products.find(p => p.sources.includes('reddit'));
        const youtubeProduct = rawResults.products.find(p => p.sources.includes('youtube'));
        
        const formattedResults = {};
        
        // Format the reddit product if found
        if (redditProduct) {
          formattedResults.reddit = {
            product: redditProduct.name,
            description: redditProduct.reason,
            sources: Array.isArray(redditProduct.urls) ? redditProduct.urls.filter(url => url && url.includes('reddit.com')) : [],
            buy_link: `https://www.amazon.com/s?k=${encodeURIComponent(redditProduct.name)}`,
            image_url: `https://placehold.co/400x400/f5f5f5/333?text=${encodeURIComponent(redditProduct.name.replace(/ /g, '+'))}`
          };
        }
        
        // Format the youtube product if found
        if (youtubeProduct) {
          formattedResults.youtube = {
            product: youtubeProduct.name,
            description: youtubeProduct.reason,
            sources: Array.isArray(youtubeProduct.urls) ? youtubeProduct.urls.filter(url => url && url.includes('youtube.com')) : [],
            buy_link: `https://www.amazon.com/s?k=${encodeURIComponent(youtubeProduct.name)}`,
            image_url: `https://placehold.co/400x400/f5f5f5/333?text=${encodeURIComponent(youtubeProduct.name.replace(/ /g, '+'))}`
          };
        }
        
        setResults(formattedResults);
      } else {
        setResults(null);
      }
    } catch (error) {
      console.error('Error parsing stored results:', error);
      navigate('/');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  // Additional debugging useEffect
  useEffect(() => {
    if (results) {
      console.log("Results state after loading:", results);
      if (results.reddit) {
        console.log("Reddit product data:", results.reddit);
      }
      if (results.youtube) {
        console.log("YouTube product data:", results.youtube);
      }
    }
  }, [results]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Finding the best products for you...</p>
      </div>
    );
  }

  return (
    <div className="results-page">
      <div className="header">
        <Link to="/" className="logo">
          <img src="/logo-placeholder.png" alt="Product Recommender" />
          <span>Product Recommender</span>
        </Link>
      </div>
      
      {query && (
        <div className="search-info">
          <h1>Results for: {query.product}</h1>
          {query.attributes && query.attributes.length > 0 && (
            <div className="attribute-tags">
              {query.attributes.map((attr, index) => (
                <span key={index} className="attribute-tag">{attr}</span>
              ))}
            </div>
          )}
        </div>
      )}
      
      <div className="results-container">
        {results && (
          <>
            {results.reddit && <RedditComponent data={results.reddit} />}
            {results.youtube && <YouTubeComponent data={results.youtube} />}
          </>
        )}
        
        {(!results || (!results.reddit && !results.youtube)) && (
          <div className="no-results">
            <h2>No recommendations found</h2>
            <p>Try searching for a different product or with different attributes.</p>
            <Link to="/" className="back-button">Back to Search</Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default Results; 
