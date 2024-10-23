from PIL import Image, ImageOps, ImageFile
from io import BytesIO
import cv2
import numpy as np
from pathlib import Path
from transformers import AutoModelForImageSegmentation
import openvino as ov

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

model_input_size = [1024, 1024]
ov_model_path = Path("models/rmbg-1.4.xml")
net = AutoModelForImageSegmentation.from_pretrained("briaai/RMBG-1.4", trust_remote_code=True)
if not ov_model_path.exists():
    # Convert the model and save it
    example_input = np.zeros((1, 3, *model_input_size), dtype=np.uint8)
    ov_model = ov.convert_model(net, example_input, input=[1, 3, *model_input_size])
    ov.save_model(ov_model, ov_model_path)
core = ov.Core()
device = "AUTO"
ov_compiled_model = core.compile_model(ov_model_path, device)

def remove_background(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        print(f"Error: Failed to read image at {image_path}. Skipping.")
    # Prepare frame for OpenVINO
    input_image = cv2.resize(image, (model_input_size[1], model_input_size[0]))
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

    # Save the image
    cv2.imwrite("no_bg_image.png", no_bg_image)
    # convert to BytesIO
    output = BytesIO()
    cv2.imencode('.png', no_bg_image)[1].tofile(output)
    output.seek(0)
    return output
