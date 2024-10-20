import subprocess
import os

def make_empty_commit():
    print()
    print("START")
    os.chdir("/Users/jackyliao/Desktop/Uni/Personal Projects/budget-tracker")

    # Start the SSH agent (only necessary if the agent is not already running)
    # It's better to check if the SSH agent is running or not.
    try:
        subprocess.run("eval $(ssh-agent -s)", shell=True, check=True)
    except subprocess.CalledProcessError:
        print("SSH agent is already running.")

    # Add your SSH key (if needed)
    # Ensure to provide the full path to your private key.
    try:
        subprocess.run("ssh-add ~/.ssh/id_rsa", shell=True, check=True)  # Change to your private key path if necessary
    except subprocess.CalledProcessError as e:
        print(f"Failed to add SSH key: {e}")

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
