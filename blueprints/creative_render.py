from flask import Blueprint,render_template,jsonify,request,send_file
from utils import db,google
from typing import Dict,List,Any
import os
import io
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont

creative_bp = Blueprint('creative', __name__,template_folder='./templates')

SHEET_LINK=os.getenv('TEMPLATES_GOOGLE_SHEET_LINK')
SHEET_NAME=os.getenv('TEMPLATES_GOOGLE_SHEET_NAME')

@creative_bp.route('/<sku_id>/<template_number>',methods=['GET'])
def creative(sku_id,template_number):
    # if request.method == 'GET':
        # return render_template('creative.html')
    
    # if request.method != 'POST':
    #     return jsonify({'error':'Invalid request method'}), 400
    result={}
    # sku_id = request.form.get('sku_id')
    # template_number = int(request.form.get('template_number'))
    template_number=int(template_number)
    # input= request.form.to_dict()
    if sku_id:
        result['input'] = {
            'sku_id': sku_id,
            'template_number': template_number
        }
    else:
        return jsonify({'error':'SKU is required'}), 400
    result['db']=get_data_from_db(sku_id)
    temp_no=result['db'].get('temp_number',None)
    if temp_no:
        template_number=int(temp_no)
    data=get_templates_from_sheet()
    template_models=get_a_plus_template_models(data,template_number)
    # result['template_models']=template_models
    processed_data=process_models(template_models)
    processed_data=add_db_data(result['db'],processed_data)
    result['processed_data']=processed_data
    rendered_image = render_to_image(processed_data)
    return send_file(rendered_image, mimetype='image/jpg')
    return jsonify(result), 200


def get_data_from_db(sku_id):
    conn = db.create_connection()
    query = 'SELECT * FROM all_platform_products WHERE sku =%s'
    params = (sku_id,)
    data = db.fetch_data(conn,query,params)
    data = data[0] if data else None
    db.close_connection(conn)
    return data

def get_templates_from_sheet():
    sheet_id=google.get_sheet_id(SHEET_LINK)
    data=google.get_sheet_data(sheet_id,SHEET_NAME)
    return data

def get_a_plus_template_models(data:List[List[str]],template_number:int):
    models=[]
    template_list=data[1:]
    template_index=template_number+1
    for template in template_list:
        if 'A+' not in template[0].strip():
            continue
        model=template[template_index]
        if not model:
            continue
        models.append(model)
    return models

def get_element_list(model: Dict[str,Any]):
    element_list={}
    # string to dict
    model= dict(eval(model))
    for key,value in model.items(): 
        element_list[key]=value
    return element_list

def process_models(models:List[str]):
    list_of_text_types=[]
    for index,model in enumerate(models):
        images,text_list=segragate_images_and_text(model)
        list_of_text_types.append({
            'demo':index+1,
            'images':images,
            'text_list':text_list   
        })
    return list_of_text_types

def segragate_images_and_text(data:Dict[str,Any]):
    data= dict(eval(data))

    images = []
    texts = []
    # Separate images and texts dynamically
    for key, value in data.items():
        if key.startswith("img"):
            img_num = int(key[3])  # Extract the image number
            while len(images) < img_num:
                images.append({})
            images[img_num - 1][key[5:]] = value  # Add property to correct image dict
            images[img_num - 1]["number"] = img_num
        elif key.startswith("text"):
            text_num = int(key[4])  # Extract the text number
            while len(texts) < text_num:
                texts.append({})
            if key.endswith("lines"):
                texts[text_num - 1]["lines"] = parse_text_lines(value)
            else:
                texts[text_num - 1][key[6:]] = value
            texts[text_num - 1]["number"] = text_num
    return images, texts

def parse_text_lines(lines_dict):
    lines = []
    for line_key, line_value in lines_dict.items():
        if line_key.startswith("line"):
            line_num = int(line_key[4])
            while len(lines) < line_num:
                lines.append({})
            lines[line_num - 1][line_key[6:]] = line_value
            lines[line_num - 1]['number'] = line_num
        else:
            # Handle metadata like "no_of_lines"
            lines_dict[line_key] = line_value
    return {"data": lines, "metadata": lines_dict.get("no_of_lines", None)}

    
def add_db_data(db_data:Dict[str,Any],processed_data:List[Dict[str,Any]]):
    for data in processed_data:
        count=0
        for image in data['images']:
            if count>=4:
                break
            if image['number'] in [1,2,3,4]:
                image['url']=db_data.get(f'img_{image["number"]}',None)
                count+=1
    return processed_data

def render_to_image(template_data: List[Dict[str, Any]],width:int=1000,height:int=1000):
    
    # Load the background image
    if not os.path.exists('./assets/bg.jpg'):
        return jsonify({'error':'Background image not found'}), 500
    with Image.open('./assets/bg.jpg') as background:
        background = background.convert("RGBA")
        original_width, original_height = background.size
        ratio = min(width / original_width, height / original_height)
        width = int(original_width * ratio)
        height = int(original_height * ratio)    
        background = background.resize((width, height), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(background)

    # Render images
    count=0
    for image_data in template_data[0]["images"]:
        if count>=4:
            break
        response = requests.get(image_data['url'])
        if response.status_code != 200:
            continue
        with Image.open(BytesIO(response.content)) as img:
            img = img.convert("RGBA")
            img = img.rotate(int(image_data["angle"]), expand=True)
            o_wid, o_hei = img.size
            o_ratio = min(int(image_data["width"]) / o_wid, int(image_data["height"]) / o_hei)
            img = img.resize((int(o_wid * o_ratio), int(o_hei * o_ratio)), Image.Resampling.LANCZOS)
            background.paste(img, (int(image_data["x"]), int(image_data["y"])), img)
            count+=1
    # Render text
    for text_data in template_data[0]["text_list"]:
        prev=0
        line_number=0
        for line in text_data["lines"]["data"]:
            start=prev
            number_of_chars=int(line['char'])
            end= start+number_of_chars+1
            prev+=end
            data=(f"{text_data['number']}{text_data["type"]}")[start:end]
            text_position = (int(text_data["x"]), int(text_data["y"])+(line_number*int(line["font_size"])*2.5))
            draw.text(text_position,data, fill=line["font_color"], anchor="mm")
            line_number+=1
    # Save to in-memory file
    img_byte_arr = io.BytesIO()
    background.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return img_byte_arr