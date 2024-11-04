from typing import List, Dict, Any
import requests
from io import BytesIO
from PIL import Image, ImageDraw
import os
from flask import jsonify

def image_insertion(image_data: Dict[str, Any], background: Image, count:int=0):
    response = requests.get(image_data['url'])
    if response.status_code != 200:
        return count
    with Image.open(BytesIO(response.content)) as img:
        img = img.convert("RGBA")
        img = img.rotate(int(image_data["angle"]), expand=True)
        o_wid, o_hei = img.size
        o_ratio = min(int(image_data["width"]) / o_wid, int(image_data["height"]) / o_hei)
        img = img.resize((int(o_wid * o_ratio), int(o_hei * o_ratio)), Image.Resampling.LANCZOS)
        background.paste(img, (int(image_data["x"]), int(image_data["y"])), img)
        count+=1 
    return count

def text_insertion(prev:int,line_number:int,line:Dict[str,Any],text_data: Dict[str, Any],draw:ImageDraw):
    start=prev
    number_of_chars=int(line['char'])
    end= start+number_of_chars+1
    prev+=end
    data=(f"{text_data['number']}{text_data["type"]}")[start:end]
    text_position = (int(text_data["x"]), int(text_data["y"])+(line_number*int(line["font_size"])*2.5))
    draw.text(text_position,data, fill=line["font_color"], anchor="mm")
    line_number+=1
    return prev,line_number
    
def setup_background(template_data: List[Dict[str, Any]],width:int=1000,height:int=1000):
    if not os.path.exists('./assets/bg.jpg'):
        return jsonify({'error':'Background image not found'}), 500
    with Image.open('./assets/bg.jpg') as background:
        background = background.convert("RGBA")
        original_width, original_height = background.size
        ratio = min(width / original_width, height / original_height)
        width = int(original_width * ratio)
        height = int(original_height * ratio)    
        background = background.resize((width, height), Image.Resampling.LANCZOS)
    return background

def render_to_image(template_data: List[Dict[str, Any]],width:int=1000,height:int=1000):
    # Load the background image
    background = setup_background(template_data,width,height)
    if background is None:
        raise Exception('Background image not found')
    draw = ImageDraw.Draw(background)
    # Render images
    count=0
    for image_data in template_data[0]["images"]:
        if count>=4:
            break
        count=image_insertion(image_data,background,count)
    # Render text
    for text_data in template_data[0]["text_list"]:
        place_text(text_data,draw,text_data["type"])
        
        prev=0
        line_number=0
        for line in text_data["lines"]["data"]:
            prev,line_number=text_insertion(prev,line_number,line,text_data,draw)
    # Save to in-memory file
    img_byte_arr = BytesIO()
    background.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return img_byte_arr
