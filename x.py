from flask import request, session
import mysql.connector
import re
import os
import uuid
from dotenv import load_dotenv

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from icecream import ic
ic.configureOutput(prefix=f'!0!x.py!0! | ', includeContext=True)

load_dotenv()

# Email credentials
sender_email = os.getenv("EMAIL_COMPANY")
password = os.getenv("EMAIL_PASSWORD")

##############################
def db():
    db = mysql.connector.connect(
        host = "mysql",      # Replace with your MySQL server's address or docker service name "mysql"
        user = "root",  # Replace with your MySQL username
        password = "password",  # Replace with your MySQL password
        database = "company"   # Replace with your MySQL database name
    )
    cursor = db.cursor(dictionary=True)
    return db, cursor

##############################
#Upload validation
ITEM_NAME_REGEX = r"^[a-zA-Z0-9æøåÆØÅ\s.,'\"()\-!?]+$"
ITEM_DESCRIPTION_REGEX = r"^[a-zA-Z0-9æøåÆØÅ\s.,'\"()\-!?]+$"
ITEM_ADDRESS_REGEX = r"^[\w\s.,'°\-#æøåÆØÅéÉäÄöÖëËèÈêÊôÔüÜ]+$"
ITEM_PRICE_REGEX = r"^\d{1,6}(\.\d{1,2})?$"
ITEM_LAT_REGEX = r"^-?([0-8]?\d(\.\d{1,8})?|90(\.0{1,8})?)$"
ITEM_LON_REGEX = r"^-?(1[0-7]\d|0?\d{1,2}|180)(\.\d{1,8})?$"

def validate_item_name():
    name = request.form.get("item_name", "").strip()
    if len(name) < 2 or len(name) > 60:
        raise Exception("company_ex name must be between 2 and 60 characters")
    if not re.match(ITEM_NAME_REGEX, name):
        raise Exception("company_ex name contains invalid characters")
    return name


def validate_item_description():
    description = request.form.get("item_description", "").strip()
    if len(description) < 5 or len(description) > 400:
        raise Exception("company_ex description must be between 5 and 400 characters")
    if not re.match(ITEM_DESCRIPTION_REGEX, description):
        raise Exception("company_ex description contains invalid characters")
    return description


def validate_item_address():
    address = request.form.get("item_address", "").strip()
    if len(address) < 5 or len(address) > 100:
        raise Exception("company_ex address must be between 5 and 100 characters")
    if not re.match(ITEM_ADDRESS_REGEX, address):
        raise Exception("company_ex address contains invalid characters")
    return address


def validate_item_price():
    price = request.form.get("item_price", "").strip()
    if not re.match(ITEM_PRICE_REGEX, price):
        raise Exception("company_ex price must be a number with up to 2 decimals")
    return float(price)


def validate_item_lat():
    lat = request.form.get("item_lat", "").strip()
    if not re.match(ITEM_LAT_REGEX, lat):
        raise Exception("company_ex latitude is invalid")
    return float(lat)


def validate_item_lon():
    lon = request.form.get("item_lon", "").strip()
    if not re.match(ITEM_LON_REGEX, lon):
        raise Exception("company_ex longitude is invalid")
    return float(lon)

############################## image validation
ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg", "gif"]
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB - size in bytes
MAX_IMAGES_PER_ITEM = 3

def validate_item_images():
    images_names = []
    if "files" not in request.files:
        raise Exception("company_ex at least one file")
    
    files = request.files.getlist('files')
    
    # TODO: Fix the validation for 0 files
    # if not files == [None]:
    #     raise Exception("company_ex at least one file")  

    if len(files) > MAX_IMAGES_PER_ITEM:
        raise Exception("company_ex max 3 images per item")

    for the_file in files:
        file_size = len(the_file.read()) # size is in bytes                 
        file_name, file_extension = os.path.splitext(the_file.filename)
        the_file.seek(0)
        file_extension = file_extension.lstrip(".")
        if file_extension not in ALLOWED_EXTENSIONS:
            raise Exception("company_ex file extension not allowed")  
        if file_size > MAX_FILE_SIZE:
            raise Exception("company_ex file too large")  
        new_file_name = f"{uuid.uuid4().hex}.{file_extension}"
        images_names.append(new_file_name)
        file_path = os.path.join("static/uploads", new_file_name)
        the_file.save(file_path) 
        
    return images_names

