from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from openpyxl import Workbook
from io import BytesIO
import os

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this to a random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usb_hub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        company = request.form['company']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        
        # Check if a record with the same first name, last name, and company already exists
        existing_record = Record.query.filter_by(
            first_name=first_name,
            last_name=last_name,
            company=company
        ).first()
        
        if existing_record:
            flash('A record with this name and company already exists.', 'error')
            return redirect(url_for('index'))
        
        new_record = Record(first_name=first_name, last_name=last_name, company=company, date=date)
        db.session.add(new_record)
        db.session.commit()
        
        flash('Record added successfully!', 'success')
        return redirect(url_for('scan_instructions'))
    
    return render_template('index.html', current_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please use a different email or log in.')
            return redirect(url_for('register'))
        
        new_user = User(email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/scan-instructions')
@login_required
def scan_instructions():
    return render_template('scan_instructions.html')

@app.route('/search')
@login_required
def search():
    company = request.args.get('company', '')
    display_all = request.args.get('display_all', 'false')

    if display_all == 'true':
        results = Record.query.all()
    elif company:
        results = Record.query.filter(Record.company.ilike(f'%{company}%')).all()
    else:
        results = []

    return render_template('search.html', records=results)

@app.route('/export')
@login_required
def export_excel():
    records = Record.query.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "USB Hub Records"

    headers = ['First Name', 'Last Name', 'Company', 'Date']
    ws.append(headers)

    for record in records:
        ws.append([record.first_name, record.last_name, record.company, record.date.strftime('%Y-%m-%d')])

    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)

    return send_file(excel_file, 
                     download_name='usb_hub_records.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)