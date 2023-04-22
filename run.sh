#!/bin/bash

# Define the path to the yolov5 folder
yolov5_path=$(pwd)/neural_networks/yolov5

# Check if the yolov5 folder exists
if [ ! -d "$yolov5_path" ]; then
    # Clone the yolov5 repository from GitHub
    git clone https://github.com/ultralytics/yolov5 "$yolov5_path"
fi

# Install the required packages using pip
pip install -r "$yolov5_path/requirements.txt"

# Run the app
python app.py