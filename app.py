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
        
        return render_template("view_index.html", title="Skatespots CPH", items=items, images=images), 200

    except Exception as ex:
        ic(ex)
        return "ups", 500

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
        """, 200

    except Exception as ex:
        ic(ex)
        return """
            <mixhtml mix-top="body">
                ups
            </mixhtml>
        """, 500

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
                "<ul class='alert error'>"
                + "".join(f"<li>{msg}</li>" for msg in form_errors.values())
                + "</ul>"
            )
            return f"""
            <mixhtml mix-update="#form-feedback">
              {error_html}
            </mixhtml>
            <mixhtml mix-function="resetButtonText">Upload skate spot</mixhtml>
            """, 400

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

        blank_form_html = render_template("upload_item_form.html", form=None, errors=None)

        return f"""
        <mixhtml mix-replace="#form-feedback">
        <div class='alert success' mix-ttl="3000">
            ✅ Spot uploaded successfully
        </div>
        </mixhtml>

        <mixhtml mix-update="#item-form">
        {blank_form_html}
        </mixhtml>

        <mixhtml mix-after="#items-h2">
        {item_html}
        </mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        return f"""
        <mixhtml mix-update="#form-feedback">
          <div class='alert error'>Something went wrong: {str(ex)}</div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">Upload skate spot</mixhtml>
        """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
#Edit item
@app.post("/items/<item_pk>")
def edit_item_post(item_pk):
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
                "<ul class='alert error'>"
                + "".join(f"<li>{msg}</li>" for msg in form_errors.values())
                + "</ul>"
            )
            return f"""
            <mixhtml mix-update="#form-feedback">
              {error_html}
            </mixhtml>
            <mixhtml mix-function="resetButtonText">Save changes</mixhtml>
            """, 400

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

        return f"""
        <mixhtml mix-redirect="{url_for('profile')}?message=Spot+updated+successfully"></mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        return f"""
        <mixhtml mix-update="#form-feedback">
          <div class='alert error'>Something went wrong: {str(ex)}</div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">Save changes</mixhtml>
        """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
#Edit spot/item page
@app.get("/items/<item_pk>/edit")
def edit_item_page(item_pk):
    try:
        user = x.validate_user_logged()
        item_pk = x.validate_item_pk(item_pk)

        db, cursor = x.db()
        cursor.execute(
            "SELECT * FROM items WHERE item_pk = %s AND item_user_fk = %s", 
            (item_pk, user["user_pk"])
        )
        item = cursor.fetchone()
        if not item:
            raise Exception("Item not found")

        return render_template("edit_item.html", item=item), 200

    except Exception as ex:
        ic(ex)
        return redirect(url_for("profile")), 302

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
#Delete image
@app.delete("/images/<image_pk>")
def delete_image(image_pk):
    try:
        image_pk = x.validate_image_pk(image_pk)
        user = x.validate_user_logged()

        db, cursor = x.db()
        q = "DELETE FROM images WHERE image_pk = %s"
        cursor.execute(q, (image_pk,))
        db.commit()

        return f"""
        <mixhtml mix-remove="#x{image_pk}"></mixhtml>
        <mixhtml mix-update="#image-delete-feedback">
        <div class='alert success' mix-ttl="3000">
            ✅ Image deleted successfully
        </div>
        </mixhtml>
        """, 200


    except Exception as ex:
        ic(ex)
        return "", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


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

        return f"""<mixhtml mix-remove="#x{item_pk}"></mixhtml>""", 200

    except Exception as ex:
        ic(ex)
        return "", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/items/page/<page_number>")
def get_items_by_page(page_number):
    try:
        page_number = x.validate_page_number(page_number)
        items_per_page = 2
        offset = (page_number - 1) * items_per_page
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
            html += render_template("_item_mini.html", item=item)

        button = ""
        if len(items) == extra_item:
            button = render_template("_button_more_items.html", page_number=page_number + 1)

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
        """, 200

    except Exception as ex:
        ic(ex)

        if "company_ex page_number" in str(ex):
            return """
                <mixhtml mix-top="body">
                    page number invalid
                </mixhtml>
            """, 400

        return """
            <mixhtml mix-top="body">
                ups
            </mixhtml>
        """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/signup")
def show_signup():
    active_signup = "active"
    error_message = request.args.get("error_message", "")
    return render_template(
        "signup.html",
        title="signup",
        active_signup=active_signup,
        error_message=error_message,
        old_values={}
    ), 200


