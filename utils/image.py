from PIL import Image, ImageOps, ImageFile
from io import BytesIO

def create_canvas_with_bleed(image_stream: BytesIO, canvas_size: int=800, bleed: int=20) -> BytesIO:
    try:
        image_stream.seek(0)
        with Image.open(image_stream) as img:
            if img.mode != "RGBA":
                raise ValueError("The image does not have an alpha channel.")
            
            bbox = img.getbbox()
            if bbox is None:
                raise ValueError("No visible subject found in the image.")
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