from flask import Blueprint,jsonify,request
from werkzeug.utils import secure_filename
import os
from utils.csv_parser import parse_csv_to_list
from .lifestyle_shots import lifestyle_shots
from .get_3D360_shots import get3D360
from .bg_elimination import bg_elimination
from .bg_elimination_bleed import bg_elimination_bleed

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/', methods=['POST'])
def upload_file():
    try:
        outputs=[]
        seller_id,csv_path = handle_inputs()
        list_of_process = parse_csv_to_list(csv_path)
        for process in list_of_process:
            output=process_handler(seller_id,process)
            outputs.append(output)
        return jsonify({"message": f"Batch process completed successfully {outputs}", }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def process_handler(seller_id,process):
    sku_id = process['sku_id']
    process_id = process['process_id']
    list_of_process_completed = []
    urls=[]
    if process_id=='lifestyle_shot':
        urls=lifestyle_shots(seller_id,sku_id)
        list_of_process_completed.append({"process":"lifestyle_shots", "urls":urls,"response":"success"})
        print({"message": f"Lifestyle shots processed successfully: {urls}"})
    elif process_id == "3D360":
        urls=[get3D360(seller_id,sku_id)]
        list_of_process_completed.append({"process":"3D360", "urls":urls,"response":"success"})
        print({"message": f"3D360 shots processed successfully: {urls}"})
    elif process_id == "bg_elimination":
        urls=bg_elimination(seller_id,sku_id)
        list_of_process_completed.append({"process":"bg_elimination", "urls":urls,"response":"success"})
        print({"message": f"Background elimination processed successfully: {urls}"})
    elif process_id == "bg_elimination with bleed":
        urls=bg_elimination_bleed(seller_id,sku_id)
        list_of_process_completed.append({"process":"bg_elimination with bleed", "urls":urls,"response":"success"})
        print({"message": f"Background elimination with bleed processed successfully: {urls}"})
    else:
        list_of_process_completed.append({"process":process_id, "urls":[],"response":"error"})

    return list_of_process_completed

def handle_inputs():
    if 'csv' not in request.files:
        return jsonify({"error": "No CSV file part"}), 400

    csv_file = request.files['csv']
    seller_id = request.form.get('sellerId')
    partner_id = request.form.get('partnerId')

    if not seller_id:
        raise ValueError(f"Missing required field: sellerId")

    if not partner_id:
        raise ValueError(f"Missing required field: partnerId")
    
    if not (csv_file and allowed_file(csv_file.filename)):
        raise ValueError(f"Invalid or missing CSV file")

    # Save the uploaded CSV file temporarily
    csv_filename = secure_filename(csv_file.filename)
    csv_path = os.path.join('uploads', csv_filename)
    csv_file.save(csv_path)

    return seller_id,csv_path

ALLOWED_EXTENSIONS = {'csv'}  # Only allow CSV file uploads for SKU information

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS