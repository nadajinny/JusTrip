#!/bin/bash

echo "Upgrading pip globally..."
pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "Warning: Failed to upgrade pip. You might need to run this script with 'sudo' or
address permissions."
fi

echo "Installing dependencies from requirements.txt globally..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies globally. Please check requirements.txt, your network connection, and permissions."
    exit 1
fi
echo "Dependencies installed globally."

echo "Starting Uvicorn server..."
cd backend
uvicorn main:app --reload