##############################
@app.post("/signup")
def signup():
    try:
        user_username  = x.validate_user_username()
        user_name      = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email     = x.validate_user_email()
        user_password  = x.validate_user_password()

        hashed_password = generate_password_hash(user_password)
        user_created_at = int(time.time())
        verification_key = str(uuid.uuid4())

        q = """
        INSERT INTO users 
        (user_pk, user_username, user_name, user_last_name, user_email, 
         user_password, user_created_at, user_updated_at, user_deleted_at,
         user_verified, user_verification_key) 
        VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        db, cursor = x.db()
        cursor.execute(q, (
            user_username, user_name, user_last_name,
            user_email, hashed_password,
            user_created_at, 0, 0, 0, verification_key
        ))

        if cursor.rowcount != 1:
            raise Exception("System under maintenance")

        db.commit()
        x.send_email(user_name, user_last_name, user_email, verification_key)

        return """
        <mixhtml mix-redirect='/login?message=Thank you for signing up. Please verify your email before logging in.'></mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if "username" in str(ex):
            return """
            <mixhtml mix-update="#form-feedback">
              <div class='alert error'>Brugernavn skal være 2–20 tegn og må ikke være i brug.</div>
            </mixhtml>
            """, 400

        if "first name" in str(ex):
            return """
            <mixhtml mix-update="#form-feedback">
              <div class='alert error'>Fornavn skal være 2–20 tegn.</div>
            </mixhtml>
            """, 400

        if "last name" in str(ex):
            return """
            <mixhtml mix-update="#form-feedback">
              <div class='alert error'>Efternavn skal være 2–20 tegn.</div>
            </mixhtml>
            """, 400

        if "Invalid email" in str(ex):
            return """
            <mixhtml mix-update="#form-feedback">
              <div class='alert error'>Ugyldig email.</div>
            </mixhtml>
            """, 400

        if "password" in str(ex):
            return """
            <mixhtml mix-update="#form-feedback">
              <div class='alert error'>Password skal være 2–20 tegn.</div>
            </mixhtml>
            """, 400

        if "user_email" in str(ex):
            return """
            <mixhtml mix-update="#form-feedback">
              <div class='alert error'>Denne email er allerede i brug.</div>
            </mixhtml>
            """, 400

        if "user_username" in str(ex):
            return """
            <mixhtml mix-update="#form-feedback">
              <div class='alert error'>Dette brugernavn er allerede i brug.</div>
            </mixhtml>
            """, 400

        return f"""
        <mixhtml mix-update="#form-feedback">
          <div class='alert error'>Ukendt fejl: {str(ex)}</div>
        </mixhtml>
        """, 400

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
        q = """
        UPDATE users
        SET user_verified = 1,
            user_verification_key = NULL
        WHERE user_verification_key = %s
        """
        cursor.execute(q, (verification_key,))
        db.commit()

        return render_template("login.html", message="Your email is now verified. You can log in."), 200

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
    return render_template(
        "login.html",
        title="Login",
        active_login=active_login,
        message=message
    ), 200

##############################
@app.post("/login")
def login():
    try:
        user_email = x.validate_user_email()
        user_password = x.validate_user_password()

        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()

        if not user:
            raise Exception("User not found")

        if not user["user_verified"]:
            return f"""
            <mixhtml mix-update="#form-feedback">
              <div class='alert error'>Please verify your email before logging in.</div>
            </mixhtml>
            """, 403

        if user["user_blocked_at"] != 0:
            return f"""
            <mixhtml mix-update="#form-feedback">
              <div class='alert error'>Your account is blocked.</div>
            </mixhtml>
            """, 403

        if not check_password_hash(user["user_password"], user_password):
            raise Exception("Invalid credentials")

        user.pop("user_password")
        session["user"] = user
        ic(user)

        return """
        <mixhtml mix-redirect='/profile'></mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        return f"""
        <mixhtml mix-update="#form-feedback">
          <div class='alert error'>{str(ex)}</div>
        </mixhtml>
        """, 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.get("/logout")
def logout():
    session.pop("user")
    return redirect(url_for("show_login")), 302


##############################
#Admin
@app.get("/admin")
def view_admin():
    try:
        if not session.get("user") or not session["user"].get("user_is_admin"):
            return render_template(
                "login.html",
                message="You must be an admin."
            ), 403

        db, cursor = x.db()

        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        cursor.execute("SELECT * FROM items")
        items = cursor.fetchall()

        return render_template(
            "view_admin.html",
            users=users,
            items=items
        ), 200

    except Exception as ex:
        ic(ex)
        return str(ex), 500

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

        button = f"""
        <div id="user-actions-{user_pk}">
            <form mix-patch="/admin/unblock-user" method="post">
                <input type="hidden" name="user_pk" value="{user_pk}">
                <button class="btn unblock">Unblock</button>
            </form>
        </div>
        """

        message = f"""
        <div class='alert success' mix-ttl="3000">
            User #{user_pk} has been blocked.
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
        """, 200

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
        """, 200

    except Exception as ex:
        ic(ex)
        return str(ex), 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


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
        """, 200

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
        """, 200

    except Exception as ex:
        ic(ex)
        return str(ex), 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/forgot-password")