##############################
REGEX_PAGE_NUMBER = "^[1-9][0-9]*$"
def validate_page_number(page_number):
    error = "company_ex page number"
    page_number = page_number.strip()
    if not re.match(REGEX_PAGE_NUMBER, page_number): raise Exception(error)
    return int(page_number)

##############################
def validate_user_logged():
    if not session.get("user"): raise Exception("compay_ex user not logged")
    return session.get("user")

##############################
# Signup validation
def validate_user_username():
    value = request.form.get("user_username", "").strip()
    if not re.match(r"^.{2,20}$", value):
        raise Exception("username must be 2-20 characters")
    return value

def validate_user_name():
    value = request.form.get("user_name", "").strip()
    if not re.match(r"^.{2,20}$", value):
        raise Exception("first name must be 2-20 characters")
    return value

def validate_user_last_name():
    value = request.form.get("user_last_name", "").strip()
    if not re.match(r"^.{2,20}$", value):
        raise Exception("last name must be 2-20 characters")
    return value

def validate_user_email():
    value = request.form.get("user_email", "").strip()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
        raise Exception("invalid email")
    return value

def validate_user_password():
    value = request.form.get("user_password", "").strip()
    if not (2 <= len(value) <= 20):
        raise Exception("password must be 2-20 characters")
    return value

##############################
#search validation
def validate_search_query(q):
    if len(q) > 50: raise Exception("Query too long")
    return q.strip()

##############################
#Email - Account created
def send_email(user_name, user_last_name, user_email, user_verification_key):
    verification_link = f"http://localhost/verify/{user_verification_key}"
    html_body = f"""
    <p>Thank you {user_name} {user_last_name} for signing up. Please verify your account by clicking the link below:</p>
    <p><a href="{verification_link}">Verify your email</a></p>
    """
    send_email_template(user_email, "Welcome", html_body)

##############################
def send_email_template(receiver_email, subject, html_body):
    try:
        message = MIMEMultipart()
        message["From"] = "SkateSpot Company"
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())

        ic(f"Email sent successfully to {receiver_email} with subject '{subject}'")

    except Exception as ex:
        ic(ex)
        raise Exception("Could not send email")

##############################
#Email - Reset password
def send_reset_email(user_email, reset_key):
    reset_link = f"http://localhost/reset-password/{reset_key}"
    html_body = f"""
    <p>We received a request to reset your password.</p>
    <p>Click the link below to choose a new one:</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>If you didn't request a password reset, just ignore this email.</p>
    """
    send_email_template(user_email, "Reset your password", html_body)


##############################
#Email - Delete account
def send_delete_confirmation(user_email):
    html_body = """
    <p>Your account has been deleted from SkateSpot.</p>
    <p>We're sorry to see you go!</p>
    """
    send_email_template(user_email, "Account deleted", html_body)

##############################
#Email - Account blocked
def send_block_user_email(user_email, user_name):
    html_body = f"""
    <p>Hi {user_name},</p>
    <p>Your account on SkateSpot has been blocked by an administrator. You can no longer log in or interact with the platform.</p>
    <p>If you believe this was a mistake, please contact support.</p>
    """
    send_email_template(user_email, "Your SkateSpot account has been blocked", html_body)


##############################
#Email - Account unblocked
def send_unblock_user_email(user_email, user_name):
    html_body = f"""
    <p>Hi {user_name},</p>
    <p>Your account on SkateSpot has been unblocked. You can now log in and use the platform again.</p>
    """
    send_email_template(user_email, "Your SkateSpot account has been unblocked", html_body)


##############################
#Email - Item blocked
def send_block_item_email(user_email, user_name, item_name):
    html_body = f"""
    <p>Hi {user_name},</p>
    <p>Your spot <strong>{item_name}</strong> has been blocked by an administrator and is no longer visible.</p>
    <p>If you believe this was a mistake, please contact support.</p>
    """
    send_email_template(user_email, f"Your spot '{item_name}' has been blocked", html_body)


##############################
#Email - Item unblocked
def send_unblock_item_email(user_email, user_name, item_name):
    html_body = f"""
    <p>Hi {user_name},</p>
    <p>Your spot <strong>{item_name}</strong> has been unblocked and is now visible on the platform again.</p>
    """
    send_email_template(user_email, f"Your spot '{item_name}' has been unblocked", html_body)
