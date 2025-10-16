import subprocess
import yaml
import os

def launch_sbatch_from_recipe(recipe_path="recipe.yml"):
    # Load recipe.yml
    with open(recipe_path, "r") as f:
        recipe = yaml.safe_load(f)

    # Find sbatch scripts in recipe
    sbatch_scripts = []
    if "sbatch" in recipe:
        # If recipe.yml has a top-level 'sbatch' key
        sbatch_scripts = recipe["sbatch"]
    elif "jobs" in recipe:
        # Or if jobs are listed under 'jobs'
        for job in recipe["jobs"]:
            if isinstance(job, dict) and "sbatch" in job:
                sbatch_scripts.append(job["sbatch"])
            elif isinstance(job, str):
                sbatch_scripts.append(job)
    else:
        print("No sbatch scripts found in recipe.yml")
        return

    # Submit each sbatch script
    for script in sbatch_scripts:
        if not os.path.isfile(script):
            print(f"Script {script} not found, skipping.")
            continue
        print(f"Submitting {script}")
        subprocess.run(["sbatch", script])

if __name__ == "__main__":
    launch_sbatch_from_recipe()