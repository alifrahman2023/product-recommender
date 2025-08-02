import React from 'react';
import './ResultCard.css';

const ResultCard = ({ title, product, description, sources, buyLink, imageUrl }) => {
  // Use a default image if none provided
  const defaultImg = "https://via.placeholder.com/200x200?text=Product";
  
  return (
    <div className="result-card">
      <div className="result-header">
        <h2>{title}</h2>
      </div>
      
      <div className="result-content">
        <div className="product-image">
          <img src={imageUrl || defaultImg} alt={product} />
        </div>
        
        <div className="product-details">
          <h3>{product}</h3>
          <p className="description">{description}</p>
          
          {sources && sources.length > 0 && (
            <div className="sources">
              <h4>Sources:</h4>
              <ul>
                {sources.map((source, index) => (
                  <li key={index}>
                    <a href={source} target="_blank" rel="noopener noreferrer">
                      {source.length > 60 ? `${source.substring(0, 60)}...` : source}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {buyLink && (
            <a 
              href={buyLink} 
              className="buy-link" 
              target="_blank" 
              rel="noopener noreferrer"
            >
              View on Amazon
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResultCard; 
