from config.flask import create_app
from dotenv import load_dotenv
from flask import render_template
import os

load_dotenv()

app, celery ,logger = create_app()

from routes import api_v1
app.register_blueprint(api_v1, url_prefix='/api/v1')

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/health')
def health():
    return "Server is Healthy", 200
