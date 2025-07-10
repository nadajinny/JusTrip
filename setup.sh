#!/bin/bash

echo "Upgrading pip globally..."
# Upgrade pip globally. This might require sudo on some systems.
sudo apt update 
sudo apt upgrade
sudo apt upgrade install python3-pip
if [ $? -ne 0 ]; then
    echo "Warning: Failed to upgrade pip. You might need to run this script with 'sudo' or address permissions."
fi

echo "Installing dependencies from requirements.txt globally..."
# Install dependencies globally. This might require sudo on some systems.
sudo pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies globally. Please check requirements.txt, your network connection, and permissions."
    exit 1
fi
echo "Dependencies installed globally."

echo "Starting Uvicorn server..."
uvicorn main:app --reload