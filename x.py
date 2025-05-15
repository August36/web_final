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
# Item validation
ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg", "gif"]
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB - size in bytes
MAX_FILES = 5

def validate_item_images():
    images_names = []
    if "files" not in request.files:
         raise Exception("company_ex at least one file")
    
    files = request.files.getlist('files')
    
    # TODO: Fix the validation for 0 files
    # if not files == [None]:
    #     raise Exception("company_ex at least one file")  
       
    if len(files) > MAX_FILES:
        raise Exception("company_ex max 5 files")

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
#Verification mails

def send_email(user_name, user_last_name, user_email, user_verification_key):
    verification_link = f"http://localhost/verify/{user_verification_key}"
    html_body = f"""
    <p>Thank you {user_name} {user_last_name} for signing up. Please verify your account by clicking the link below:</p>
    <p><a href="{verification_link}">Verify your email</a></p>
    """
    send_email_template(user_email, "Welcome", html_body)

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