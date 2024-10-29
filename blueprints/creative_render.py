from flask import Blueprint,render_template

creative_bp = Blueprint('creative', __name__,template_folder='./templates')

@creative_bp.route('/')
def creative():
    return render_template('creative.html')