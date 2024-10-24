from io import BytesIO  
from . import make_api_request
from app import logger
REPLACE_BACKGROUND_API_URL = "https://i8zbn250bb.execute-api.us-east-1.amazonaws.com/dev/image-replace"

def replace_background(image_bytes:BytesIO, prompt: str) -> BytesIO:
    """
    Replaces the background of an image based on a text prompt using an external API.
    """
    logger.info(f"Replacing background of image with prompt: {prompt}")
    try:
        image_bytes.seek(0) 
        logger.info(f"Image bytes seeked to 0")
        files = {
            'file':  ('centered_image.png', image_bytes, 'image/png')
        }
        logger.info(f"Files: {files}")
        data = {'outpaint_prompt': prompt}
        logger.info(f"Data: {data}")

        response = make_api_request('post', REPLACE_BACKGROUND_API_URL, files=files, data=data, timeout=100)
        logger.info(f"Response: {response}")
        return BytesIO(response.content)
    except Exception as e:
        raise Exception(f"Error replacing background of image: {e}") from e
