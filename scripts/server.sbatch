#!/bin/bash
#SBATCH --job-name=server
#SBATCH --time=02:00:00
#SBATCH --account=p200981
#SBATCH --qos=default
#SBATCH --ntasks=1

# Launch middleware
python3 ../src/server.py 22000
