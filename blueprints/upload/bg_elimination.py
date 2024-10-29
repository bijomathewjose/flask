import os
import cv2
import numpy as np
from utils import db
from utils import directory as DIR
from .utils import center_align_subject, add_white_background, setup_openvino_model, MODEL_INPUT_SIZE, get_raw_images,upload_to_s3
import logging

logger = logging.getLogger(__name__)
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION_NAME = os.getenv("AWS_DEFAULT_REGION")
ALLOWED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']

def bg_elimination(seller_id, sku_id):
    try:
        logger.info("Setting up OpenVINO model.")
        ov_compiled_model = setup_openvino_model()
    except Exception as e:
        logger.error(f"Error setting up OpenVINO model: {e}")
        raise ValueError(f"Error setting up OpenVINO model: {e}")
    
    base_folder = f"assets/batch_process_output/{seller_id}/{sku_id}/raw"
    if not DIR.check_folder_exists(base_folder):
        logger.error(f"Folder '{base_folder}' does not exist.")
        raise ValueError(f"Folder '{base_folder}' does not exist.")
    else:
        logger.info(f"Folder '{base_folder}' exists.")
    
    image_file_paths = get_raw_images(sku_id, base_folder, ALLOWED_EXTENSIONS)
    image_file_paths = [f"assets/batch_process_output/{seller_id}/{sku_id}/raw/{image_file_path}"  for image_file_path in image_file_paths ]
    logger.info(f"Found {len(image_file_paths)} images for processing.")

    if len(image_file_paths) <= 0:
        logger.error("No image files found in the raw folder for background elimination.")
        raise ValueError("No image files found in the raw folder for background elimination.")

    processed_folder = os.path.join(f"assets/batch_process_output/{seller_id}/{sku_id}/processed/bg_eliminated")
    os.makedirs(processed_folder, exist_ok=True)
    logger.info(f"Created processed images folder at {processed_folder}.")

    image_counter = 1
    processed_images = []
    s3_urls = []

    for image_path in image_file_paths:
        try:
            logger.info(f"Processing image: {image_path}")
            image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if image is None:
                logger.warning(f"Failed to read image at {image_path}. Skipping.")
                continue

            input_image = cv2.resize(image, (MODEL_INPUT_SIZE[1], MODEL_INPUT_SIZE[0]))
            input_image = input_image.transpose(2, 0, 1)
            input_image = np.expand_dims(input_image, axis=0).astype(np.float32) / 255.0

            result = ov_compiled_model(input_image)[0]

            mask = result[0] > 0.5
            mask = mask.astype(np.uint8) * 255
            mask = np.squeeze(mask)
            mask_resized = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)

            kernel = np.ones((5, 5), np.uint8)
            mask_resized = cv2.morphologyEx(mask_resized, cv2.MORPH_CLOSE, kernel)

            no_bg_image = cv2.bitwise_and(image, image, mask=mask_resized)
            no_bg_image = cv2.cvtColor(no_bg_image, cv2.COLOR_BGR2BGRA)
            no_bg_image[:, :, 3] = mask_resized

            white_bg_image = add_white_background(no_bg_image)
            white_bg_image = cv2.cvtColor(white_bg_image, cv2.COLOR_BGR2BGRA)

            centered_image = center_align_subject(white_bg_image)

            output_filename = f"{seller_id}_{sku_id}_{image_counter}.png"
            output_path = os.path.join(processed_folder, output_filename)
            cv2.imwrite(output_path, centered_image)
            logger.info(f"Processed image saved as {output_path}")

            s3_key = f"python_processed_outputs/bg_eliminated/{output_filename}"
            s3_url = upload_to_s3(output_path, s3_key)
            s3_urls.append(s3_url)
            logger.info(f"Uploaded image to S3: {s3_url}")

            connection = db.create_connection()
            store_image_in_db(connection, s3_url, sku_id, image_counter)
            db.close_connection(connection)
            logger.info(f"Stored image URL in database for SKU: {sku_id}, Image Index: {image_counter}")

            processed_images.append(output_path)
        except Exception as e:
            logger.error(f"Unexpected error while processing image {image_path}: {e}")
        finally:
            image_counter += 1
    return s3_urls

def store_image_in_db(connection, s3_url, sku_id, index):
    field_name = f"img_{index}"
    query = f"UPDATE all_platform_products SET {field_name} = %s WHERE sku = %s"
    params = [s3_url, sku_id]
    db.execute_query(connection, query, params)
    logger.info(f"Updated database with image URL: {s3_url} for SKU: {sku_id}, Field: {field_name}")
