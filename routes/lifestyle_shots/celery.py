from utils.aws import s3
from utils import external_api as EX_API,image as IMG
from app import celery
from .lifestyle_shots import *

@celery.task(bind=True, max_retries=3, default_retry_delay=300)
def process_image_task(self, file_id, file_name, bucket_name):
    try:
        data = get_data_from_db(file_name)
        lifestyle_prompt = generate_prompt(data)
        image_with_no_bg = remove_background(file_id)
        centered_image = IMG.create_canvas_with_bleed(image_with_no_bg)
        lifestyle_image = EX_API.replace_background(centered_image, lifestyle_prompt)
        s3_url = s3.upload_to_s3(lifestyle_image, bucket_name, file_name)
        if not s3_url:
            raise ValueError("Failed to upload processed image to S3")
        return {'file_name': file_name, 's3_url': s3_url}

    except Exception as e:
        # Retry the task in case of an exception
        self.retry(exc=e)
        return {'error': str(e), 'file_name': file_name}
    
