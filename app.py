from config.flask import create_app
from flask import jsonify
app,celery = create_app()

from routes import api_v1
app.register_blueprint(api_v1, url_prefix='/api/v1')

@app.route('/')
def index():
    return 'Welcome to the Flask API'

@app.route('/health')
def health():
    return "Server is Healthy", 200