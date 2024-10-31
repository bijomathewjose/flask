from flask import Blueprint,render_template,jsonify,request
from utils import db,google
from typing import Dict,List,Any
import os

creative_bp = Blueprint('creative', __name__,template_folder='./templates')

SHEET_LINK=os.getenv('TEMPLATES_GOOGLE_SHEET_LINK')
SHEET_NAME=os.getenv('TEMPLATES_GOOGLE_SHEET_NAME')

@creative_bp.route('/',methods=['GET','POST'])
def creative():
    if request.method == 'GET':
        return render_template('creative.html')
    
    if request.method != 'POST':
        return jsonify({'error':'Invalid request method'}), 400
    result={}
    sku_id = request.form.get('sku_id')
    template_number = int(request.form.get('template_number'))
    input= request.form.to_dict()
    if sku_id:
        result['input'] = input
    else:
        return jsonify({'error':'SKU is required'}), 400
    # get_data_from_db(sku_id)
    data=get_templates_from_sheet()
    template_models=get_a_plus_template_models(data,template_number)
    result['template_models']=template_models
    result['text_types']=process_models(template_models)

    return jsonify(result), 200


def get_data_from_db(sku_id):
    conn = db.create_connection()
    query = 'SELECT * FROM all_platform_products WHERE sku =%s'
    params = (sku_id,)
    data = db.fetch_data(conn,query,params)
    data=data[0]
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

def get_text_type(model: Dict[str,Any]):
    text_types=[]
    # string to dict
    model= dict(eval(model))
    for key,value in model.items(): 
        if 'text' in key and 'type' in key:
            text_types.append({key:value})
    return text_types

def process_models(models:List[str]):
    list_of_text_types={}
    for index,model in enumerate(models):
        text_types=get_text_type(model)
        list_of_text_types[index]=(text_types)
    return list_of_text_types