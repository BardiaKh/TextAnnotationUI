#!/bin/bash

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate base
cd /home/ubuntu/UI/
python stats.py >> notification.log 2>&1