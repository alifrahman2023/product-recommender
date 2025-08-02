#!/bin/bash

# Start Flask backend in the background
echo "Starting Flask backend..."
cd backend
python app.py &
BACKEND_PID=$!

# Wait a moment for the backend to start
sleep 2

# Start React frontend
echo "Starting React frontend..."
cd ../frontend
npm start

# When the React process ends, kill the Flask process
kill $BACKEND_PID 
