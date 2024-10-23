import os

def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return True
    else:
        raise ValueError(f"Folder '{folder_path}' already exists.")
    
def list_files_in_directory(folder_path):
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # List all files in the directory
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        return files
    else:
        raise ValueError(f"'{folder_path}' does not exist or is not a directory.")
    
def check_folder_exists(folder_path):
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        return True
    else:
        return False