from google.oauth2 import service_account
import gspread
from . import GOOGLE_CREDENTIALS, SHEET_SCOPES

def get_sheets_service():
    """
    Creates and returns a Google Sheets API service object.
    """
    credentials = service_account.Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=SHEET_SCOPES)
    service = gspread.authorize(credentials)
    return service

def get_sheet_data(sheet_id: str, sheet_name: str):
    """
    Fetches data from a Google Sheet.
    """
    data=[]
    service = get_sheets_service()
    sheet = service.open_by_key(sheet_id)
    worksheet = sheet.worksheet(sheet_name)
    data = worksheet.get_all_values()
    return data

def get_sheet_id(url: str):
    """
    Extracts the sheet ID and sheet name from a Google Sheet URL.
    """
    sheet_id = url.split('/')[-2]
    return sheet_id