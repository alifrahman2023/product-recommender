import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './SearchForm.css';

const SearchForm = () => {
  const [product, setProduct] = useState('');
  const [attributes, setAttributes] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!product.trim()) {
      alert('Please enter a product name');
      return;
    }

    // Convert attributes to array and trim whitespace
    const attributesArray = attributes
      .split(',')
      .map(attr => attr.trim())
      .filter(attr => attr.length > 0);
    
    setIsLoading(true);
    
    try {
      const response = await fetch('http://localhost:5001/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product: product.trim(),
          attributes: attributesArray,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Search request failed');
      }
      
      const data = await response.json();
      
      // Debug the API response
      console.log("API Response:", data);
      
      // Store the original API response directly without transformation
      sessionStorage.setItem('searchResults', JSON.stringify(data));
      sessionStorage.setItem('searchQuery', JSON.stringify({
        product: product.trim(),
        attributes: attributesArray,
      }));
      
      // Navigate to results page
      navigate('/results');
    } catch (error) {
      console.error('Search error:', error);
      alert('Failed to search for products. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="search-form-container">
      <form className="search-form" onSubmit={handleSubmit}>
        <div className="form-group">
          <input
            type="text"
            id="product"
            placeholder="Enter a product (e.g., vacuum cleaner, headphones, coffee maker)"
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            className="product-input"
            required
          />
        </div>
        
        <div className="form-group">
          <input
            type="text"
            id="attributes"
            placeholder="Enter desired attributes, separated by commas (e.g., cheap, durable, wireless)"
            value={attributes}
            onChange={(e) => setAttributes(e.target.value)}
            className="attributes-input"
          />
        </div>
        
        <button 
          type="submit" 
          className="search-button"
          disabled={isLoading}
        >
          {isLoading ? 'Searching...' : 'Find Products'}
        </button>
      </form>
    </div>
  );
};

export default SearchForm; 
