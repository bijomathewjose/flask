from dotenv import load_dotenv
from flask import render_template,Flask
from flask_cors import CORS
import logging
load_dotenv()
logger = logging.getLogger(__name__)
app = Flask(__name__,template_folder='./templates')
CORS(app)
from blueprints import creative_bp,upload_bp

app.register_blueprint(upload_bp, url_prefix='/upload')
app.register_blueprint(creative_bp, url_prefix='/creative')

@app.route('/')
def index():
    logger.info("index")
    return render_template('index.html')
    
@app.route('/health')
def health():
    return "Server is Healthy", 200

if __name__ == '__main__':
    # Enable debug mode and allow external connections by setting host to '0.0.0.0'
    app.run(host='0.0.0.0', debug=True)