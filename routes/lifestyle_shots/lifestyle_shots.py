from app import logger
import os
from flask import jsonify
import re
from .celery import process_image_task,processor
from utils import directory as DIR
import time

IMAGE_EXTENSIONS = ['.jpg', '.jpeg']
BUCKET_NAME=os.getenv("S3_BUCKET_NAME")
def sort_filenames(filenames):
    # Function to extract the number after '_raw_' using regex
    def extract_number(filename):
        match = re.search(r'_raw_(\d+)', filename)
        return int(match.group(1)) if match else 0

    # Sort the list based on the extracted number
    sorted_filenames = sorted(filenames, key=extract_number)
    return sorted_filenames

def lifestyle_shots(user_id,sku_id):
    path=f"./assets/batch_process_output/{user_id}/{sku_id}/raw"
    logger.info(f"Starting lifestyle shots for SKU: {sku_id}")
    if not DIR.check_folder_exists(path):
        raise ValueError(f"Folder '{path}' does not exist.")
    else:
        logger.info(f"Folder '{path}' exists.")
    files = DIR.list_files_in_directory(path)
    images = [file for file in files if os.path.splitext(file)[1].lower() in IMAGE_EXTENSIONS]
    if len(images) <=0:
        raise ValueError("No images found in the raw folder")
    count=0
    sorted_images=sort_filenames(images)
    task_ids = []
    processed_folder = os.path.join(f"./assets/batch_process_output/{user_id}/{sku_id}/processed/lifestyle_shots")
    logger.info(f"Processed folder: {processed_folder}")
    os.makedirs(processed_folder, exist_ok=True)
    for image in sorted_images:
        format=image.split('.')[-1]
        filepath=f"{path}/{image}"
        with open(filepath, 'rb') as file:
            file_content=file.read()
            filename=f"{user_id}_{sku_id}_{count+1}.{format}"
            logger.info(f"Processing image: {filename}")
            
            task_id=processor(file_content, filename, BUCKET_NAME,sku_id,count,filepath,user_id,processed_folder)
            task_ids.append(task_id)
            time.sleep(10)  
            count+=1
            if count==3:
                break
    return jsonify({"task_ids":task_ids}), 200
