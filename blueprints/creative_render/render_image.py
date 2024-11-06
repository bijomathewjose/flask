import re
from typing import List, Dict, Any, Union

import requests
from io import BytesIO
from PIL import Image, ImageDraw,ImageFont
import os
from flask import json, jsonify
from utils.Gen_AI import generate_prompt


def image_insertion(image_data: Dict[str, Any], background: Image, count:int=0):
    if image_data['url'] is None:
        count+=1
        return count
    response = requests.get(image_data['url'])
    if response.status_code != 200:
        return count
    with Image.open(BytesIO(response.content)) as img:
        img = img.convert("RGBA")
        img = img.rotate(int(image_data["angle"]), expand=True)
        o_wid, o_hei = img.size
        o_ratio = min(int(image_data["width"]) / o_wid, int(image_data["height"]) / o_hei)
        # with aspect ratio resizing
        # img = img.resize((int(o_wid * o_ratio), int(o_hei * o_ratio)), Image.Resampling.LANCZOS)
        # without aspect ratio resizing
        img=img.resize((int(image_data["width"]), int(image_data["height"])), Image.Resampling.LANCZOS)
        background.paste(img, (int(image_data["x"]), int(image_data["y"])), img)
        count+=1 
    return count

def text_insertion(prev:int,line_number:int,line:Dict[str,Any],text_data: Dict[str, Any],draw:ImageDraw):
    font = ImageFont.load_default()
    text=text_data['type']
    text_width, text_height = draw.textsize(text, font=font)
    x_axis=int(text_data['x'])
    y_axis=int(text_data['y'])
    text_position = (x_axis-text_width//2, y_axis-text_height//2)
    draw.text(text_position, text, font=font, fill="black")
    return prev,line_number

def setup_background(template_data: List[Dict[str, Any]],width:int=2000,height:int=2000):
    if not os.path.exists('./assets/bg.png'):
        return jsonify({'error':'Background image not found'}), 500
    with Image.open('./assets/bg.png') as background:
        background = background.convert("RGBA")
        original_width, original_height = background.size
        ratio = min(width / original_width, height / original_height)
        width = int(original_width * ratio)
        height = int(original_height * ratio)    
        background = background.resize((width, height), Image.Resampling.LANCZOS)
    return background

def render_to_image(template_data: List[Dict[str, Any]],width:int=1000,height:int=1000,db_data: Dict[str, Any]=None):
    # Load the background image
    background = setup_background(template_data,width,height)
    if background is None:
        raise Exception('Background image not found')
    draw = ImageDraw.Draw(background)
    # Render images
    count=0
    template=template_data[0]
    for image_data in template["images"]:
        if count>=4:
            break
        count=image_insertion(image_data,background,count)
    prompt_1=f"""
        Given the following inputs:
        - Product data: {db_data}
        - This the template data: {template['text_list']} for this one
        Task:
        1. Add appropriate values for each line in text data lines
        2. Focus on the most important product features/benefits
        3. Ensure the text is relevant and informative based on template data received
        4. Ensure the text data is varied and unique not repeating
        5. Provide the text data in JSON format with additional field in each line as 'text_value' which is the value of the text to filled in image template

        Output requirements:
        - Return the text data in JSON format with additional field in each line as 'text_value' which is the value of the text to filled in image template
        - No additional explanations or metadata
        - Must be complete sentences
        - Must be within the number provide in 'chars' in each line  characters
        - limit the text_value to the number value provided in 'chars' in each line
        - Ensure the text data is varied and unique not repeating
        
    """
    template=generate_prompt(prompt_1)
    cleaned_data = template.strip("```json").strip("```").strip()
    
    template=json.loads(cleaned_data)
    # Render text
    for text_data in template:
        x_axis=int(text_data['x'])
        y_axis=int(text_data['y'])
        characters_per_line=[line['char'] for line in text_data['lines']['data']]
        lines = []
        line_spacing = 20
        start=0

        for i,limit in enumerate(characters_per_line):
            limit=int(limit)
            value=text_data['lines']['data'][i]['text_value']
            value = re.sub(r'[^A-Za-z0-9 _-]', '', value)
            lines.append(value)
            start += limit
        for i, line in enumerate(lines):
            
            font_name=text_data['lines']['data'][i]['font']
            font_path=f'./static/fonts/{font_name}'
            
            font_size=float(text_data['lines']['data'][i]['font_size'])
            font_size=round(font_size*4.235)
            font = load_font(font_path, font_size)
            align=text_data['lines']['data'][i]['align']
            font_color=text_data['lines']['data'][i]['font_color']
            bbox = draw.textbbox((0, 0), line, font=font,font_size=font_size)
            text_height = bbox[3] - bbox[1]
            line_y = y_axis + i * (text_height + line_spacing)
            # Draw text
            if (align == 'center' or align == 'centre'):
                centreOffset = bbox[2] // 2
                draw.text((x_axis+centreOffset, line_y), line, fill=font_color, font=font, anchor="rt", align="right")
            elif (align == "right"):
                draw.text((x_axis+int(width), line_y), line, fill=font_color, font=font, anchor="rt", align="right")
            else:
                draw.text((x_axis, line_y), line, font_color, font=font, align="left")
    # Save to in-memory file
    img_byte_arr = BytesIO()
    background.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return img_byte_arr

import os
from PIL import ImageFont

def load_font(font_path, font_size=20):
    # Check if the font file exists
    if not os.path.exists(font_path):
        print(f"Error: Font file '{font_path}' does not exist.")
        return ImageFont.load_default()  # Use default font as a fallback
    else:
        print(f"Font file '{font_path}' exists.")
    # Check if the font file is accessible
    if not os.access(font_path, os.R_OK):
        print(f"Error: Font file '{font_path}' is not accessible.")
        return ImageFont.load_default()  # Use default font as a fallback
    else:
        print(f"Font file '{font_path}' is accessible.")
    try:
        # Attempt to load the specified font
        font = ImageFont.truetype(font_path, size=font_size)
        return font
    except OSError:
        print(f"Error: Could not load font '{font_path}'. Using default font.")
        return ImageFont.load_default()  # Fallback in case of any other error

import json
import re
import ast
from typing import Union, Dict, Any

def clean_input_data(data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(data, dict):
        return data
    
    # If data is a string, try parsing it as JSON
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("Invalid input format. Please provide a valid JSON string or dictionary.")
    
    # Raise an error if the input is neither a string nor dictionary
    raise ValueError("Input must be a JSON string or a dictionary.")
