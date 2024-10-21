from io import BytesIO  
from . import make_api_request

REPLACE_BACKGROUND_API_URL = "https://i8zbn250bb.execute-api.us-east-1.amazonaws.com/dev/image-replace"

def replace_background(image_bytes:BytesIO, prompt: str) -> BytesIO:
    """
    Replaces the background of an image based on a text prompt using an external API.
    """
    try:
        image_bytes.seek(0) 
        files = {
            'file':  ('centered_image.jpeg', image_bytes, 'image/png')
        }
        data = {'outpaint_prompt': prompt}

        response = make_api_request('post', REPLACE_BACKGROUND_API_URL, files=files, data=data, timeout=100)
        return BytesIO(response.content)
    except Exception as e:
        raise Exception(f"Error replacing background of image: {e}") from e
