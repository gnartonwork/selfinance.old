from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from datetime import datetime, date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '1'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    accounts = db.relationship('Account', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    reports = db.relationship('Report', backref='user', lazy=True)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    balance = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship('Transaction', backref='account', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    transaction_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_description = db.Column(db.String(255))

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)
    report_date = db.Column(db.DateTime, default=datetime.utcnow)
    content = db.Column(db.String(255))

# Bổ sung một hàm kiểm tra đăng nhập
def is_logged_in():
    return 'username' in session

# Bổ sung decorator để kiểm tra đăng nhập trước khi truy cập các trang sau
def login_required_decorator(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if is_logged_in():
            return route_function(*args, **kwargs)
        return redirect(url_for('login'))
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Add a condition to check for the default username and password
        if username == 'me' and password == '123456':
            session['username'] = username
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required_decorator
def dashboard():
    return render_template('dashboard.html', username=session['username'])

@app.route('/manage_account')
@login_required_decorator
def manage_account():
    current_user = User.query.filter_by(username=session['username']).first()
    return render_template('manage_account.html', user_details=current_user)


@app.route('/manage_finance', methods=['GET', 'POST'])
@login_required_decorator
def manage_finance():
    net_profit = 0  # Default value or calculate it based on your logic

    if request.method == 'POST':
        # Handle form submission and calculate net_profit here
        income = float(request.form.get('income', 0))
        interest = float(request.form.get('interest', 0))
        loss = float(request.form.get('loss', 0))
        loaner = float(request.form.get('loaner', 0))

        # Check if transaction_date is provided in the form
        transaction_date_str = request.form.get('transaction_date')
        if transaction_date_str:
            transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d')
        else:
            # Handle the case where transaction_date is not provided
            transaction_date = datetime.utcnow()
        
        net_profit = income + interest - loss - loaner

        # Lấy thông tin người dùng từ session
        current_user = User.query.filter_by(username=session['username']).first()

        if current_user:
            # Lưu dữ liệu vào database
            account = Account.query.filter_by(user_id=current_user.id).first()

            if account:
                transaction = Transaction(
                    user_id=current_user.id,
                    account_id=account.id,
                    transaction_type='financial_data',
                    amount=net_profit,
                    transaction_date=transaction_date,
                    transaction_description="Financial transaction"
                )

                db.session.add(transaction)
                db.session.commit()

            else:
                flash('Account not found', 'error')
        else:
            flash('User not found', 'error')

    return render_template('manage_finance.html', username=session.get('username'), net_profit=net_profit)


@app.route('/write_report', methods=['GET', 'POST'])
@login_required_decorator
def write_report():
    daily_net_profits = []
    average_monthly_net_profit = 0

    if request.method == 'POST':
        # Lấy dữ liệu tài chính từ database
        user_id = User.query.filter_by(username=session['username']).first().id
        financial_data = Transaction.query.filter_by(user_id=user_id, transaction_type='financial_data').all()

        # Thực hiện các tính toán cần thiết cho báo cáo hàng ngày và hàng tháng
        daily_net_profits = [data.amount for data in financial_data if data.transaction_date.date() == date.today()]
        monthly_net_profits = [data.amount for data in financial_data if data.transaction_date.month == date.today().month]

        # Tính toán trung bình lợi nhuận hàng tháng
        average_monthly_net_profit = sum(monthly_net_profits) / len(monthly_net_profits) if monthly_net_profits else 0

        flash('Report generated successfully', 'success')

    return render_template('write_report.html', username=session['username'],
                           daily_net_profits=daily_net_profits,
                           average_monthly_net_profit=average_monthly_net_profit)

@app.route('/maintenance')
@login_required_decorator
def maintenance():
    return render_template('maintenance.html', username=session['username'])

if __name__ == '__main__':
    app.run(debug=True)
