import os
import cv2
import zipfile
import numpy as np
import openvino as ov
from pathlib import Path
from .utils import center_align_subject,MODEL_INPUT_SIZE,setup_openvino_model,upload_to_s3
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION_NAME = os.getenv("AWS_DEFAULT_REGION")
ALLOWED_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']

def get3D360(seller_id, sku_id):
    base_folder = f"./assets/batch_process_output/{seller_id}/{sku_id}/raw"
    
    video_file_paths=[
        os.path.join(base_folder, file) for file in os.listdir(base_folder) if os.path.splitext(file)[1].lower() in ALLOWED_EXTENSIONS
    ]
    if not video_file_paths:
        raise "No video files found in the raw folder"

    processed_folder = os.path.join(f"./assets/batch_process_output/{seller_id}/{sku_id}/processed")
    os.makedirs(processed_folder, exist_ok=True)

    processed_images = []
    
    for video_file_path in video_file_paths:
        video_processed_images = process_video(video_file_path, processed_folder, seller_id, sku_id)
        processed_images.extend(video_processed_images)

    create_p3d_file(processed_images, processed_folder, seller_id, sku_id)

    s3_file_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION_NAME}.amazonaws.com/{seller_id}/{sku_id}/{sku_id}.p3d"
    return s3_file_url

def process_video(video_path, save_directory, seller_id, sku_id):
    ov_compiled_model=setup_openvino_model()
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
            input_image = cv2.resize(frame, (MODEL_INPUT_SIZE[1], MODEL_INPUT_SIZE[0]))
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

