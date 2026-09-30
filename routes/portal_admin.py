from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

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

@admin_bp.route('/dashboard')
@login_required('ADMIN')
def dashboard():
    return render_template('admin/dashboard.html', name=session.get('name'))
