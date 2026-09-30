from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth_bp = Blueprint('auth', __name__)

# Dummy users for prototype
USERS = {
    "ongc_user": {"password": "password123", "role": "CPSE", "name": "Rajesh Kumar", "cpse_name": "ONGC"},
    "ntpc_user": {"password": "password123", "role": "CPSE", "name": "Priya Singh", "cpse_name": "NTPC"},
    "sail_user": {"password": "password123", "role": "CPSE", "name": "Amit Sharma", "cpse_name": "SAIL"},
    "coal_user": {"password": "password123", "role": "CPSE", "name": "Sanjay Verma", "cpse_name": "Coal India"},
    "admin_user": {"password": "admin123", "role": "ADMIN", "name": "Ministry Admin", "cpse_name": "Ministry"}
}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = USERS.get(username)
        if user and user['password'] == password:
            session['user'] = username
            session['role'] = user['role']
            session['name'] = user['name']
            session['cpse_name'] = user.get('cpse_name', 'Unknown')
            
            if user['role'] == 'CPSE':
                return redirect(url_for('cpse.dashboard'))
            else:
                return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid username or password", "error")
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
