import React from 'react';
import ResultCard from './ResultCard';

const RedditComponent = ({ data }) => {
  if (!data || !data.product) {
    return null;
  }
  
  // Always use the RedditLogo.png for the image
  const redditLogo = "/RedditLogo.png";
  
  // Debug output to console
  console.log("Reddit Component Data:", data);
  
  return (
    <ResultCard
      title="Reddit Recommendation"
      product={data.product}
      description={data.description}
      sources={data.sources}
      buyLink={data.buy_link}
      imageUrl={redditLogo}
    />
  );
};

export default RedditComponent; 
