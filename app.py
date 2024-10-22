from config.flask import create_app
from dotenv import load_dotenv
from flask import render_template, jsonify, request
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


load_dotenv()

app, celery ,logger = create_app()

from routes import api_v1
app.register_blueprint(api_v1, url_prefix='/api/v1')

@app.route('/')
def index():
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
        data = pd.read_csv(csv_path)
        if 'sku_id' not in data.columns or 'process_id' not in data.columns:
            return jsonify({"error": "CSV file must contain 'sku_id' and 'process_id' columns"}), 400

        sku_id = data['sku_id'].iloc[0]
        process_id = data['process_id'].iloc[0]  # Get the process_id from the CSV
    except Exception as e:
        return jsonify({"error": f"Failed to read the CSV file: {str(e)}"}), 500

    # Construct the folder paths based on seller ID and SKU ID
    base_folder = f"./assets/3d360/{seller_id}/{sku_id}/raw"

    # Look for video files in the raw folder
    video_file_paths = [
        os.path.join(base_folder, file_name)
        for file_name in os.listdir(base_folder)
        if file_name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv'))
    ][:10]  # Limit to 10 video files

    if process_id == "3D360":
        if not video_file_paths:
            return jsonify({"error": "No video files found in the raw folder"}), 400

        # Process the videos and generate P3D
        try:
            # Create the output folder for processed images and P3D
            processed_folder = os.path.join(f"./assets/3d360/{seller_id}/{sku_id}/processed")
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
        image_file_paths = [os.path.join(base_folder, f) for f in os.listdir(base_folder)
                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'))]

        if not image_file_paths:
            return jsonify({"error": "No image files found in the raw folder for background elimination."}), 400

        # Create the output folder for processed images
        processed_folder = os.path.join(f"./assets/3d360/{seller_id}/{sku_id}/processed")
        os.makedirs(processed_folder, exist_ok=True)

        # Process each image file
        processed_images = []
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

                # Apply center alignment
                centered_image = center_align_subject(no_bg_image)

                # Save the image
                output_filename = os.path.basename(image_path)
                output_path = os.path.join(processed_folder, output_filename)
                cv2.imwrite(output_path, centered_image)

                processed_images.append(output_path)
                print(f"Processed image saved as {output_path}")

            except Exception as e:
                print(f"Unexpected error while processing image {image_path}: {e}")

        return jsonify({"message": "Background elimination completed successfully.", "processed_images": processed_images}), 200

    elif process_id == "bg_elimination with bleed":
        # Look for image files in the raw folder
        image_file_paths = [os.path.join(base_folder, f) for f in os.listdir(base_folder)
                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.jfif'))]

        if not image_file_paths:
            return jsonify({"error": "No image files found in the raw folder for background elimination with bleed."}), 400

        # Create the output folder for processed images
        processed_folder = os.path.join(f"./assets/3d360/{seller_id}/{sku_id}/processed")
        os.makedirs(processed_folder, exist_ok=True)

        # Process each image file with bleed effect
        processed_images = []
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

                # Apply bleed effect and center alignment
                bleeded_image = apply_bleed_effect(no_bg_image)
                centered_image = center_align_subject(bleeded_image)

                # Save the image
                output_filename = os.path.basename(image_path)
                output_path = os.path.join(processed_folder, output_filename)
                cv2.imwrite(output_path, centered_image)

                processed_images.append(output_path)
                print(f"Processed image saved as {output_path}")

            except Exception as e:
                print(f"Unexpected error while processing image {image_path}: {e}")

        return jsonify({"message": "Background elimination with bleed completed successfully.", "processed_images": processed_images}), 200

    else:
        return jsonify({"error": "Unsupported process_id"}), 400    

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
        region_name="us-east-1",
        aws_access_key_id="AKIAQLSIVUGCCDXXZXFC",
        aws_secret_access_key="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"
    )

    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = "application/octet-stream"

    try:
        # Upload the file to the S3 bucket
        s3_client.upload_file(file_path, "igo-media-dev", s3_key)
        print(f"File {file_path} uploaded to S3 as {s3_key}.")
    except Exception as e:
        print(f"Failed to upload {file_path} to S3: {e}")


ALLOWED_EXTENSIONS = {'csv'}  # Only allow CSV file uploads for SKU information

# S3 configuration
S3_BUCKET_NAME = 'your-s3-bucket-name'
S3_REGION_NAME = 'your-region-name'  
S3_ACCESS_KEY = 'your-access-key'
S3_SECRET_KEY = 'your-secret-key'

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