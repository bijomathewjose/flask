from celery import Celery
import logging

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['result_backend'],
        broker=app.config['CELERY_BROKER_URL'],   
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    
    logging.basicConfig(level=logging.INFO)  # Set logging level
    logger = logging.getLogger(__name__)
    logger.info("Celery has been set up")

    return celery