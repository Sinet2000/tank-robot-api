#!/bin/bash
# Initialize environment and install required packages
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.tx

# Define the path to the yolov5 folder
yolov5_path=$(pwd)/neural_networks/yolov5

# Check if the yolov5 folder exists
if [ ! -d "$yolov5_path" ]; then
    # Clone the yolov5 repository from GitHub
    git clone https://github.com/ultralytics/yolov5 "$yolov5_path"
    cd $yolov5_path
    git reset --hard fbe67e465375231474a2ad80a4389efc77ecff99
fi

# Install the required packages
pip install -qr "$yolov5_path/requirements.txt"

pip install torch==1.8.0
pip install torchvision==0.9.0

cd ..
# Run the app
python app.py
