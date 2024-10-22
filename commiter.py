import subprocess
import os

def make_empty_commit():
    print()
    print("START")
    os.chdir("/Users/jackyliao/Desktop/Uni/Personal Projects/budget-tracker")

    try:
        # Run the Git command to create an empty commit
        subprocess.run(['git', 'add', '.'], check=True) 
        subprocess.run(['git', 'commit', '--allow-empty', '-m', 'Regular empty commit'], check=True)
        subprocess.run(['git', 'push'], check=True)
        print("Empty commit made successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error making empty commit: {e}")

if __name__ == "__main__":
    make_empty_commit()
