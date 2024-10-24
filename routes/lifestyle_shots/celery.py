from utils.aws import s3
from utils import external_api as EX_API,image as IMG,Gen_AI
from app import logger
from utils import db
import cv2
import os
from PIL import Image
import numpy as np


def get_data_from_db(connection, sku):
    query = f"SELECT text_dump FROM all_platform_products WHERE sku = '{sku}'"
    data = db.fetch_data(connection, query)
    if not data or data[0]['text_dump'] is None:
        raise ValueError("No data found for the given SKU or text_dump is empty")
    return data[0]['text_dump']

def store_image_in_db(connection, s3_url, sku_id, index):
    field_name = f"img_{index+5}"
    logger.info(f"Storing image in db: {field_name} = {s3_url}")
    query = f"UPDATE all_platform_products SET {field_name} = %s WHERE sku = %s"
    logger.info(f"Query: {query}")
    params = [s3_url, sku_id]  # Pass as tuple
    logger.info(f"Params: {params}")
    db.execute_query(connection, query, params)
    

def generate_prompt(data):
    prompt_text = (
            f"This is the product information : {data}\n\n"
            f"Based on provided data for this image\n\n"
            "Generate prompt for creating a lifestyle shot background suitable for the product.\n\n"
            "Follow AUP or AWS Responsible AI Policy to generate the background."
            "Prompt should be within 500 characters and should not be greater."
    )
    prompt_text = Gen_AI.generate_prompt(prompt_text)
    logger.info(f"Prompt text: {prompt_text}")
    return prompt_text


def processor(file, filename, bucket_name,sku_id,index,filepath,seller_id,processed_folder):
    try:
        logger.info(f"Processing image: {filename}, SKU: {sku_id}, Index: {index}")
        image_with_no_bg = EX_API.remove_background(file)

        logger.info('Image with no background')
        centered_image = IMG.create_canvas_with_bleed(image_with_no_bg)

        logger.info('centered Image')
        connection = db.create_connection()
        data = get_data_from_db(connection,sku_id)
        logger.info(f"Data: {data}")
        lifestyle_prompt = generate_prompt(data)
        logger.info(f"Lifestyle prompt: {lifestyle_prompt}")
        lifestyle_image = EX_API.replace_background(centered_image, lifestyle_prompt)
        logger.info(f"Lifestyle image: {lifestyle_image}")
        lifestyle_image.seek(0)
    
        pil_image = Image.open(lifestyle_image)
        cv_image = np.array(pil_image)
        output_filename = f"{seller_id}_{sku_id}_{index}.jpg"
        output_path = os.path.join(processed_folder, output_filename)
        cv2.imwrite(output_path, cv_image)
        logger.info(f"Image saved at {output_path}")

        lifestyle_image.seek(0)
        s3_url = s3.upload_to_s3(lifestyle_image, filename,bucket_name,directory_name='lifestyle_shots')
        store_image_in_db(connection,s3_url,sku_id,index)
        db.close_connection(connection)
        if not s3_url:
            logger.info("Failed to upload processed image to S3")
            return None
        return s3_url
    except Exception as e:
        logger.error(f"Error: {e}")
        # Retry the task in case of an exception
        return {'error': str(e), 'filename': filename}
    
# @celery.task(bind=True, max_retries=3, default_retry_delay=300)
# def process_image_task(self, file, filename, bucket_name,sku_id,index,filepath):
#     try:
#         logger.info(f"Processing image: {filename}, SKU: {sku_id}, Index: {index}")
#         image_with_no_bg = remove_background(filepath)
#         centered_image = IMG.create_canvas_with_bleed(image_with_no_bg)
#         connection = db.create_connection()
#         data = get_data_from_db(connection,sku_id)
#         lifestyle_image = EX_API.replace_background(centered_image, lifestyle_prompt)
#         s3_url = s3.upload_to_s3(lifestyle_image, bucket_name, filename)
#         store_image_in_db(connection,s3_url,sku_id,index)
#         lifestyle_prompt = generate_prompt(data)
#         db.close_connection(connection)
#         if not s3_url:
#             raise ValueError("Failed to upload processed image to S3")
#         return {'filename': filename, 's3_url': s3_url}
#     except Exception as e:
#         # Retry the task in case of an exception
#         self.retry(exc=e)
#         return {'error': str(e), 'filename': filename}
    
