from blueprints.creative_render.types import (AllProductType, ImageItem, TemplateData, TextItem,Masked_Images,VectorItem,Lifestyle_Shots)
from utils.Gen_AI.generate_prompt import generate_prompt, generate_svg
from PIL import Image,ImageDraw,ImageFont
from typing import Literal,List
from io import BytesIO
import requests
import random
import json
import os
import re
from blueprints.upload.lifestyle_shots import lifestyle_shots
import cairosvg
import math
class CreativeRender:
    def __init__(self,template:TemplateData,product_data:AllProductType,sku_id:str,template_number:int,demo:int):
        if template is None:
            raise Exception('Template not found')
        self.template=template  
        self.sku_id=sku_id
        self.template_number=template_number
        self.demo=demo
        if product_data is None:
            raise Exception('Product data not found')
        self.product_data=product_data
        path=f'./assets/templates/background/{self.template["background"]}'
        with Image.open(path) as img:
            rgba_background = img.convert("RGBA")
            resized_background=self.resize_image(rgba_background,1000,1000)
            self.background_image=resized_background
        if self.background_image is None:
            raise Exception('Background image not found')
    
    def get_background_image(self,path=None):
        img_byte_arr = BytesIO()
        self.background_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        self.background_image=None
        save_path=path if path is not None else f'./assets/creative_render/{self.sku_id}-{self.template_number}-{self.demo}.jpg'
        directory = os.path.dirname(save_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(save_path, 'wb') as file:
            file.write(img_byte_arr.getvalue())
        return img_byte_arr
    
    def insert_images(self):
        count=0
        masked_images:Masked_Images=['img_1','img_2','img_3','img_4']        
        lifestyle_shots:Lifestyle_Shots=['img_5','img_6','img_7','img_8']
        images=self.template.get('images',[])
        for image in images:
            if count>=4:
                break
            if image["type"]=='wb':
                self.add_white_background(image)
            elif image["type"]=='mask':
                index=random.randint(0,len(masked_images)-1)
                image_to_add=masked_images.pop(index)
                image['url']=self.product_data.get(image_to_add,None)
                self.add_masked_image(image)
            elif image["type"]=='ls':
                index=random.randint(0,len(lifestyle_shots)-1)
                image['url']=self.product_data.get(lifestyle_shots.pop(index),None)
                self.add_masked_image(image)
            count+=1

    def add_masked_image(self,image_data:ImageItem):
        bg_image=self.background_image
        if image_data['url'] is None:
            return
        response = requests.get(image_data['url'])
        if response.status_code != 200:
            return
        with Image.open(BytesIO(response.content)) as img:
            height,width=int(image_data["height"]),int(image_data["width"])
            x_axis,y_axis=int(image_data["x"]),int(image_data["y"])
            img = img.convert("RGBA")
            img = img.rotate(int(image_data["angle"]), expand=True)
            img=self.resize_image(img,width,height)
            bg_image.paste(img, (x_axis, y_axis), img)
    
    def add_white_background(self,data:ImageItem):
        bg_image=self.background_image
        width,height=int(data["width"]),int(data["height"])
        angle=int(data["angle"])
        x_axis,y_axis=int(data["x"]),int(data["y"])
        white_background = Image.new("RGBA", (width, height), (255, 255, 255))
        white_background = white_background.rotate(angle, expand=True)
        bg_image.paste(white_background, (x_axis, y_axis), white_background)
    
    def resize_image(self,img: Image,width:int,height:int,keep_ratio=True):
        if keep_ratio:
            original_width, original_height = img.size
            original_ratio = min(width / original_width, height / original_height)
            width=int(original_width * original_ratio)
            height=int(original_height * original_ratio)
        img=img.resize((width, height), Image.Resampling.LANCZOS) 
        return img 
    
    def insert_the_texts(self):
        raw_texts=self.template.get('text_list',[])
        if len(raw_texts)==0:
            return
        texts=self.insert_ai_generated_text(raw_texts)
        self.template["text_list"]=texts
        if len(texts)==0:
            return
        draw = ImageDraw.Draw(self.background_image)
        for text in texts:
            self.paste_lines(text,draw)
    
    def insert_ai_generated_text(self,texts:List[TextItem])-> List[TextItem]:
        prompt=f"""
        Given the following inputs:
        - Product data: {self.product_data}
        - This the template data of text: {texts} for this one
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
        - Should never exceed the number provided in 'chars' in each line
        - Always keep the text value in the 'text_value' field in each line within chars provided and that should be absolutely within
        - Do not go beyond the number provided in 'chars' in each line
        
        """
        json_data=generate_prompt(prompt)
        if json_data is None:
            raise ValueError("JSON data is None")
        cleaned_up_json_data=json_data.strip("```json").strip("```").strip()
        texts=json.loads(cleaned_up_json_data)

        return texts

    def paste_lines(self,text:TextItem,draw: ImageDraw.Draw):
        x_axis,y_axis=int(text["x"])+23.88,int(text["y"])
        text_box_width=int(text["width"])
        lines=text["lines"]['data']
        lines=sorted(lines,key=lambda x: x['number'])
        for i,line in enumerate(lines):
            character_limit=int(line["char"])
            string=line["text_value"]
            value=string[:character_limit]
            value=re.sub(r'[^A-Za-z0-9 _-]', '', string)
            font_path=f'./static/fonts/{line["font"]}'
            font_size=int(line["font_size"])*4.235       
            font=self.load_font(font_path,font_size)     
            align=line["align"]
            color=line["font_color"]
            bbox = draw.textbbox((0, 0), value, font=font,font_size=font_size)
            text_height = bbox[3] - bbox[1]
            text_width = bbox[2] - bbox[0]
            x_axis=self.align_text(align,text_width,x_axis,text_box_width)
            y_offset=line.get("offset",20)
            line_y = y_axis + i * (text_height + y_offset)
            draw.text((x_axis, line_y), value, fill=color, font=font,anchor="lt")

    def load_font(self,font_path, font_size=20):
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

    def align_text(self,align:str, text_width:int,x_axis:int,text_box_width:int):
        # return x_axis
        width = abs(text_box_width - text_width)
        if align=='center' or align=='centre' :
            return x_axis +(width)//2
        elif align=='right':
            return x_axis + width
        else:
            return x_axis
    
    def insert_vectors(self):
        vectors=self.template["vectors"]
        text_data=self.template["text_list"]
        for idx,text in enumerate(text_data):
            if idx >= len(vectors) or vectors[idx] is None:
                continue
            vector=vectors[idx]
            color=vector["color"]
            height=int(vector["height"])
            width=int(vector["width"])
            x_axis,y_axis=int(vector["x"]),int(vector["y"])
            text_values=[line["text_value"] for line in text["lines"]["data"] ]
            prompt=f"""
                    Generate a svg vector based on the values provided : {text_values} in circular shape 
                    The svg is used to showcase a feature of a product.
                    The svg size is {width}x{height}
            """
            svg_code=generate_svg(prompt)
            svg_code=svg_code.strip("```svg")
            location=svg_code.find("```")
            if location != -1:
                svg_code=svg_code[:location]
            
            if not svg_code or svg_code.strip() == "":
                raise ValueError("SVG code is empty or None.")
            svg_code = svg_code.replace("{stroke}", color)
            try:
                png_data =self.convert_svg_to_png(svg_code, width, height)
            except Exception as e:
                print("Error converting SVG to PNG:", e)
                continue
            with Image.open(BytesIO(png_data)) as png:
                bg_image=self.background_image
                bg_image.paste(png, (x_axis, y_axis), png)

    def convert_svg_to_png(self,svg_code, width, height):
    # Check if svg_code is not empty or None
        if not svg_code:
            raise ValueError("SVG code is empty or None.")
        try:
            # Convert SVG to PNG
            png_data = cairosvg.svg2png(bytestring=svg_code.encode('utf-8'), output_width=width, output_height=height)
        except Exception as e:
            # Handle and log the specific error
            print("Error converting SVG to PNG:", e)
            raise e

        return png_data