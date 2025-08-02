import React from 'react';
import { Link } from 'react-router-dom';
import SearchForm from '../components/SearchForm';
import './Home.css';

const Home = () => {
  return (
    <div className="home-page">
      <div className="logo-container">
        <Link to="/" className="logo">
          <img src="/logo-placeholder.png" alt="Product Recommender" />
          <span>Product Recommender</span>
        </Link>
      </div>
      
      <div className="search-container">
        <h1>Find the Best Products For You</h1>
        <SearchForm />
      </div>
    </div>
  );
};

export default Home; 
