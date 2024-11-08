from flask import Blueprint,jsonify,send_file
from blueprints.creative_render.TemplateRender import CreativeRender
from blueprints.creative_render.types import TemplateData
from .external_data import get_data_from_db, get_templates_from_sheet
from .process_data import add_db_data, get_a_plus_template_models, process_models

import traceback


creative_bp = Blueprint('creative', __name__,template_folder='./templates')

import os
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
    if not result['db']:
        return jsonify({'error':'SKU not found'}), 404
    temp_no=result['db'].get('temp_number',None)
    if temp_no:
        template_number=int(temp_no)
    data=get_templates_from_sheet()
    template_models=get_a_plus_template_models(data,template_number)
    processed_data=process_models(template_models)
    processed_data=add_db_data(result['db'],processed_data)
    result['processed_data']=processed_data
    if True:
        try:
            template:TemplateData=processed_data[0]
            render=CreativeRender(template,result['db'])
            render.insert_images()
            render.insert_the_texts()
            rendered_image =render.get_background_image()
        except Exception as e:
            return jsonify({'error':str(e),'traceback':traceback.format_exc()}), 500
        return send_file(rendered_image, mimetype='image/jpg')
    return jsonify(result), 200