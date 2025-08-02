import React from 'react';
import ResultCard from './ResultCard';

const YouTubeComponent = ({ data }) => {
  if (!data || !data.product) {
    return null;
  }
  
  // Always use the YoutubeLogo.png for the image
  const youtubeLogo = "/YoutubeLogo.png";
  
  return (
    <ResultCard
      title="YouTube Recommendation"
      product={data.product}
      description={data.description}
      sources={data.sources}
      buyLink={data.buy_link}
      imageUrl={youtubeLogo}
    />
  );
};

export default YouTubeComponent; 
