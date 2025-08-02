# Apply monkey patching before any other imports
import gevent.monkey
gevent.monkey.patch_all()

# Increase default timeout for requests
import socket
socket.setdefaulttimeout(30)

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv
from recommender import process_and_rank_products
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Dictionary to store background tasks
background_tasks = {}

@app.route('/search', methods=['POST'])
def search():
    """
    Endpoint to search for product recommendations based on product name and attributes.
    Expected JSON input: {'product': 'vacuum cleaner', 'attributes': ['cheap', 'cordless']}
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        product = data.get('product')
        attributes = data.get('attributes', [])
        
        if not product:
            return jsonify({"error": "Product name is required"}), 400
            
        # Process product recommendations based on the query
        results = process_and_rank_products(product, attributes)
            
        return jsonify(results)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True) 
