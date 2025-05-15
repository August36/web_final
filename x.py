from flask import request, session
import mysql.connector
import re
import os
import uuid


from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)


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
def validate_user_logged():
    if not session.get("user"): raise Exception("compay_ex user not logged")
    return session.get("user")



##############################
USER_NAME_MIN = 2
USER_NAME_MAX = 20
USER_NAME_REGEX = f"^.{{{USER_NAME_MIN},{USER_NAME_MAX}}}$"
def validate_user_name():
    error = "company_ex user_name"
    user_name = request.form.get("user_name", "").strip()
    if not re.match(USER_NAME_REGEX, user_name): raise Exception(error)
    return user_name


##############################
REGEX_PAGE_NUMBER = "^[1-9][0-9]*$"
def validate_page_number(page_number):
    error = "company_ex page number"
    page_number = page_number.strip()
    if not re.match(REGEX_PAGE_NUMBER, page_number): raise Exception(error)
    return int(page_number)


##############################
REGEX_EMAIL = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
def validate_email():
    error = f"company_ex email"
    email = request.form.get("email", "").strip()
    if not re.match(REGEX_EMAIL, email): raise Exception(error)
    return email

##############################
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
