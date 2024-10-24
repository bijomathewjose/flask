from config.flask import create_app
from dotenv import load_dotenv
from flask import render_template, jsonify, request,send_file
import zipfile
import os
import cv2
import pandas as pd
import numpy as np
from transformers import AutoModelForImageSegmentation
import openvino as ov
from pathlib import Path
from werkzeug.utils import secure_filename
import boto3
import mimetypes
from utils import db

load_dotenv()

app, celery ,logger = create_app()

from routes import api_v1,lifestyle_shots as LS
from utils.csv_parser import parse_csv_to_list

app.register_blueprint(api_v1, url_prefix='/api/v1')

def store_image_in_db(connection, s3_url, sku_id, index):
    field_name = f"img_{index}"
    query = f"UPDATE all_platform_products SET {field_name} = %s WHERE sku = %s"
    params = [s3_url, sku_id]  # Pass as tuple
    db.execute_query(connection, query, params)

@app.route('/')
def index():
    logger.info("index")
    return render_template('index.html')
    
@app.route('/health')
def health():
    return "Server is Healthy", 200

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'csv' not in request.files:
        return jsonify({"error": "No CSV file part"}), 400

    csv_file = request.files['csv']
    seller_id = request.form.get('sellerId')
    partner_id = request.form.get('partnerId')

    if not seller_id or not partner_id:
        return jsonify({"error": "Seller ID and Partner ID are required"}), 400

    if not (csv_file and allowed_file(csv_file.filename)):
        return jsonify({"error": "Invalid CSV file type"}), 400

    # Save the uploaded CSV file temporarily
    csv_filename = secure_filename(csv_file.filename)
    csv_path = os.path.join('uploads', csv_filename)
    csv_file.save(csv_path)

    # Read the CSV file to get the SKU ID and process_id
    try:
        list_of_process = parse_csv_to_list(csv_path)
    except Exception as e:
        return jsonify({"error": f"Failed to read the CSV file: {str(e)}"}), 500
    try:
        for process in list_of_process:
            logger.info(f"Processing SKU: {process['sku_id']} with process: {process['process_id']}")
            sku_id = process['sku_id']
            process_id = process['process_id']

    # Construct the folder paths based on seller ID and SKU ID
            base_folder = f"./assets/batch_process_output/{seller_id}/{sku_id}/raw"

            # Look for video files in the raw folder
            video_file_paths = [
                os.path.join(base_folder, file_name)
                for file_name in os.listdir(base_folder)
                if file_name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv'))
            ][:10]  # Limit to 10 video files
            if process_id=='lifestyle_shot': 
                try: 
                    image=LS.lifestyle_shots(seller_id,sku_id)
                    return jsonify({"message": "Lifestyle shots processed successfully"}), 200
                except Exception as e:
                    logger.error(f"Error processing lifestyle shots for SKU {sku_id}: {str(e)}")
                    continue
            elif process_id == "3D360":
                if not video_file_paths:
                    return jsonify({"error": "No video files found in the raw folder"}), 400

                # Process the videos and generate P3D
                try:
                    # Create the output folder for processed images and P3D
                    processed_folder = os.path.join(f"./assets/batch_process_output/{seller_id}/{sku_id}/processed")
                    os.makedirs(processed_folder, exist_ok=True)

                    processed_images = []
                    
                    # Process each video file, passing seller_id and sku_id
                    for video_file_path in video_file_paths:
                        video_processed_images = process_video(video_file_path, processed_folder, seller_id, sku_id)
                        processed_images.extend(video_processed_images)

                    # Create P3D file in the processed folder
                    create_p3d_file(processed_images, processed_folder, seller_id, sku_id)

                    # Generate S3 file URL
                    s3_file_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION_NAME}.amazonaws.com/{seller_id}/{sku_id}/{sku_id}.p3d"

                    return jsonify({"message": "Videos processed and P3D file stored successfully.", "s3_url": s3_file_url}), 200
                except Exception as e:
                    return jsonify({"error": str(e)}), 500
                
            elif process_id == "bg_elimination":
                # Look for image files in the raw folder
                image_file_paths = [
                    os.path.join(base_folder, f) for f in os.listdir(base_folder)
                    if any(f.lower() == f"{sku_id}_raw_{i}.{ext}" for i in range(1, 5) for ext in ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff'])
                    ]

                if not image_file_paths:
                    return jsonify({"error": "No image files found in the raw folder for background elimination."}), 400

                # Create the output folder for processed images
                processed_folder = os.path.join(f"./assets/batch_process_output/{seller_id}/{sku_id}/processed/bg_eliminated")
                os.makedirs(processed_folder, exist_ok=True)

                image_counter = 1

                # Process each image file
                processed_images = []
                
                s3_urls = []

                for image_path in image_file_paths:
                    try:
                        
                        image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
                        if image is None:
                            print(f"Error: Failed to read image at {image_path}. Skipping.")
                            continue

                        # Prepare frame for OpenVINO
                        input_image = cv2.resize(image, (model_input_size[1], model_input_size[0]))
                        input_image = input_image.transpose(2, 0, 1)
                        input_image = np.expand_dims(input_image, axis=0).astype(np.float32) / 255.0

                        # Perform inference
                        result = ov_compiled_model(input_image)[0]

                        # Generate binary mask
                        mask = result[0] > 0.5
                        mask = mask.astype(np.uint8) * 255
                        mask = np.squeeze(mask)
                        mask_resized = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)

                        # Optional: Morphological operations to improve mask
                        kernel = np.ones((5, 5), np.uint8)
                        mask_resized = cv2.morphologyEx(mask_resized, cv2.MORPH_CLOSE, kernel)

                        # Create output image with background removed
                        no_bg_image = cv2.bitwise_and(image, image, mask=mask_resized)
                        no_bg_image = cv2.cvtColor(no_bg_image, cv2.COLOR_BGR2BGRA)
                        no_bg_image[:, :, 3] = mask_resized

                        # Add a white background to the background-eliminated image
                        white_bg_image = add_white_background(no_bg_image)
                        white_bg_image = cv2.cvtColor(white_bg_image, cv2.COLOR_BGR2BGRA)

                        # Apply center alignment
                        centered_image = center_align_subject(white_bg_image)

                        # Save the image
                        output_filename = f"{seller_id}_{sku_id}_{image_counter}.png"
                        output_path = os.path.join(processed_folder, output_filename)
                        cv2.imwrite(output_path, centered_image)

                        # Upload processed image to S3
                        s3_key = f"python_processed_outputs/bg_eliminated/{output_filename}"
                        s3_url = upload_to_s3(output_path, s3_key)
                        s3_urls.append(s3_url)

                        connection = db.create_connection()
                        store_image_in_db(connection, s3_url, sku_id, image_counter)
                        db.close_connection(connection)

                        processed_images.append(output_path)
                        print(f"Processed image saved as {output_path}")

                        image_counter += 1

                    except Exception as e:
                        print(f"Unexpected error while processing image {image_path}: {e}")

                return jsonify({"message": "Background elimination completed successfully.", "processed_images": s3_urls}), 200

            elif process_id == "bg_elimination with bleed":
                # Look for image files in the raw folder
                image_file_paths = [
                    os.path.join(base_folder, f) for f in os.listdir(base_folder)
                    if any(f.lower() == f"{sku_id}_raw_{i}.{ext}" for i in range(1, 5) for ext in ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff'])
                ]

                if not image_file_paths:
                    return jsonify({"error": "No image files found in the raw folder for background elimination with bleed."}), 400

                # Create the output folder for processed images
                processed_folder = os.path.join(f"./assets/batch_process_output/{seller_id}/{sku_id}/processed/bg_eliminated_bleed")
                os.makedirs(processed_folder, exist_ok=True)

                image_counter = 1

                # Process each image file with bleed effect
                processed_images = []
                s3_urls = []
                for image_path in image_file_paths:
                    try:
                        image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
                        if image is None:
                            print(f"Error: Failed to read image at {image_path}. Skipping.")
                            continue

                        # Prepare frame for OpenVINO
                        input_image = cv2.resize(image, (model_input_size[1], model_input_size[0]))
                        input_image = input_image.transpose(2, 0, 1)
                        input_image = np.expand_dims(input_image, axis=0).astype(np.float32) / 255.0

                        # Perform inference
                        result = ov_compiled_model(input_image)[0]

                        # Generate binary mask
                        mask = result[0] > 0.5
                        mask = mask.astype(np.uint8) * 255
                        mask = np.squeeze(mask)
                        mask_resized = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)

                        # Optional: Morphological operations to improve mask
                        kernel = np.ones((5, 5), np.uint8)
                        mask_resized = cv2.morphologyEx(mask_resized, cv2.MORPH_CLOSE, kernel)

                        # Create output image with background removed
                        no_bg_image = cv2.bitwise_and(image, image, mask=mask_resized)
                        no_bg_image = cv2.cvtColor(no_bg_image, cv2.COLOR_BGR2BGRA)
                        no_bg_image[:, :, 3] = mask_resized

                        # Add a white background to the background-eliminated image
                        white_bg_image = add_white_background(no_bg_image)
                        white_bg_image = cv2.cvtColor(white_bg_image, cv2.COLOR_BGR2BGRA)

                        # Apply bleed effect and center alignment
                        bleeded_image = apply_bleed_effect(white_bg_image)
                        centered_image = center_align_subject(bleeded_image)

                        # Save the image
                        output_filename = f"{seller_id}_{sku_id}_{image_counter}.png"
                        output_path = os.path.join(processed_folder, output_filename)
                        cv2.imwrite(output_path, centered_image)

                        # Upload processed image to S3
                        s3_key = f"python_processed_outputs/bg_eliminated_bleed/{output_filename}"
                        s3_url = upload_to_s3(output_path, s3_key)
                        s3_urls.append(s3_url)

                        connection = db.create_connection()
                        store_image_in_db(connection, s3_url, sku_id, image_counter)
                        db.close_connection(connection)

                        processed_images.append(output_path)
                        print(f"Processed image saved as {output_path}")

                        image_counter += 1

                    except Exception as e:
                        print(f"Unexpected error while processing image {image_path}: {e}")

                return jsonify({"message": "Background elimination with bleed completed successfully.", "processed_images": s3_urls}), 200

            else:
                return jsonify({"error": "Unsupported process_id"}), 400    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "Process completed successfully"}), 200
