import os

GOOGLE_SERVICE_TYPE=os.getenv('GOOGLE_SERVICE_TYPE')
GOOGLE_PROJECT_ID=os.getenv('GOOGLE_PROJECT_ID')
GOOGLE_PRIVATE_KEY=os.getenv('GOOGLE_PRIVATE_KEY')
GOOGLE_PRIVATE_KEY_ID=os.getenv('GOOGLE_PRIVATE_KEY_ID')
GOOGLE_CLIENT_EMAIL=os.getenv('GOOGLE_CLIENT_EMAIL')
GOOGLE_CLIENT_ID=os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_AUTH_URI=os.getenv('GOOGLE_AUTH_URI')
GOOGLE_TOKEN_URI=os.getenv('GOOGLE_TOKEN_URI')
GOOGLE_AUTH_PROVIDER_X509_CERT_URL=os.getenv('GOOGLE_AUTH_PROVIDER_X509_CERT_URL')
GOOGLE_CLIENT_X509_CERT_URL=os.getenv('GOOGLE_CLIENT_X509_CERT_URL')
GOOGLE_UNIVERSE_DOMAIN=os.getenv('GOOGLE_UNIVERSE_DOMAIN')

GOOGLE_CREDENTIALS = {
        "type": GOOGLE_SERVICE_TYPE,
        "project_id": GOOGLE_PROJECT_ID,
        "private_key_id": GOOGLE_PRIVATE_KEY_ID,
        "private_key": GOOGLE_PRIVATE_KEY,
        "client_email": GOOGLE_CLIENT_EMAIL,
        "client_id": GOOGLE_CLIENT_ID,
        "auth_uri": GOOGLE_AUTH_URI,
        "token_uri": GOOGLE_TOKEN_URI,
        "auth_provider_x509_cert_url": GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
        "client_x509_cert_url": GOOGLE_CLIENT_X509_CERT_URL,
        "universe_domain": GOOGLE_UNIVERSE_DOMAIN,
}
GOOGLE_CREDENTIALS['private_key'] = GOOGLE_CREDENTIALS['private_key'].replace('\\n', '\n')

SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

from .sheets import *