from flask import Flask, request, session, redirect, url_for, render_template, flash
import boto3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os
from dotenv import load_dotenv
from functools import wraps

# Load .env variables
load_dotenv()

# Flask Setup
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fleetsync_secret_key_2024')

# AWS and Email Config
AWS_REGION = os.environ.get('AWS_REGION_NAME', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns = boto3.client('sns', region_name=AWS_REGION)

# Email Config
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD')
ENABLE_EMAIL = os.environ.get('ENABLE_EMAIL', 'False').lower() == 'true'
ENABLE_SNS = os.environ.get('ENABLE_SNS', 'False').lower() == 'true'
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

# Table Names
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'FleetSyncUsers')
users_table = dynamodb.Table(USERS_TABLE_NAME)

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("fleetsync.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
app = Flask(__name__)
app.secret_key = "secretkey123"

users = {}  # Example: {'user1': 'password123'}
cart = []

products = [
    {"id": 1, "name": "Gongura Pickle", "price": 120, "image":'images/gongurapickle.jpg'},
    {"id": 2, "name": "Lemon Pickle", "price": 100, "image": 'images/lemon.jpg'},
    {"id": 3, "name": "Chilli Pickle", "price": 130, "image": 'images/chillipickle.jpg'},
    {'id': 4, 'name': 'Chicken Pickle', 'price': 180, 'image': 'images/chiken.jpg'},
        {'id': 5, 'name': 'Prawn Pickle', 'price': 200, 'image': 'images/prwan.jpg'},
    ]
snack_list = [
        {"id": 6, "name": "Murukku", "price": 60, "image": 'images/murukulu.jpg'},
        {"id": 7, "name": "Mixture", "price": 70, "image": 'images/mixture.jpg'},
        {"id": 8, "name": "Kajjikaya", "price": 80, "image":'images/kajikaya.jpg'},
        {"id": 9, "name": "Chekkalu", "price": 50, "image": 'images/chekkalu.jpg'},
        {"id": 10, "name": "Boondi", "price": 65, "image":'images/boondi.jpg'},
        {"id": 11, "name": "Chakodi", "price": 55, "image": 'images/chekodilu.jpg'},
    ]
def is_logged_in():
    return 'email' in session

def get_user_role(email):
    try:
        response = users_table.get_item(Key={'email': email})
        return response.get('Item', {}).get('role')
    except Exception as e:
        logger.error(f"Role fetch error: {e}")
        return None

def send_email(to, subject, body):
    if not ENABLE_EMAIL:
        logger.info(f"[EMAIL DISABLED] {subject}")
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to, msg.as_string())
        logger.info(f"Email sent to {to}")
    except Exception as e:
        logger.error(f"Email error: {e}")

def publish_to_sns(message, subject="FleetSync Notification"):
    if not ENABLE_SNS:
        logger.info("[SNS DISABLED]")
        return
    try:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject=subject)
        logger.info("SNS message sent.")
    except Exception as e:
        logger.error(f"SNS error: {e}")

def require_role(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not is_logged_in():
                flash("Please log in first", "warning")
                return redirect(url_for('login'))
            role = get_user_role(session['email'])
            if required_role != 'any' and role != required_role:
                flash("Access denied", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator
@app.route('/snacks')
def snacks():
    snack_list = [
        {"id": 6, "name": "Murukku", "price": 60, "image": url_for('static', filename='images/murukulu.jpg')},
        {"id": 7, "name": "Mixture", "price": 70, "image": url_for('static', filename='images/mixture.jpg')},
        {"id": 8, "name": "Kajjikaya", "price": 80, "image": url_for('static', filename='images/kajikaya.jpg')},
        {"id": 9, "name": "Chekkalu", "price": 50, "image": url_for('static', filename='images/chekkalu.jpg')},
        {"id": 10, "name": "Boondi", "price": 65, "image": url_for('static', filename='images/boondi.jpg')},
        {"id": 11, "name": "Chakodi", "price": 55, "image": url_for('static', filename='images/chekodilu.jpg')},
    ]
    return render_template("snacks.html", snacks=snack_list)




@app.route('/')
def home():
    return render_template("home.html", products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        if uname in users:
            flash("cartUsername already exists!")
        else:
            users[uname] = pwd
            flash("Registered successfully!")
            return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        if uname in users and users[uname] == pwd:
            session['username'] = uname
            flash("Login successful!")
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials!")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Logged out successfully!")
    return redirect(url_for('home'))
@app.route('/about')
def about():
    return render_template("about.html")
@app.route('/pickles')
def show_pickles():
    pickles = [p for p in products if 'pickle' in p['name'].lower()]
    return render_template("pickles.html", pickles=pickles)

@app.route('/snacks')
def show_snacks():
    snacks = [p for p in products if 'pickle' not in p['name'].lower()]
    return render_template("snacks.html", snacks=snacks)
@app.route('/veg_pickles')
def veg_pickles():
    pickles = [
        {'id': 1, 'name': 'Mango Pickle', 'price': 120, 'image': 'images/mango.jpg'},
        {'id': 2, 'name': 'Lemon Pickle', 'price': 100, 'image': 'images/lemon.jpg'},
    ]
    return render_template('pickles.html', pickles=pickles)

@app.route('/non_veg_pickles')
def non_veg_pickles():
    pickles = [
        {'id': 3, 'name': 'Chicken Pickle', 'price': 180, 'image': 'images/chiken.jpg'},
        {'id': 4, 'name': 'Prawn Pickle', 'price': 200, 'image': 'images/prwan.jpg'},
    ]
    return render_template('pickles.html', pickles=pickles)
# Replace global cart list with session-based cart management
@app.before_request
def initialize_cart():
    if 'cart' not in session:
        session['cart'] = []

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    # Combine both lists for lookup
    all_items = products + snack_list
    for item in all_items:
        if item["id"] == product_id:
            cart = session.get('cart', [])
            cart.append(item)
            session['cart'] = cart
            flash(f"{item['name']} added to cart.")
            break
    return redirect(request.referrer or url_for('home'))

@app.route('/cart')
def cart_page():
    return render_template("cart.html", cart=session.get('cart', []))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', [])

    if request.method == 'POST':
        session['cart'] = []  # Clear cart on order
        flash('Order placed successfully!')
        return redirect(url_for('order_success'))

    return render_template('checkout.html', cart=cart)

@app.route('/order_success')
def order_success():
    return render_template('success.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # You could handle form submission here (e.g., send email)
        flash("Thanks for contacting us! We'll get back to you soon.")
        return redirect(url_for('contact'))
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
