import os
from utils import db,google

SHEET_LINK=os.getenv('TEMPLATES_GOOGLE_SHEET_LINK')
SHEET_NAME=os.getenv('TEMPLATES_GOOGLE_SHEET_NAME')

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
    