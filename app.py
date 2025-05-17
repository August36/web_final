from flask import Flask, g, render_template, session, request, redirect, url_for, jsonify
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
@app.before_request
def before_request():
    g.is_session = "user" in session

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
        WHERE item_blocked_at = 0
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
        q_item = "SELECT * FROM items WHERE item_pk = %s AND item_blocked_at = 0"
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
@app.post("/item")
def post_item():
    try:
        user = x.validate_user_logged()
        validators = [
            ("item_name",        x.validate_item_name),
            ("item_description", x.validate_item_description),
            ("item_price",       x.validate_item_price),
            ("item_lat",         x.validate_item_lat),
            ("item_lon",         x.validate_item_lon),
            ("item_address",     x.validate_item_address),
            ("files",            x.validate_item_images),
        ]

        values, form_errors = {}, {}
        for field, fn in validators:
            try:
                values[field] = fn()
            except Exception as ex:
                form_errors[field] = str(ex)

        if form_errors:
            error_html = (
                "<ul class='error-list'>"
                + "".join(f"<li>{msg}</li>" for msg in form_errors.values())
                + "</ul>"
            )
            return f"""
            <mixhtml mix-update="#form-errors">
              {error_html}
            </mixhtml>
            """

        db, cursor = x.db()
        item_created_at = int(time.time())

        cursor.execute(
            """
            INSERT INTO items (
                item_name, item_description, item_price,
                item_lat, item_lon, item_address,
                item_user_fk, item_created_at, item_updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                values["item_name"],
                values["item_description"],
                values["item_price"],
                values["item_lat"],
                values["item_lon"],
                values["item_address"],
                user["user_pk"],
                item_created_at,
                0,
            ),
        )
        item_pk = cursor.lastrowid

        images, value_rows = [], []
        for image_name in values["files"]:
            image_pk = uuid.uuid4().hex
            images.append({"image_pk": image_pk, "image_name": image_name})
            value_rows.append(
                f"('{image_pk}', '{user['user_pk']}', '{item_pk}', '{image_name}')"
            )

        if value_rows:
            cursor.execute(
                f"""
                INSERT INTO images (
                    image_pk, image_user_fk, image_item_fk, image_name
                ) VALUES {','.join(value_rows)}
                """
            )

        db.commit()

        item_html = f"""
        <div class="item-card" id="x{item_pk}">
            <h3>{values['item_name']}</h3>
            <p><strong>Price:</strong> {values['item_price']} DKK</p>
            <p><strong>Address:</strong> {values['item_address']}</p>
            <p>{values['item_description']}</p>
            <div class="item-images">
        """
        for img in images:
            item_html += f"""
                <div id="x{img['image_pk']}">
                    <img class="uploaded_imgs_profile"
                         src="/static/uploads/{img['image_name']}"
                         alt="{img['image_name']}">
                    <button mix-delete="/images/{img['image_pk']}">Delete image</button>
                </div>
            """
        item_html += f"""
            </div>
            <button mix-delete="/items/{item_pk}">Delete item</button>
        </div>
        """

        blank_form_html = """
        <form id="item-form" mix-post="/item" enctype="multipart/form-data">
          <input name="item_name"        type="text"     placeholder="Name"        value="" required>
          <textarea name="item_description" placeholder="Description" required></textarea>
          <input name="item_price"       type="number"   placeholder="Price"       value="" required>
          <input name="item_address"     type="text"     placeholder="Address"     value="" required>
          <input name="item_lat"         type="text"     placeholder="Latitude"    value="" required>
          <input name="item_lon"         type="text"     placeholder="Longitude"   value="" required>
          <input name="files"            type="file"     multiple>
          <button>Upload skate spot</button>
        </form>
        """

        return f"""
        <mixhtml mix-top="#items">
          {item_html}
        </mixhtml>

        <mixhtml mix-update="#item-form">
          {blank_form_html}
        </mixhtml>

        <mixhtml mix-update="#form-errors">
          <!-- tomt ⇒ fjerner fejl / succesbeskeder -->
        </mixhtml>
        """

    except Exception as ex:
        ic(ex)
        return str(ex), 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals():     db.close()

##############################
#Edit item
@app.patch("/items/<item_pk>")
def edit_item(item_pk):
    try:
        user = x.validate_user_logged()
        item_pk = x.validate_item_pk(item_pk)
        validators = [
            ("item_name",        x.validate_item_name),
            ("item_description", x.validate_item_description),
            ("item_price",       x.validate_item_price),
            ("item_lat",         x.validate_item_lat),
            ("item_lon",         x.validate_item_lon),
            ("item_address",     x.validate_item_address),
        ]

        values, form_errors = {}, {}
        for field, fn in validators:
            try:
                values[field] = fn()
            except Exception as ex:
                form_errors[field] = str(ex)

        if form_errors:
            error_html = (
                "<ul class='error-list'>"
                + "".join(f"<li>{msg}</li>" for msg in form_errors.values())
                + "</ul>"
            )
            return f"""
            <mixhtml mix-update="#form-errors-{item_pk}">
                {error_html}
            </mixhtml>
            """

        db, cursor = x.db()

        cursor.execute(
            """
            UPDATE items
            SET item_name = %s,
                item_description = %s,
                item_price = %s,
                item_lat = %s,
                item_lon = %s,
                item_address = %s,
                item_updated_at = %s
            WHERE item_pk = %s AND item_user_fk = %s
            """,
            (
                values["item_name"],
                values["item_description"],
                values["item_price"],
                values["item_lat"],
                values["item_lon"],
                values["item_address"],
                int(time.time()),
                item_pk,
                user["user_pk"],
            ),
        )

        db.commit()

        message = f"""
        <div class="alert success" mix-ttl="3000">
            ✅ Spot updated successfully.
        </div>
        """
        return f"""
        <mixhtml mix-update="#form-errors-{item_pk}">
            {message}
        </mixhtml>
        """

    except Exception as ex:
        ic(ex)
        return str(ex), 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.delete("/images/<image_pk>")
def delete_image(image_pk):
    try:
        image_pk = x.validate_image_pk(image_pk)
        user = x.validate_user_logged()
        db, cursor = x.db()
        q = "DELETE FROM images WHERE image_pk = %s"
        cursor.execute(q, (image_pk,))
        db.commit()

        return f"""<mixhtml mix-remove="#x{image_pk}"></mixhtml>"""
    except Exception as ex:
        ic(ex)
        return ""

##############################
# DELETE CARD
@app.delete("/items/<item_pk>")
def delete_item(item_pk):
    try:
        user = x.validate_user_logged()
        item_pk = x.validate_item_pk(item_pk)
        db, cursor = x.db()

        # Slet billeder tilknyttet item
        q_images = "DELETE FROM images WHERE image_item_fk = %s"
        cursor.execute(q_images, (item_pk,))

        # Slet selve item
        q_item = "DELETE FROM items WHERE item_pk = %s AND item_user_fk = %s"
        cursor.execute(q_item, (item_pk, user["user_pk"]))

        db.commit()

        return f"""<mixhtml mix-remove="#x{item_pk}"></mixhtml>"""
    except Exception as ex:
        ic(ex)
        return ""
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

# *************!!!!!!!!!!Overstående er valideret!!!!!!!!!!!!!!!**********************

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
        WHERE item_blocked_at = 0
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
        verification_key = x.validate_verification_key(verification_key)
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

##############################
@app.get("/login")
def show_login():
    active_login = "active"
    message = request.args.get("message", "")
    return render_template("login.html", title="Login", active_login=active_login, message=message)

##############################
@app.post("/login")
def login():
    try:
        # MUST VALIDATE
        user_email = x.validate_user_email()
        user_password = x.validate_user_password()
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()
        if not user: raise Exception("User not found")
        if not user["user_verified"]:
            return render_template("login.html", title="Login", active_login="active", message="Please verify your email before logging in.")
        if user["user_blocked_at"] != 0:
            return render_template("login.html", title="Login", active_login="active", message="Your account is blocked.")
        if not check_password_hash(user["user_password"], user_password):
            raise Exception("Invalid credentials")
        user.pop("user_password")
        ic(user)
        session["user"] = user
        return redirect(url_for("profile"))
    except Exception as ex:
        ic(ex)
        return str(ex), 400 
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/logout")
def logout():
    session.pop("user")
    return redirect(url_for("show_login"))


##############################
#Admin
@app.get("/admin")
def view_admin():
    try:
        if not session.get("user") or not session["user"].get("user_is_admin"):
            return render_template("login.html", message="You must be an admin.")

        db, cursor = x.db()

        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        cursor.execute("SELECT * FROM items")
        items = cursor.fetchall()

        return render_template("view_admin.html", users=users, items=items)

    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
#Block user med form
@app.patch("/admin/block-user")
def admin_block_user():
    try:
        user_pk = x.validate_user_pk(request.form.get("user_pk", ""))

        db, cursor = x.db()
        q = "UPDATE users SET user_blocked_at = %s WHERE user_pk = %s"
        cursor.execute(q, (int(time.time()), user_pk))
        db.commit()

        # Ny unblock-form med wrapper
        button = f"""
        <div id="user-actions-{user_pk}">
            <form mix-patch="/admin/unblock-user" method="post">
                <input type="hidden" name="user_pk" value="{user_pk}">
                <button class="btn unblock">Unblock</button>
            </form>
        </div>
        """

        # Besked
        message = f"""
        <div class='alert success' mix-ttl="3000">
            ✅ User #{user_pk} has been blocked.
        </div>
        """
        cursor.execute("SELECT user_email, user_name FROM users WHERE user_pk = %s", (user_pk,))
        user = cursor.fetchone()
        if user:
            x.send_block_user_email(user["user_email"], user["user_name"])
        return f"""
        <mixhtml mix-replace="#user-actions-{user_pk}">
            {button}
        </mixhtml>

        <mixhtml mix-update="#user-card-{user_pk} .user-feedback">
            {message}
        </mixhtml>
        """

    except Exception as ex:
        ic(ex)
        return str(ex), 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
#Unblock user
@app.patch("/admin/unblock-user")
def admin_unblock_user():
    try:
        user_pk = x.validate_user_pk(request.form.get("user_pk", ""))

        db, cursor = x.db()
        q = "UPDATE users SET user_blocked_at = 0 WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        db.commit()

        # Ny block-form med wrapper
        button = f"""
        <div id="user-actions-{user_pk}">
            <form mix-patch="/admin/block-user" method="post">
                <input type="hidden" name="user_pk" value="{user_pk}">
                <button class="btn block">Block</button>
            </form>
        </div>
        """

        message = f"""
        <div class='alert success' mix-ttl="3000">
            ✅ User #{user_pk} has been unblocked.
        </div>
        """
        cursor.execute("SELECT user_email, user_name FROM users WHERE user_pk = %s", (user_pk,))
        user = cursor.fetchone()
        if user:
            x.send_unblock_user_email(user["user_email"], user["user_name"])

        return f"""
        <mixhtml mix-replace="#user-actions-{user_pk}">
            {button}
        </mixhtml>

        <mixhtml mix-update="#user-card-{user_pk} .user-feedback">
            {message}
        </mixhtml>
        """

    except Exception as ex:
        ic(ex)
        return str(ex), 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################OVERSTÅENDE ER TJEKKET##########################################################################################


##############################
#Block item
@app.patch("/admin/block-item")
def admin_block_item():
    try:
        item_pk = x.validate_item_pk(request.form.get("item_pk", ""))


        db, cursor = x.db()
        cursor.execute("UPDATE items SET item_blocked_at = %s WHERE item_pk = %s", (int(time.time()), item_pk))
        db.commit()

        button = f"""
        <div id="item-actions-{item_pk}">
            <form mix-patch="/admin/unblock-item" method="post">
                <input type="hidden" name="item_pk" value="{item_pk}">
                <button class="btn unblock">Unblock</button>
            </form>
            <div class="item-feedback"></div>
        </div>
        """

        message = f"""
        <div class='alert success' mix-ttl="3000">
            ✅ Item #{item_pk} has been blocked.
        </div>
        """

        cursor.execute("""
        SELECT users.user_email, users.user_name, items.item_name
        FROM items
        JOIN users ON users.user_pk = items.item_user_fk
        WHERE items.item_pk = %s
        """, (item_pk,))
        data = cursor.fetchone()
        if data:
            x.send_block_item_email(data["user_email"], data["user_name"], data["item_name"])

        return f"""
        <mixhtml mix-replace="#item-actions-{item_pk}">
            {button}
        </mixhtml>
        <mixhtml mix-update="#item-actions-{item_pk} .item-feedback">
            {message}
        </mixhtml>
        """

    except Exception as ex:
        ic(ex)
        return str(ex), 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
#Unblock item
@app.patch("/admin/unblock-item")
def admin_unblock_item():
    try:
        item_pk = x.validate_item_pk(request.form.get("item_pk", ""))


        db, cursor = x.db()
        cursor.execute("UPDATE items SET item_blocked_at = 0 WHERE item_pk = %s", (item_pk,))
        db.commit()

        button = f"""
        <div id="item-actions-{item_pk}">
            <form mix-patch="/admin/block-item" method="post">
                <input type="hidden" name="item_pk" value="{item_pk}">
                <button class="btn block">Block</button>
            </form>
            <div class="item-feedback"></div>
        </div>
        """

        message = f"""
        <div class='alert success' mix-ttl="3000">
            ✅ Item #{item_pk} has been unblocked.
        </div>
        """
        cursor.execute("""
        SELECT users.user_email, users.user_name, items.item_name
        FROM items
        JOIN users ON users.user_pk = items.item_user_fk
        WHERE items.item_pk = %s
        """, (item_pk,))
        data = cursor.fetchone()
        if data:
            x.send_unblock_item_email(data["user_email"], data["user_name"], data["item_name"])


        return f"""
        <mixhtml mix-replace="#item-actions-{item_pk}">
            {button}
        </mixhtml>
        <mixhtml mix-update="#item-actions-{item_pk} .item-feedback">
            {message}
        </mixhtml>
        """

    except Exception as ex:
        ic(ex)
        return str(ex), 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/forgot-password")
def show_forgot_password():
    return render_template("forgot_password.html", old_values={})

##############################
@app.post("/forgot-password")
def forgot_password():
    try:
        user_email = request.form.get("user_email", "").strip()

        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()

        if user:
            reset_key = str(uuid.uuid4())
            now = int(time.time())
            q = "UPDATE users SET user_reset_key = %s, user_reset_requested_at = %s WHERE user_email = %s"
            cursor.execute(q, (reset_key, now, user_email))
            db.commit()
            x.send_reset_email(user_email, reset_key)

        # Vis besked uanset om email findes eller ej
        return render_template("forgot_password.html",
            message="If your email exists, we've sent a reset link.",
            old_values={})

    except Exception as ex:
        return render_template("forgot_password.html",
            message="Something went wrong: " + str(ex),
            old_values=request.form), 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/reset-password/<reset_key>")
def show_reset_form(reset_key):
    return render_template("reset_password.html", reset_key=reset_key)


##############################
@app.post("/reset-password/<reset_key>")
def reset_password(reset_key):
    try:
        try:
            new_password = x.validate_user_password()
        except Exception as ex:
            return render_template("reset_password.html", 
                reset_key=reset_key, 
                message=str(ex),
                user_password_error="input_error")

        db, cursor = x.db()

        q = "SELECT * FROM users WHERE user_reset_key = %s AND user_deleted_at = 0"
        cursor.execute(q, (reset_key,))
        user = cursor.fetchone()

        if not user:
            return render_template("reset_password.html",
                message="Invalid or expired reset link")

        now = int(time.time())
        if user["user_reset_requested_at"] < now - 3600:
            return render_template("reset_password.html",
                message="Reset link has expired. Please request a new one.")

        hashed = generate_password_hash(new_password)
        q = "UPDATE users SET user_password = %s, user_reset_key = NULL, user_reset_requested_at = 0 WHERE user_reset_key = %s"
        cursor.execute(q, (hashed, reset_key))

        if cursor.rowcount != 1:
            return render_template("reset_password.html",
                reset_key=reset_key,
                message="Invalid or expired reset link",
                user_password_error="input_error")

        db.commit()
        return render_template("login.html", message="Password updated. You can now log in.")

    except Exception as ex:
        return f"Site under maintenance: {ex}", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.get("/profile")
def profile():
    try:
        user = x.validate_user_logged()
        db, cursor = x.db()

        q_items = "SELECT * FROM items WHERE item_user_fk = %s AND item_blocked_at = 0 ORDER BY item_created_at DESC"
        cursor.execute(q_items, (user["user_pk"],))
        items = cursor.fetchall()

        for item in items:
            q_images = "SELECT * FROM images WHERE image_item_fk = %s"
            cursor.execute(q_images, (item["item_pk"],))
            item["images"] = cursor.fetchall()

        return render_template(
            "profile.html",
            user=user,
            items=items,
            active_profile="active",
            title="Profile"
        )
    except Exception as ex:
        ic(ex)
        return redirect(url_for("show_login"))
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.get("/profile/edit")
def edit_profile():
    try:
        if "user" not in session:
            return redirect(url_for("show_login"))

        user = session["user"]
        return render_template("edit_profile.html", user=user, old_values=user, message="")

    except Exception as ex:
        return str(ex), 500

##############################
@app.post("/profile/edit")
def update_profile():
    try:
        if "user" not in session:
            return redirect(url_for("show_login"))

        # Hent brugerens id (vi bruger det til UPDATE)
        user_pk = session["user"]["user_pk"]

        # Valider input som ved signup (brug gerne dine eksisterende x.py-funktioner)
        user_username = x.validate_user_username()
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()

        db, cursor = x.db()

        # Opdater brugeren i databasen
        q = """
        UPDATE users
        SET user_username = %s,
            user_name = %s,
            user_last_name = %s,
            user_email = %s,
            user_updated_at = %s
        WHERE user_pk = %s AND user_deleted_at = 0
        """
        cursor.execute(q, (
            user_username, user_name, user_last_name, user_email, int(time.time()), user_pk
        ))
        db.commit()

        # Opdater session med nye oplysninger
        session["user"].update({
            "user_username": user_username,
            "user_name": user_name,
            "user_last_name": user_last_name,
            "user_email": user_email
        })

        return redirect(url_for("profile"))

    except Exception as ex:
        old_values = request.form.to_dict()
        return render_template("edit_profile.html",
            message=str(ex),
            old_values=old_values,
            user=session["user"])

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/profile/delete")
def delete_profile():
    if "user" not in session:
        return redirect(url_for("show_login"))
    return render_template("delete_profile.html", message="", user_password_error="", old_values={})

##############################
@app.post("/profile/delete")
def confirm_delete_profile():
    try:
        if "user" not in session:
            return redirect(url_for("show_login"))

        user_pk = session["user"]["user_pk"]
        user_email = session["user"]["user_email"]
        user_password = request.form.get("user_password", "").strip()

        db, cursor = x.db()

        # Hent brugerens hashede password
        q = "SELECT user_password FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        result = cursor.fetchone()

        if not result or not check_password_hash(result["user_password"], user_password):
            return render_template("delete_profile.html",
            message="Invalid password",
            user_password_error="input_error",
            old_values=request.form)

        #soft delete
        timestamp = int(time.time())
        q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
        cursor.execute(q, (timestamp, user_pk))
        db.commit()

        # send bekræftelsesmail
        x.send_delete_confirmation(user_email)
        session.pop("user", None)
        return redirect(url_for("show_login", message="Your account has been deleted."))

    except Exception as ex:
        return str(ex), 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
#search
@app.get("/search")
def search():
    try:
        search_for = request.args.get("q", "").strip()
        search_for = x.validate_search_query(search_for)

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
        WHERE item_blocked_at = 0 AND item_name LIKE %s
        """
        cursor.execute(q, (f"{search_for}%",))
        rows = cursor.fetchall()
        return jsonify(rows)
    except Exception as ex:
        ic(ex)
        return "x", 400