def process_video(video_path, save_directory, seller_id, sku_id):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open video file")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        cap.release()
        raise ValueError("Could not determine the FPS of the video")

    processed_images = []  # List to hold paths of processed images
    file_counter = len(os.listdir(save_directory)) + 1  # Start from existing files

    # Generate 36 frames for the video
    for j in range(36):
        try:
            frame_position = int((j / 36) * cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
            ret, frame = cap.read()

            if not ret or frame is None:
                print(f"Error: Failed to read frame at position {frame_position}. Skipping.")
                continue

            # Prepare frame for OpenVINO
            input_image = cv2.resize(frame, (model_input_size[1], model_input_size[0]))
            input_image = input_image.transpose(2, 0, 1)
            input_image = np.expand_dims(input_image, axis=0).astype(np.float32) / 255.0

            # Perform inference
            result = ov_compiled_model(input_image)[0]

            # Generate binary mask
            mask = result[0] > 0.5
            mask = mask.astype(np.uint8) * 255
            mask = np.squeeze(mask)
            mask_resized = cv2.resize(mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)

            # Optional: Morphological operations to improve mask
            kernel = np.ones((5, 5), np.uint8)
            mask_resized = cv2.morphologyEx(mask_resized, cv2.MORPH_CLOSE, kernel)

            # Create output image with background removed
            no_bg_image = cv2.bitwise_and(frame, frame, mask=mask_resized)
            no_bg_image = cv2.cvtColor(no_bg_image, cv2.COLOR_BGR2BGRA)
            no_bg_image[:, :, 3] = mask_resized

            # Apply bleed effect and center alignment
            # bleeded_image = apply_bleed_effect(no_bg_image)
            centered_image = center_align_subject(no_bg_image)

            # Save the image
            output_filename = f"image_f{file_counter}.png"
            output_path = os.path.join(save_directory, output_filename)
            cv2.imwrite(output_path, centered_image)

            processed_images.append(output_path)
            print(f"Frame {file_counter} processed: Background removed and saved as {output_path}")
            file_counter += 1

        except Exception as e:
            print(f"Unexpected error while processing frame {file_counter}: {e}")

    cap.release()
    print("Frame extraction completed.")
    for img_path in processed_images:
        try:
            output_filename = os.path.basename(img_path)
            s3_key = f"3d360/{seller_id}/{sku_id}/{output_filename}"
            upload_to_s3(img_path, s3_key)
            print(f"Uploaded {img_path} to S3.")
        except Exception as e:
            print(f"Failed to upload {img_path} to S3: {e}")

    return processed_images

def create_p3d_file(processed_images, save_directory, seller_id, sku_id):
    p3d_file = os.path.join(save_directory, f"{sku_id}.p3d")
    with zipfile.ZipFile(p3d_file, 'w') as zipf:
        for img_path in processed_images:
            img_filename = os.path.basename(img_path)
            zipf.write(img_path, img_filename)

    # Upload the P3D file to S3 in the appropriate folder
    s3_key = f"3d360/{seller_id}/{sku_id}/{sku_id}.p3d"
    upload_to_s3(p3d_file, s3_key)

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
        s3_client.upload_file(file_path, "igo-media-dev", s3_key)
        print(f"File {file_path} uploaded to S3 as {s3_key}.")

        s3_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION_NAME}.amazonaws.com/{s3_key}"
        return s3_url
    
    except Exception as e:
        print(f"Failed to upload {file_path} to S3: {e}")


