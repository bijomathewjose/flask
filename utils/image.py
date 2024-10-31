from PIL import Image, ImageOps, ImageFile
from io import BytesIO
from urllib.parse import urlparse
import requests
from werkzeug.datastructures import FileStorage

def create_canvas_with_bleed(image_stream: BytesIO, canvas_size: int=800, bleed: int=20) -> BytesIO:
    try:
        image_stream.seek(0)
        with Image.open(image_stream) as img:
            if img.mode != "RGBA":
                raise Exception("The image does not have an alpha channel.")
            
            bbox = img.getbbox()
            if bbox is None:
                raise Exception("No visible subject found in the image.")
            bleedless_canvas_size = canvas_size - 2 * bleed
            subject_img = img.crop(bbox)
            subject_img.thumbnail((bleedless_canvas_size, bleedless_canvas_size), Image.Resampling.LANCZOS)
            new_canvas_size= (subject_img.width if subject_img.width > subject_img.height else subject_img.height) + 2 * bleed 
            canvas = Image.new("RGB", (new_canvas_size, new_canvas_size), (255, 255, 255, 1))
            x_offset = (new_canvas_size - subject_img.width) // 2
            y_offset = (new_canvas_size - subject_img.height) // 2
        
            canvas.paste(subject_img, (x_offset, y_offset), subject_img)

            resized_canvas = canvas.resize((bleedless_canvas_size,bleedless_canvas_size), Image.Resampling.LANCZOS)

            if bleed > 0:
                canvas = ImageOps.expand(resized_canvas, border=bleed, fill=(255, 255, 255, 0))

            output = BytesIO()
            canvas.save(output, format="JPEG")
            output.seek(0)

            return output
    except Exception as e:
        print(f"Unexpected error occurred while creating a canvas with bleed : {e}")
        raise


def resize_image(img:ImageFile,size=(1400,1400)):
    format=img.format
    img.thumbnail(size, Image.Resampling.LANCZOS)
    output = BytesIO()
    img.save(output, format=format) 
    output.seek(0)
    return output

def download_image(image_url):
    parsed_url = urlparse(image_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("Invalid URL format.")
    response = requests.get(image_url, stream=True, timeout=10)
    response.raise_for_status()
    # Check if the Content-Type header indicates an image
    content_type = response.headers.get('Content-Type', '')
    if not content_type.startswith('image/'):
        raise ValueError("URL does not point to a valid image.")

    # Optionally, you can enforce specific image types (e.g., JPEG, PNG)
    allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    if content_type not in allowed_types:
        raise ValueError(f"Unsupported image type: {content_type}")

    # Read the image content into BytesIO
    image_stream = BytesIO(response.content)
    image_stream.seek(0)  # Ensure the stream's position is at the start

    # Extract the image filename from the URL or assign a default name
    filename = image_url.split('/')[-1] or 'downloaded_image'

    # Create a FileStorage object from the BytesIO stream
    image_file = FileStorage(stream=image_stream, filename=filename)

    return image_file