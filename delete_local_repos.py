from dotenv import load_dotenv
import os
import shutil
import stat
import subprocess
import time

def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def force_delete_directory(path):
    """Force delete a directory and its contents on Windows"""
    if not os.path.exists(path):
        return
    
    print(f"Attempting to delete {path}")
    
    # First, try to close any Git processes
    if os.path.exists(os.path.join(path, '.git')):
        try:
            subprocess.run(['git', 'gc'], cwd=path, capture_output=True)
        except Exception as e:
            print(f"Warning: Could not run git gc: {e}")
    
    # Make all files writable
    for root, dirs, files in os.walk(path):
        for dir_name in dirs:
            try:
                os.chmod(os.path.join(root, dir_name), stat.S_IWRITE)
            except Exception as e:
                print(f"Warning: Could not change permissions on directory {dir_name}: {e}")
        for file_name in files:
            try:
                os.chmod(os.path.join(root, file_name), stat.S_IWRITE)
            except Exception as e:
                print(f"Warning: Could not change permissions on file {file_name}: {e}")

    # Try to delete with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path, onerror=remove_readonly)
            print(f"Successfully deleted {path}")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed, retrying in 1 second... Error: {e}")
                time.sleep(1)
            else:
                print(f"Failed to delete {path} after {max_retries} attempts: {e}")
                raise

# Main execution
load_dotenv()

json_repo_path = os.getenv("SAMPLE_JSON_REPO")
code_repo_path = os.getenv("SAMPLE_CODE_REPO")

if not json_repo_path or not code_repo_path:
    raise ValueError("Environment variables SAMPLE_JSON_REPO and SAMPLE_CODE_REPO must be set")

print(f"Processing repositories: {json_repo_path} and {code_repo_path}")

# Get local paths
json_repo_path = os.path.basename(json_repo_path).split(".")[0]
json_repo_path = os.path.join(os.getcwd(), json_repo_path)
print(f"Local JSON repo path: {json_repo_path}")

code_repo_path = os.path.basename(code_repo_path).split(".")[0]
code_repo_path = os.path.join(os.getcwd(), code_repo_path)
print(f"Local Code repo path: {code_repo_path}")

# Delete the directories
try:
    force_delete_directory(json_repo_path)
    force_delete_directory(code_repo_path)
    print("All directories deleted successfully")
except Exception as e:
    print(f"Error during deletion: {e}")
    raise
