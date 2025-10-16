#!/bin/bash
#SBATCH --job-name=launcher
#SBATCH --account=p200981
#SBATCH --qos=default
#SBATCH --output=launcher_output.log
#SBATCH --error=launcher_error.log
#SBATCH --time=01:00:00
#SBATCH --partition=standard
#SBATCH --ntasks=1

# Launch middleware
python3 ../src/middleware_interface.py

# 

# Launch clients
sbatch_scripts=("job1.sbatch" "job2.sbatch" "job3.sbatch")

for script in "${sbatch_scripts[@]}"
do
    echo "Submitting $script"
    sbatch "$script"
done