#!/bin/bash
# Initialize environment and install required packages
python3.9 -m venv venv
source venv/bin/activate

# Setup conda env
# Install Miniconda (replace Miniconda3-latest-Linux-x86_64.sh with the appropriate file for your system)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p $PWD/miniconda

# Activate the conda environment
source $PWD/miniconda/bin/activate

# Create a new environment called "flask-env" and install Flask
conda create -n tank-robot-api-env flask

# Activate the "flask-env" environment
conda activate tank-robot-api-env

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
