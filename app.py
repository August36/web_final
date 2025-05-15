from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
import x
from werkzeug.security import generate_password_hash, check_password_hash
import time
import uuid
import os
import json

from icecream import ic
ic.configureOutput(prefix=f'!x!app.py!x! | ', includeContext=True)

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

##############################
@app.after_request
def disable_cache(response):
    """
    This function automatically disables caching for all responses.
    It is applied after every request to the server.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

##############################
@app.get("/")
def view_index():
    try:
        db, cursor = x.db()
        q = """
        SELECT items.*, (
            SELECT image_name
            FROM images
            WHERE images.image_item_fk = items.item_pk
            ORDER BY image_pk ASC
            LIMIT 1
        ) AS item_image
        FROM items
        ORDER BY item_created_at
        LIMIT 2
        """
        cursor.execute(q)
        items = cursor.fetchall()

        images = []
        if items:
            q_images = "SELECT * FROM images WHERE image_item_fk = %s"
            cursor.execute(q_images, (items[0]["item_pk"],))
            images = cursor.fetchall()
        
        return render_template("view_index.html", title="Skatespots CPH", items=items, images=images)

    except Exception as ex:
        ic(ex)
        return "ups"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/items/<item_pk>")
def get_item_by_pk(item_pk):
    try:
        db, cursor = x.db()

        # Hent selve item
        q_item = "SELECT * FROM items WHERE item_pk = %s"
        cursor.execute(q_item, (item_pk,))
        item = cursor.fetchone()

        # Hent billeder til item
        q_images = "SELECT * FROM images WHERE image_item_fk = %s"
        cursor.execute(q_images, (item_pk,))
        images = cursor.fetchall()

        html_item = render_template("_item.html", item=item, images=images)

        return f"""
            <mixhtml mix-replace="#item">
                {html_item}
            </mixhtml>
        """
    except Exception as ex:
        ic(ex)
        return """
            <mixhtml mix-top="body">
                ups
            </mixhtml>
        """
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/items/page/<page_number>")
def get_items_by_page(page_number):
    try:
        page_number = x.validate_page_number(page_number)
        items_per_page = 2
        offset = (page_number-1) * items_per_page
        extra_item = items_per_page + 1

        db, cursor = x.db()
        q = """
        SELECT items.*, (
            SELECT image_name
            FROM images
            WHERE images.image_item_fk = items.item_pk
            ORDER BY image_pk ASC
            LIMIT 1
        ) AS item_image
        FROM items
        ORDER BY item_created_at
        LIMIT %s OFFSET %s
        """
        cursor.execute(q, (extra_item, offset))
        items = cursor.fetchall()


        html = ""

        for item in items[:items_per_page]:
            i = render_template("_item_mini.html", item=item)
            html += i
        
        button = render_template("_button_more_items.html", page_number=page_number + 1)

        if len(items) < extra_item: button = ""

        return f"""
            <mixhtml mix-bottom="#items">
                {html}
            </mixhtml>
            <mixhtml mix-replace="#button_more_items">
                {button}
            </mixhtml>
            <mixhtml mix-function="add_markers_to_map">
                {json.dumps(items[:items_per_page], default=str)}
            </mixhtml>
        """
    except Exception as ex:
        ic(ex)
        if "company_ex page_number" in str(ex):
            return """
                <mixhtml mix-top="body">
                    page number invalid
                </mixhtml>
            """

        return """
            <mixhtml mix-top="body">
                ups
            </mixhtml>
        """

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/signup")
def show_signup():
        active_signup = "active"
        error_message = request.args.get("error_message", "")
        return render_template("signup.html", title="signup", active_signup=active_signup, error_message=error_message, old_values={})

##############################
@app.post("/signup")        
def signup():
    try:
        # vi validere username med funktion fra x filen som indeholder regex.
        user_username = x.validate_user_username()
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()
        user_password = x.validate_user_password()
        hashed_password = generate_password_hash(user_password)
        # ic(hashed_password)
        user_created_at = int(time.time())
        verification_key = str(uuid.uuid4())

        # query der sender form dataen til databasen. user_pk er null da den auto oprettes i databasen.
        # i python bruges """ til at lave multi line strings
        q = """INSERT INTO users 
        (user_pk, user_username, user_name, user_last_name, user_email, 
        user_password, user_created_at, user_updated_at, user_deleted_at, user_verified, user_verification_key) 
        VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        db, cursor = x.db()
        cursor.execute(q, (user_username, user_name, user_last_name, user_email, hashed_password, user_created_at, 0, 0, 0, verification_key))

        # Denne linje tjekker om præcis en række er oprettet. Hvis 0 rækker oprettes, fx fordi email allerede eksistere i databasen og INSERT afvises, vises fejlbeskeden
        if cursor.rowcount != 1: 
            raise Exception("System under maintenance")
        
        db.commit()
        x.send_email(user_name, user_last_name, user_email, verification_key)
        # hvis alt er korrekt - redirectes til login siden.
        return redirect(url_for("show_login", message="Thank you for signing up. A verification email has been sent to your inbox. Please click the link in the email to verify your account before logging in."))
    except Exception as ex:
        ic(ex)

        # Locals er et indbygget python dictionary, som indeholder alle variabler der er lavet i det lokale scope (i signup funktionen).
        # Locals = "Vis mig alle variabler, vi har lavet i denne funktion lige nu."
        # Så hvis brugeren sender forkert data så laves database forbindelsen ikke, og db vil ikke være en del af dictionaryiet.
        # Men hvis brugeren sender korrekt data og vi når at lave db forbindelsen, så findes db i dictionariet og hvis der går noget galt laver vi et rollback
        # Så det er bare en sikkerhedsforanstaltning, der laver en rollback hvis der opstår en fejl i transaktionen
        # Så det er basically for at lave et rollback, hvis der sker en fejl som fx: serveren mister forbindelsen mid i signup eller hvis databasen er løbet tør for plads
        if "db" in locals():
            db.rollback()

        # Tag alle input-felter, som brugeren har sendt med formen, og lav dem om til et dictionary, som gemmes i old_values variablen.
        # Senere i koden indsættes disse værdier så igen i de inputs hvor der ikke var fejl, så brugeren ikke skal skrive dem igen.
        old_values = request.form.to_dict()
        # ex er fejlbeskeden, og vi laver fejlbeskeden om til string og tjekker om "username" er i stringen, for at kunne afgøre om det var her fejlen skete.
        if "username" in str(ex):
            # Hvis det var i username feltet at fejlen skete, bruger vi pop til at fjerne det brugeren har indtastet, så dette felt bliver tomt og de kan prøve igen
            old_values.pop("user_username", None)
            # Hvis fejlen skete her, rendere siden igen, fejlbeskeden vises og old values indsættes i de felter hvor der ikke var fejl.
            return render_template("signup.html",                                   
                error_message="Invalid username", old_values=old_values, user_username_error="input_error")
        if "first name" in str(ex):
            old_values.pop("user_name", None)
            return render_template("signup.html",
                error_message="Invalid name", old_values=old_values, user_name_error="input_error")
        if "last name" in str(ex):
            old_values.pop("user_last_name", None)
            return render_template("signup.html",
                error_message="Invalid last name", old_values=old_values, user_last_name_error="input_error")
        if "Invalid email" in str(ex):
            old_values.pop("user_email", None)
            return render_template("signup.html",
                error_message="Invalid email", old_values=old_values, user_email_error="input_error")
        if "password" in str(ex):
            old_values.pop("user_password", None)
            return render_template("signup.html",
                error_message="Invalid password", old_values=old_values, user_password_error="input_error")

        if "user_email" in str(ex):
            return redirect(url_for("show_signup",
                error_message="Email already exists", old_values=old_values, email_error=True))
        if "user_username" in str(ex): 
            return redirect(url_for("show_signup", 
                error_message="Username already exists", old_values=request.form, user_username_error=True))
        return redirect(url_for("show_signup", error_message=ex.args[0]))
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/verify/<verification_key>")
def verify_user(verification_key):
    try:
        db, cursor = x.db()

        # Tjek om en bruger med denne nøgle findes og ikke allerede er verificeret
        q = "SELECT * FROM users WHERE user_verification_key = %s AND user_verified = 0"
        cursor.execute(q, (verification_key,))
        user = cursor.fetchone()

        if not user:
            return "Verification key is invalid or already in use", 400

        # Opdater brugeren til at være verificeret og slet nøglen
        q = "UPDATE users SET user_verified = 1, user_verification_key = NULL WHERE user_verification_key = %s"
        cursor.execute(q, (verification_key,))
        db.commit()

        return render_template("login.html", message="Your email is now verified. You can log in.")
    except Exception as ex:
        return str(ex), 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