def show_forgot_password():
    return render_template("forgot_password.html", old_values={}), 200

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
            q = """
            UPDATE users
            SET user_reset_key = %s,
                user_reset_requested_at = %s
            WHERE user_email = %s
            """
            cursor.execute(q, (reset_key, now, user_email))
            db.commit()
            x.send_reset_email(user_email, reset_key)

        return render_template(
            "forgot_password.html",
            message="If your email exists, we've sent a reset link.",
            old_values={}
        ), 200

    except Exception as ex:
        return render_template(
            "forgot_password.html",
            message="Something went wrong: " + str(ex),
            old_values=request.form
        ), 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/reset-password/<reset_key>")
def show_reset_form(reset_key):
    return render_template("reset_password.html", reset_key=reset_key), 200

##############################
@app.post("/reset-password/<reset_key>")
def reset_password(reset_key):
    try:
        try:
            new_password = x.validate_user_password()
        except Exception as ex:
            return render_template(
                "reset_password.html",
                reset_key=reset_key,
                message=str(ex),
                user_password_error="input_error"
            ), 400

        db, cursor = x.db()

        q = "SELECT * FROM users WHERE user_reset_key = %s AND user_deleted_at = 0"
        cursor.execute(q, (reset_key,))
        user = cursor.fetchone()

        if not user:
            return render_template(
                "reset_password.html",
                message="Invalid or expired reset link"
            ), 403

        now = int(time.time())
        if user["user_reset_requested_at"] < now - 3600:
            return render_template(
                "reset_password.html",
                message="Reset link has expired. Please request a new one."
            ), 403

        hashed = generate_password_hash(new_password)

        q = """
        UPDATE users
        SET user_password = %s,
            user_reset_key = NULL,
            user_reset_requested_at = 0
        WHERE user_reset_key = %s
        """
        cursor.execute(q, (hashed, reset_key))

        if cursor.rowcount != 1:
            return render_template(
                "reset_password.html",
                reset_key=reset_key,
                message="Invalid or expired reset link",
                user_password_error="input_error"
            ), 403

        db.commit()
        return render_template(
            "login.html",
            message="Password updated. You can now log in."
        ), 200

    except Exception as ex:
        return f"Site under maintenance: {ex}", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/profile")
def profile():
    try:
        user = x.validate_user_logged()
        message = request.args.get("message", "")

        db, cursor = x.db()

        q_items = """
        SELECT * FROM items
        WHERE item_user_fk = %s AND item_blocked_at = 0
        ORDER BY item_created_at DESC
        """
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
            title="Profile",
            form=None,
            errors=None,
            message=message
        ), 200

    except Exception as ex:
        ic(ex)
        return redirect(url_for("show_login")), 302

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/profile/edit")
def edit_profile():
    try:
        if "user" not in session:
            return redirect(url_for("show_login")), 302

        user = session["user"]
        return render_template(
            "edit_profile.html",
            user=user,
            old_values=user,
            message=""
        ), 200

    except Exception as ex:
        return str(ex), 500

##############################
@app.post("/profile/edit")
def update_profile():
    try:
        if "user" not in session:
            return redirect(url_for("show_login")), 302

        user_pk = session["user"]["user_pk"]

        # Valider input
        user_username = x.validate_user_username()
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()

        db, cursor = x.db()

        cursor.execute("""
        UPDATE users
        SET user_username = %s,
            user_name = %s,
            user_last_name = %s,
            user_email = %s,
            user_updated_at = %s
        WHERE user_pk = %s AND user_deleted_at = 0
        """, (
            user_username,
            user_name,
            user_last_name,
            user_email,
            int(time.time()),
            user_pk
        ))
        db.commit()

        # Opdater session
        session["user"].update({
            "user_username": user_username,
            "user_name": user_name,
            "user_last_name": user_last_name,
            "user_email": user_email
        })

        return redirect(url_for("profile")), 302

    except Exception as ex:
        old_values = request.form.to_dict()
        return render_template(
            "edit_profile.html",
            message=str(ex),
            old_values=old_values,
            user=session["user"]
        ), 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/profile/delete")
def delete_profile():
    if "user" not in session:
        return redirect(url_for("show_login")), 302

    return render_template(
        "delete_profile.html",
        message="",
        user_password_error="",
        old_values={}
    ), 200

##############################
@app.post("/profile/delete")
def confirm_delete_profile():
    try:
        if "user" not in session:
            return redirect(url_for("show_login")), 302

        user_pk = session["user"]["user_pk"]
        user_email = session["user"]["user_email"]
        user_password = request.form.get("user_password", "").strip()

        db, cursor = x.db()

        # Tjek password
        q = "SELECT user_password FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        result = cursor.fetchone()

        if not result or not check_password_hash(result["user_password"], user_password):
            return render_template(
                "delete_profile.html",
                message="Invalid password",
                user_password_error="input_error",
                old_values=request.form
            ), 403

        # Soft delete
        timestamp = int(time.time())
        q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
        cursor.execute(q, (timestamp, user_pk))
        db.commit()

        x.send_delete_confirmation(user_email)
        session.pop("user", None)

        return redirect(url_for("show_login", message="Your account has been deleted.")), 302

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
        return jsonify(rows), 200

    except Exception as ex:
        ic(ex)
        return "x", 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
