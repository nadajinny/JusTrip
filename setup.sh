#!/bin/bash

# setup.sh
# This script sets up the environment for the FastAPI application.

echo "Setting up environment..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi


echo "Activating virtual environment..."
source venv/bin/activate


echo "Installing Python dependencies..."
pip install -r requirements.txt


if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    touch .env
    echo "# Please add your API keys here" >> .env
    echo "Maps_API_KEY='your_Maps_api_key_here'" >> .env
    echo "OPENWEATHER_API_KEY='your_openweather_api_key_here'" >> .env
    echo "GEMINI_KEY='your_gemini_api_key_here'" >> .env
    echo "Remember to replace the placeholder API keys in .env with your actual keys."
else
    echo ".env file already exists."
fi

echo "Setup complete. To activate the virtual environment, run: source venv/bin/activate"
echo "To run the application, use: uvicorn main:app --reload"
echo "Make sure your API keys are correctly set in the .env file."