ALLOWED_EXTENSIONS = {'csv'}  # Only allow CSV file uploads for SKU information

# S3 configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION_NAME = os.getenv("AWS_DEFAULT_REGION")
S3_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
S3_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Load the OpenVINO model
model_input_size = [1024, 1024]
ov_model_path = Path("models/rmbg-1.4.xml")

# Load the segmentation model
net = AutoModelForImageSegmentation.from_pretrained("briaai/RMBG-1.4", trust_remote_code=True)

if not ov_model_path.exists():
    # Convert the model and save it
    example_input = np.zeros((1, 3, *model_input_size), dtype=np.uint8)
    ov_model = ov.convert_model(net, example_input, input=[1, 3, *model_input_size])
    ov.save_model(ov_model, ov_model_path)

core = ov.Core()
device = "AUTO"
ov_compiled_model = core.compile_model(ov_model_path, device)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def apply_bleed_effect(image_np):
    """Apply a bleed effect to the image."""
    x_scale = 20
    y_scale = 20
    alpha_channel = image_np[:, :, 3]
    kernel_size_x = max(1, x_scale)
    kernel_size_y = max(1, y_scale)
    kernel = np.ones((kernel_size_y, kernel_size_x), np.uint8)

    adjusted_mask = cv2.dilate(alpha_channel, kernel, iterations=1)
    bleeded_image = image_np.copy()
    bleeded_image[:, :, 3] = adjusted_mask
    return bleeded_image

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