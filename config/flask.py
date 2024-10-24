import logging
import os
from flask import Flask
from flask_cors import CORS



def create_app(app, logger):
    logging.basicConfig(level=logging.INFO)

    if logger is None:
        logger = logging.getLogger(__name__)
        logger.info('Created logger...')
    else:
        logger.info('Logger already created...')

    if app is None:
        logger.info("Creating app...")
        app = Flask(__name__, template_folder='../templates')
        logger.info("App created...")
        app.url_map.strict_slashes = False
        app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
        app.config['result_backend'] = os.getenv('result_backend', 'redis://redis:6379/0')
        app.config['broker_connection_retry_on_startup'] = True
        logger.info("App config set...")
        CORS(app, resources={r"/*": {
            "origins": ["*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }})
        logger.info("CORS set...")
    else:
        logger.info('App already created...')

    return app, logger
