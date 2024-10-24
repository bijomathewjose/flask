from celery import Celery
import logging


def make_celery(app):
    celery_app = Celery(
        app.import_name,
        backend=app.config['result_backend'],
        broker=app.config['CELERY_BROKER_URL'],   
    )
    celery_app.conf.update(app.config)

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery_app.Task = ContextTask
    
    logging.basicConfig(level=logging.INFO)  # Set logging level
    logger = logging.getLogger(__name__)
    logger.info("Celery has been set up")

    return celery_app