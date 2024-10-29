import os
import cv2
import numpy as np
from utils import db
from .utils import center_align_subject,add_white_background,store_image_in_db,MODEL_INPUT_SIZE,setup_openvino_model,upload_to_s3

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION_NAME = os.getenv("AWS_DEFAULT_REGION")
ALLOWED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']

def bg_elimination_bleed(seller_id, sku_id):
    ov_compiled_model =setup_openvino_model()
    base_folder = f"./assets/batch_process_output/{seller_id}/{sku_id}/raw"
    image_file_paths = [
        os.path.join(base_folder, file) for file in os.listdir(base_folder) if os.path.splitext(file)[1].lower() in ALLOWED_EXTENSIONS
    ]

    if not image_file_paths:
        raise ValueError("No image files found in the raw folder for background elimination with bleed.")

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
            input_image = cv2.resize(image, (MODEL_INPUT_SIZE[1], MODEL_INPUT_SIZE[0]))
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

    return s3_urls


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