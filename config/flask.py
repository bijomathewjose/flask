from flask import Flask
import logging
from flask_cors import CORS
from .celery import make_celery
import os

def create_app():
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info('Creating app...')
    app.url_map.strict_slashes = False

    app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
    app.config['result_backend'] = os.getenv('result_backend', 'redis://redis:6379/0')
    app.config['broker_connection_retry_on_startup'] = True  

    CORS(app, resources={r"/*": {
    "origins": ["*"],
    "methods": ["GET", "POST", "PUT", "DELETE","OPTIONS"],
    "allow_headers": ["Content-Type"]
    }})

    celery = make_celery(app)

    return app, celery,logger