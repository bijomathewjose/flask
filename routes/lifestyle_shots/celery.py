from utils.aws import s3
from utils import external_api as EX_API,image as IMG,Gen_AI
from app import celery,logger
from utils import db
from utils.image import remove_background
def get_data_from_db(connection, sku):
    query = f"SELECT text_dump FROM all_platform_products WHERE sku = '{sku}'"
    data = db.fetch_data(connection, query)
    if not data or data[0]['text_dump'] is None:
        raise ValueError("No data found for the given SKU or text_dump is empty")
    return data[0]['text_dump']

def store_image_in_db(connection, s3_url, sku_id, index):
    field_name = f"img_{index+5}"
    query = f"UPDATE all_platform_products SET {field_name} = %s WHERE sku = %s"
    params = [s3_url, sku_id]  # Pass as tuple
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
    return prompt_text



@celery.task(bind=True, max_retries=3, default_retry_delay=300)
def process_image_task(self, file, filename, bucket_name,sku_id,index,filepath):
    try:
        logger.info(f"Processing image: {filename}, SKU: {sku_id}, Index: {index}")
        connection = db.create_connection()
        data = get_data_from_db(connection,sku_id)
        lifestyle_prompt = generate_prompt(data)
        image_with_no_bg = remove_background(filepath)
        centered_image = IMG.create_canvas_with_bleed(image_with_no_bg)
        lifestyle_image = EX_API.replace_background(centered_image, lifestyle_prompt)
        s3_url = s3.upload_to_s3(lifestyle_image, bucket_name, filename)
        store_image_in_db(connection,s3_url,sku_id,index)
        db.close_connection(connection)
        if not s3_url:
            raise ValueError("Failed to upload processed image to S3")
        return {'filename': filename, 's3_url': s3_url}
    except Exception as e:
        # Retry the task in case of an exception
        self.retry(exc=e)
        return {'error': str(e), 'filename': filename}
    
