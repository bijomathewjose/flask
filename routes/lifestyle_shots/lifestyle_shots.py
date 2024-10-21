from flask import request
import csv
from utils import db,external_api as EX_API,Gen_AI,image as IMG,directory as DIR
from .celery import process_image_task

def lifestyle_shots():
    user_id,sku_id_list = handle_input()
    if not DIR.check_folder_exists(user_id):
        raise ValueError(f"Folder '{user_id}' does not exist.")
    images = DIR.list_files_in_directory(user_id)
    task_ids = handle_input_images(images,sku_id_list)
    return task_ids

def handle_input():
    if 'user_id' not in request.form:
        raise ValueError("User ID is required")
    user_id = request.form['user_id']
    if 'csv_file' not in request.files:
        raise ValueError("CSV file is required")
    csv_file = request.files['csv_file']
    sku_id_list = parse_csv_file(csv_file)
    return user_id,sku_id_list

def parse_csv_file(csv_file):
    # parse the csv file and return a list of dictionaries
    csv_data = csv.reader(csv_file)
    sku_id_list = []
    for row in csv_data:
        sku_id_list.append(row[0][0])
    return sku_id_list

def handle_input_images(images):
    task_ids = []
    if not images:
        raise ValueError("Images are required")
    for image in images:
        task_id=process_image_task.delay(image['file_id'], image['file_name'], 'lifestyle-shots')
        task_ids.append(task_id)
    return task_ids

def get_data_from_db(sku):
    connection = db.create_connection()
    query = "SELECT text_dump FROM products WHERE sku = %s"
    params = (sku,)
    data = db.fetch_data(connection, query, params)
    if not data or data[0]['text_dump'] is None:
        raise ValueError("No data found for the given SKU or text_dump is empty")
    db.close_connection(connection)
    return data

def generate_prompt(data):
    prompt_text = (
            f"This is the product information : {data}\n\n"
            f"Based on provided data for this image\n\n"
            "Generate prompt for creating a lifestyle shot background suitable for the product.\n\n"
            "Follow AUP or AWS Responsible AI Policy to generate the background."
            "Prompt should be within 500 characters and should not be greater."
    )
    prompt_text = Gen_AI.generate_prompt(prompt_text)
    return prompt_text

def remove_background(file):
    """
    Removes the background from an image and returns the image with no background.
    """
    file_data = file.read()
    if not file_data:
        raise ValueError("Failed to download image data")
    image_with_no_bg = EX_API.remove_background(file_data)
    return image_with_no_bg