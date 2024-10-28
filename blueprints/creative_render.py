from flask import Blueprint,render_template

creative_bp = Blueprint('creative', __name__)

@creative_bp.route('/')
def creative():
    return render_template('index.html')