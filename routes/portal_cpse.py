from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps

cpse_bp = Blueprint('cpse', __name__, url_prefix='/cpse')

def login_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('auth.login'))
            if session.get('role') != role:
                return "Access Denied: You do not have permission to view this page.", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@cpse_bp.route('/dashboard')
@login_required('CPSE')
def dashboard():
    return render_template('cpse/dashboard.html', name=session.get('name'), cpse_name=session.get('cpse_name'))
