from PIL import Image
from io import BytesIO

import utils.image
from . import make_api_request
import utils
BACKGROUND_REMOVAL_API_URL = "https://o7x1m9cc6g.execute-api.us-east-1.amazonaws.com/dev/remove-background"

def remove_background(image_file:bytes) -> BytesIO:
    """
    Removes the background from an image using an external API.
    """
    try:
        image_file = BytesIO(image_file)
        image_file.seek(0)
        with Image.open(image_file) as img:
            width, height = img.size
            if width >1400 or height >1400:
                image_file=utils.image.resize_image(img)
            else:
                image_file.seek(0)
        files = {'image': image_file}
        response = make_api_request('post', BACKGROUND_REMOVAL_API_URL, files=files, timeout=30)
        return BytesIO(response.content)
    except Exception as e:
        raise Exception(f"Error removing background from image: {e}") from e
