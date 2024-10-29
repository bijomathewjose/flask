import cv2
import numpy as np
from utils import db
import openvino as ov
from pathlib import Path
from transformers import AutoModelForImageSegmentation
from utils import directory as DIR
import os
import re
import boto3
import mimetypes
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def center_align_subject(image):
    """Center the subject within a new blank canvas."""
    alpha_channel = image[:, :, 3]
    coords = cv2.findNonZero(alpha_channel)
    x, y, w, h = cv2.boundingRect(coords)
    subject_region = image[y:y + h, x:x + w]

    centered_image = np.zeros_like(image)
    center_x = (image.shape[1] - w) // 2
    center_y = (image.shape[0] - h) // 2
    centered_image[center_y:center_y + h, center_x:center_x + w] = subject_region
    return centered_image

def add_white_background(image):
    """Add a white background to an image with a transparent background."""
    white_background = np.ones_like(image) * 255
    for c in range(3):  
        white_background[:, :, c] = image[:, :, c] * (image[:, :, 3] / 255.0) + 255 * (1 - (image[:, :, 3] / 255.0))

    return white_background    

def store_image_in_db(connection, s3_url, sku_id, index):
    field_name = f"img_{index}"
    query = f"UPDATE all_platform_products SET {field_name} = %s WHERE sku = %s"
    params = [s3_url, sku_id]  # Pass as tuple
    db.execute_query(connection, query, params)

MODEL_INPUT_SIZE = [1024, 1024]
OV_MODEL_PATH = Path("models/rmbg-1.4.xml")
DEVICE = "AUTO"
OV_COMPILED_MODEL = None
NET= AutoModelForImageSegmentation.from_pretrained("briaai/RMBG-1.4", trust_remote_code=True)

def setup_openvino_model():
        if not OV_MODEL_PATH.exists():
        # Convert the model and save it
            example_input = np.zeros((1, 3, *MODEL_INPUT_SIZE), dtype=np.uint8)
            ov_model = ov.convert_model(NET, example_input, [1, 3, *MODEL_INPUT_SIZE])
            ov.save_model(ov_model, OV_MODEL_PATH)

        core = ov.Core()
        ov_compiled_model = core.compile_model(OV_MODEL_PATH, DEVICE)
        if not ov_compiled_model:
            raise "Failed to compile the model"
        return ov_compiled_model

def sort_filenames(filenames):
    # Function to extract the number after '_raw_' using regex
    def extract_number(filename):
        match = re.search(r'_raw_(\d+)', filename)
        return int(match.group(1)) if match else 0

    # Sort the list based on the extracted number
    sorted_filenames = sorted(filenames, key=extract_number)
    return sorted_filenames

def get_raw_images(sku_id,folder_path,allowed_extensions):
    filenames=[f"{sku_id}_raw_{i}" for i in range(1,5)]
    files=DIR.list_files_in_directory(folder_path)
    image_files=[file for file in files if os.path.splitext(file)[1].lower() in allowed_extensions]
    required_files=[]
    for file_name in image_files:
        if any(file_name.startswith(path) for path in filenames):
            required_files.append(file_name)
    sorted_files=sort_filenames(required_files)
    return sorted_files

def upload_to_s3(file_path, s3_key):
    # Initialize a session using Amazon S3
    s3_client = boto3.client(
        's3',
        region_name=os.getenv("AWS_DEFAULT_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )

    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = "application/octet-stream"

    try:
        # Upload the file to the S3 bucket
        s3_client.upload_file(file_path, S3_BUCKET_NAME, s3_key,
            ExtraArgs={
                "ContentType": content_type,
                "ContentDisposition": "inline"
            }
        )
        
        print(f"File {file_path} uploaded to S3 as {s3_key}.")

        s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        return s3_url
    
    except Exception as e:
        print(f"Failed to upload {file_path} to S3: {e}")