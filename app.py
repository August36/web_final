from flask import Flask, g, render_template, session, request, redirect, url_for, jsonify
from flask_session import Session
import x
from werkzeug.security import generate_password_hash, check_password_hash
import time
import uuid
import os
import json
import re
import requests
import languages
from datetime import datetime

from icecream import ic
ic.configureOutput(prefix=f'!x!app.py!x! | ', includeContext=True)

#SPØRGSMÅL JEG FIK TIL EKSAMEN - få styr på disse i løbet af sommerferien samt øv dig på andre spørgsmål:
# - Få show more button til at vise 4 items i stedet for 2
# - Byg ny test route som viser en variabel med dit navn - tror han ville have at navnet skulle medsendes i url'en, så variablen skulle trækkes ned der fra
# - Lav en list og render den med et for loop i html'en.
# - Hvad er cache og hvordan virker den funktion der fjerner cache under udvikling.

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

##############################
@app.before_request
def before_request():
    g.is_session = "user" in session

##############################
# ***rates***
@app.get("/rates")
def get_rates():
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/usd")
        data = response.json()

        with open("rates.txt", "w") as file:
            file.write(response.text)

        return {
            "status": "success",
            "base": data.get("base"),
            "date": data.get("date")
        }
    except Exception as ex:
        return {
            "status": "error",
            "message": str(ex)
        }, 500

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
# ***Format unix timestamp***
@app.template_filter('datetimeformat')
def datetimeformat(value, format="%d.%m.%Y"):
    return datetime.fromtimestamp(value).strftime(format)

##############################
# ***index***
@app.get("/")
@app.get("/<lan>")
def view_index(lan="en"):
    try:
        #Henter data og ét billede til de to første items
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"
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

        #Henter alle billeder til det første item i items - angives med items[0] - dette item bliver renderet i højre column via _item.html.
        images = []
        if items:
            q_images = "SELECT * FROM images WHERE image_item_fk = %s"
            cursor.execute(q_images, (items[0]["item_pk"],))
            images = cursor.fetchall()

        rates = {}
        with open("rates.txt", "r") as file:
            rates = json.loads(file.read())
        
        return render_template("view_index.html", title="Skatespots CPH", items=items, images=images, rates=rates, lan=lan, languages=languages), 200

    except Exception as ex:
        ic(ex)
        return "ups", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***item get***
@app.get("/items/<item_pk>")
@app.get("/items/<item_pk>/<lan>")
def get_item_by_pk(item_pk, lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        db, cursor = x.db()

        # Hent selve item
        q_item = "SELECT * FROM items WHERE item_pk = %s AND item_blocked_at = 0"
        cursor.execute(q_item, (item_pk,))
        item = cursor.fetchone()

        # Hent billeder til item
        q_images = "SELECT * FROM images WHERE image_item_fk = %s"
        cursor.execute(q_images, (item_pk,))
        images = cursor.fetchall()

        rates = {}
        with open("rates.txt", "r") as file:
            rates = json.loads(file.read())

        html_item = render_template("_item.html", item=item, images=images, rates=rates, lan=lan, languages=languages, request=request)

        return f"""
            <mixhtml mix-replace="#item">
                {html_item}
            </mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        return f"""
            <mixhtml mix-top="body">
                {getattr(languages, f"{lan}_dry_unknown_error")}
            </mixhtml>
        """, 500

##############################
# ***item pagination***
@app.get("/items/page/<page_number>")
@app.get("/items/page/<page_number>/<lan>")
def get_items_by_page(page_number, lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

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

        rates = {}
        with open("rates.txt", "r") as file:
            rates = json.loads(file.read())

        html = ""
        for item in items[:items_per_page]:
            html += render_template("_item_mini.html", item=item, rates=rates, lan=lan, languages=languages)

        button = ""
        if len(items) == extra_item:
            button = render_template("_button_more_items.html", page_number=page_number + 1, lan=lan, languages=languages)

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

        if "skatespots_ex page_number" in str(ex):
            return f"""
                <mixhtml mix-top="body">
                    {getattr(languages, f"{lan}_pagination_invalid_page")}
                </mixhtml>
            """, 400

        return f"""
            <mixhtml mix-top="body">
                {getattr(languages, f"{lan}_dry_unknown_error")}
            </mixhtml>
        """, 500

##############################
# ***item post***
# @app.post("/item/<lan>")
# def post_item(lan):
#     try:
#         languages_allowed = ["en", "dk"]
#         if lan not in languages_allowed: lan = "en"

#         user = x.validate_user_logged()

#         validators = [
#             ("item_name",        x.validate_item_name),
#             ("item_description", x.validate_item_description),
#             ("item_price",       x.validate_item_price),
#             ("item_lat",         x.validate_item_lat),
#             ("item_lon",         x.validate_item_lon),
#             ("item_address",     x.validate_item_address),
#             ("files",            x.validate_item_images),
#         ]

#         values, form_errors = {}, {}
#         for field, fn in validators:
#             try:
#                 values[field] = fn()
#             except Exception as ex:
#                 form_errors[field] = str(ex)

#         if form_errors:
#             error_html = (
#                 "<ul class='alert error'>"
#                 + "".join(f"<li>{msg}</li>" for msg in form_errors.values())
#                 + "</ul>"
#             )
#             return f"""
#             <mixhtml mix-update=".form-feedback">
#               {error_html}
#             </mixhtml>
#             <mixhtml mix-function="resetButtonText">
#               {getattr(languages, f"{lan}_upload_item_button_default")}
#             </mixhtml>
#             """, 400

#         db, cursor = x.db()
#         item_created_at = int(time.time())

#         cursor.execute(
#             """
#             INSERT INTO items (
#                 item_name, item_description, item_price,
#                 item_lat, item_lon, item_address,
#                 item_user_fk, item_created_at, item_updated_at
#             ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """,
#             (
#                 values["item_name"],
#                 values["item_description"],
#                 values["item_price"],
#                 values["item_lat"],
#                 values["item_lon"],
#                 values["item_address"],
#                 user["user_pk"],
#                 item_created_at,
#                 0,
#             ),
#         )
#         item_pk = cursor.lastrowid

#         images, value_rows = [], []
#         for image_name in values["files"]:
#             image_pk = uuid.uuid4().hex
#             images.append({"image_pk": image_pk, "image_name": image_name})
#             value_rows.append(
#                 f"('{image_pk}', '{user['user_pk']}', '{item_pk}', '{image_name}')"
#             )

#         if value_rows:
#             cursor.execute(
#                 f"""
#                 INSERT INTO images (
#                     image_pk, image_user_fk, image_item_fk, image_name
#                 ) VALUES {','.join(value_rows)}
#                 """
#             )

#         db.commit()

#         item_html = f"""
#         <div class="item-card" id="x{item_pk}">
#             <h3>{values['item_name']}</h3>
#             <p><strong>{getattr(languages, f"{lan}_dry_price")}</strong> {values['item_price']} DKK</p>
#             <p><strong>{getattr(languages, f"{lan}_dry_address")}</strong> {values['item_address']}</p>
#             <p>{values['item_description']}</p>

#             <a href="/items/{item_pk}/edit/{lan}">{getattr(languages, f"{lan}_profile_edit_spot")}</a>
#             <button mix-delete="/items/{item_pk}/{lan}">{getattr(languages, f"{lan}_profile_delete_item_btn")} {values['item_name']}</button>

#             <div class="item-images">
#         """
#         for img in images:
#             item_html += f"""
#                 <div id="x{img['image_pk']}">
#                     <img class="uploaded_imgs_profile"
#                          src="/static/uploads/{img['image_name']}"
#                          alt="{img['image_name']}">
#                 </div>
#             """
#         item_html += "</div></div>"

#         blank_form_html = render_template(
#             "upload_item_form.html",
#             form=None,
#             errors=None,
#             lan=lan,
#             languages=languages
#         )

#         return f"""
#         <mixhtml mix-after="#item-form">
#           <div class='alert success' mix-ttl="3000">
#             {getattr(languages, f"{lan}_upload_item_success")}
#           </div>
#         </mixhtml>

#         <mixhtml mix-update="#item-form">
#           {blank_form_html}
#         </mixhtml>

#         <mixhtml mix-after="#items-h2">
#           {item_html}
#         </mixhtml>
#         """, 200

#     except Exception as ex:
#         ic(ex)
#         return f"""
#         <mixhtml mix-update=".form-feedback">
#           <div class='alert error'>{getattr(languages, f"{lan}_upload_item_error").replace("{str(ex)}", str(ex))}</div>
#         </mixhtml>
#         <mixhtml mix-function="resetButtonText">
#           {getattr(languages, f"{lan}_upload_item_button_default")}
#         </mixhtml>
#         """, 500

#     finally:
#         if "cursor" in locals(): cursor.close()
#         if "db" in locals(): db.close()


##############################
#***FORBEDRET TIL MUNDTLIG EKSAMEN***
# --- SIKKERHED OG SQL-INJEKTION VED INSERT AF BILLEDER ---

# I min tidligere løsning blev billeddata indsat i databasen ved at opbygge en SQL-streng manuelt:
# Jeg brugte .join() til at sammenkæde værdier som denne:
#
#   value_rows.append(f"('{image_pk}', '{user_pk}', '{item_pk}', '{image_name}')")
#   ...
#   cursor.execute("INSERT INTO images (...) VALUES " + ','.join(value_rows))
#
# Dette virker, men er ikke sikkert, fordi brugerinput (her: image_name) teknisk set bliver flettet direkte
# ind i SQL-strengen. Det betyder, at hvis et felt indeholder ondsindet SQL (fx "'); DROP TABLE users; --"),
# kunne det potentielt udføres som en del af kommandoen. Dette kaldes en SQL-injektion.

# I min billedvalidering bruger jeg dog en vigtig sikkerhedsforanstaltning:
# Jeg gemmer aldrig det oprindelige filnavn fra brugeren i databasen.
# I stedet genererer jeg et nyt unikt filnavn ved at kombinere et UUID med filens tilladte extension:
#
#   new_file_name = f"{uuid.uuid4().hex}.{file_extension}"
#
# Det betyder, at selv hvis en bruger uploader en fil med skadeligt navn, bliver det ikke brugt.
# Kun den sikre og kontrollerede UUID-baserede filnavn gemmes. Dermed reduceres risikoen betydeligt.

# MEN: Selvom inputtet er sikkert i praksis, er det stadig dårlig praksis at bygge SQL-strenge manuelt.
# Hvis jeg i fremtiden ændrer valideringsfunktionen og fx genbruger dele af det originale filnavn,
# risikerer jeg at introducere en sårbarhed uden at opdage det.

# Derfor har jeg ændret koden til at bruge cursor.executemany(), som er en sikker og anbefalet metode.
# Med executemany() bruger jeg en parameteriseret SQL-query med %s som pladsholdere, og indsætter data som tuples:
#
#   image_values = [
#       (image_pk, user_pk, item_pk, image_name),
#       ...
#   ]
#   cursor.executemany("INSERT INTO images (...) VALUES (%s, %s, %s, %s)", image_values)
#
# Fordele ved denne metode:
# - Adskiller data fra SQL-kode
# - Beskytter automatisk mod SQL-injektion
# - Gør det lettere at vedligeholde og fremtidssikre koden

# Samlet konklusion:
# Selvom validering af input gør løsningen robust, er den kun rigtig sikker, hvis man aldrig manuelt indsætter data
# i SQL-strenge. Ved at skifte til executemany() opnår jeg en løsning, der er både sikker, korrekt og best practice.
# ***item post***
@app.post("/item/<lan>")
def post_item(lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

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
            <mixhtml mix-update=".form-feedback">
              {error_html}
            </mixhtml>
            <mixhtml mix-function="resetButtonText">
              {getattr(languages, f"{lan}_upload_item_button_default")}
            </mixhtml>
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

        #***FORBEDRET TIL MUNDTLIG EKSAMEN***
        # Her genererer vi billeddata og opbygger en liste af tuples, som vi sender til executemany
        images = []
        images_to_insert = []

        for image_name in values["files"]:
            image_pk = uuid.uuid4().hex
            images.append({"image_pk": image_pk, "image_name": image_name})
            images_to_insert.append(
                (image_pk, user["user_pk"], item_pk, image_name)
            )

        if images_to_insert:
            cursor.executemany(
                """
                INSERT INTO images (
                    image_pk, image_user_fk, image_item_fk, image_name
                ) VALUES (%s, %s, %s, %s)
                """,
                images_to_insert
            )

        db.commit()

        item_html = f"""
        <div class="item-card" id="x{item_pk}">
            <h3>{values['item_name']}</h3>
            <p><strong>{getattr(languages, f"{lan}_dry_price")}</strong> {values['item_price']} DKK</p>
            <p><strong>{getattr(languages, f"{lan}_dry_address")}</strong> {values['item_address']}</p>
            <p>{values['item_description']}</p>

            <a href="/items/{item_pk}/edit/{lan}">{getattr(languages, f"{lan}_profile_edit_spot")}</a>
            <button mix-delete="/items/{item_pk}/{lan}">{getattr(languages, f"{lan}_profile_delete_item_btn")} {values['item_name']}</button>

            <div class="item-images">
        """
        for img in images:
            item_html += f"""
                <div id="x{img['image_pk']}">
                    <img class="uploaded_imgs_profile"
                         src="/static/uploads/{img['image_name']}"
                         alt="{img['image_name']}">
                </div>
            """
        item_html += "</div></div>"

        blank_form_html = render_template(
            "upload_item_form.html",
            form=None,
            errors=None,
            lan=lan,
            languages=languages
        )

        return f"""
        <mixhtml mix-after="#item-form">
          <div class='alert success' mix-ttl="3000">
            {getattr(languages, f"{lan}_upload_item_success")}
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
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{getattr(languages, f"{lan}_upload_item_error").replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">
          {getattr(languages, f"{lan}_upload_item_button_default")}
        </mixhtml>
        """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***item edit patch***
@app.patch("/items/<item_pk>/<lan>")
def edit_item_post(item_pk, lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

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
            <mixhtml mix-update=".form-feedback">
              {error_html}
            </mixhtml>
            <mixhtml mix-function="resetButtonText">{getattr(languages, f"{lan}_dry_save_changes")}</mixhtml>
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
        <mixhtml mix-redirect="/profile/{lan}?item_message={getattr(languages, f'{lan}_profile_item_updated')}"></mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{getattr(languages, f"{lan}_profile_item_error").replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">{getattr(languages, f"{lan}_dry_save_changes")}</mixhtml>
        """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***item edit get***
@app.get("/items/<item_pk>/edit")
@app.get("/items/<item_pk>/edit/<lan>")
def edit_item_page(item_pk, lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

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

        return render_template(
            "edit_item.html",
            item=item,
            lan=lan,
            languages=languages
        ), 200

    except Exception as ex:
        ic(ex)
        return redirect(url_for("profile")), 302

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***image delete***
# @app.delete("/images/<image_pk>/<lan>")
# def delete_image(image_pk, lan):
#     try:
#         languages_allowed = ["en", "dk"]
#         if lan not in languages_allowed: lan = "en"

#         image_pk = x.validate_image_pk(image_pk)
#         user = x.validate_user_logged()

#         db, cursor = x.db()
#         q = "DELETE FROM images WHERE image_pk = %s"
#         cursor.execute(q, (image_pk,))
#         db.commit()

#         return f"""
#         <mixhtml mix-remove="#x{image_pk}"></mixhtml>
#         <mixhtml mix-after="#items-h2">
#         <div class='alert success' mix-ttl="3000">
#             {getattr(languages, f"{lan}_profile_image_deleted")}
#         </div>
#         </mixhtml>
#         """, 200

#     except Exception as ex:
#         ic(ex)
#         return "", 500

#     finally:
#         if "cursor" in locals(): cursor.close()
#         if "db" in locals(): db.close()

##############################
# ***item delete***
@app.delete("/items/<item_pk>/<lan>")
def delete_item(item_pk, lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

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

        return f"""
        <mixhtml mix-remove="#x{item_pk}"></mixhtml>
        <mixhtml mix-after="#items-h2">
        <div class='alert success' mix-ttl="3000">
            {getattr(languages, f"{lan}_profile_item_deleted")}
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
# ***signup get***
@app.get("/signup")
@app.get("/signup/<lan>")
def show_signup(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        active_signup = "active"
        error_message = request.args.get("error_message", "")
        return render_template(
            "signup.html",
            title="Signup",
            active_signup=active_signup,
            error_message=error_message,
            old_values={},
            lan=lan,
            languages=languages
        ), 200
    except Exception as ex:
        return str(ex), 500

##############################
# ***signup post***
# @app.post("/signup/<lan>")
# def signup(lan):
#     try:
#         languages_allowed = ["en", "dk"]
#         if lan not in languages_allowed: lan = "en"

#         user_username  = x.validate_user_username()
#         user_name      = x.validate_user_name()
#         user_last_name = x.validate_user_last_name()
#         user_email     = x.validate_user_email()
#         user_password  = x.validate_user_password()

#         hashed_password = generate_password_hash(user_password)
#         user_created_at = int(time.time())
#         verification_key = str(uuid.uuid4())

#         q = """
#         INSERT INTO users 
#         (user_pk, user_username, user_name, user_last_name, user_email, 
#          user_password, user_created_at, user_updated_at, user_deleted_at,
#          user_verified, user_verification_key) 
#         VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         """
#         db, cursor = x.db()
#         cursor.execute(q, (
#             user_username, user_name, user_last_name,
#             user_email, hashed_password,
#             user_created_at, 0, 0, 0, verification_key
#         ))

#         if cursor.rowcount != 1:
#             raise Exception("System under maintenance")

#         db.commit()
#         x.send_email(user_name, user_last_name, user_email, verification_key)

#         return f"""
#         <mixhtml mix-redirect='/login/{lan}?message={getattr(languages, f"{lan}_signup_success")}'></mixhtml>
#         """, 200

#     except Exception as ex:
#         ic(ex)
#         if "db" in locals(): db.rollback()

#         if "username" in str(ex):
#             return f"""
#             <mixhtml mix-update=".form-feedback">
#               <div class='alert error'>{getattr(languages, f"{lan}_signup_username_invalid")}</div>
#             </mixhtml>
#             """, 400

#         if "first name" in str(ex):
#             return f"""
#             <mixhtml mix-update=".form-feedback">
#               <div class='alert error'>{getattr(languages, f"{lan}_signup_first_name_invalid")}</div>
#             </mixhtml>
#             """, 400

#         if "last name" in str(ex):
#             return f"""
#             <mixhtml mix-update=".form-feedback">
#               <div class='alert error'>{getattr(languages, f"{lan}_signup_last_name_invalid")}</div>
#             </mixhtml>
#             """, 400

#         if "Invalid email" in str(ex):
#             return f"""
#             <mixhtml mix-update=".form-feedback">
#               <div class='alert error'>{getattr(languages, f"{lan}_signup_email_invalid")}</div>
#             </mixhtml>
#             """, 400

#         if "password" in str(ex):
#             return f"""
#             <mixhtml mix-update=".form-feedback">
#               <div class='alert error'>{getattr(languages, f"{lan}_signup_password_invalid")}</div>
#             </mixhtml>
#             """, 400

#         if "user_email" in str(ex):
#             return f"""
#             <mixhtml mix-update=".form-feedback">
#               <div class='alert error'>{getattr(languages, f"{lan}_signup_email_exists")}</div>
#             </mixhtml>
#             """, 400

#         if "user_username" in str(ex):
#             return f"""
#             <mixhtml mix-update=".form-feedback">
#               <div class='alert error'>{getattr(languages, f"{lan}_signup_username_exists")}</div>
#             </mixhtml>
#             """, 400

#         return f"""
#         <mixhtml mix-update=".form-feedback">
#           <div class='alert error'>{getattr(languages, f"{lan}_signup_unknown_error").replace("{str(ex)}", str(ex))}</div>
#         </mixhtml>
#         """, 400

#     finally:
#         if "cursor" in locals(): cursor.close()
#         if "db" in locals(): db.close()


# ***signup post***
#***FORBEDRET TIL MUNDTLIG EKSAMEN***
#For at gøre min kode mere konsistent, forbedre jeg valideringen i denne route
#Jeg bruger et for loop og tuple unpacking i stedet for at validere manuelt én ad gangen
#Det gør min kode mere DRY, jeg undgår at skrive det samme valideringsmønster igen og igen ved at bruge et loop der reducerer fejl og gør koden lettere at opdatere senere.
# Med for loopet opbygges form_errors automatisk, jeg behøver ikke omslutte alting med validate()-kald, da det sker i loopet.
#Den forbedrede version sikre også i mod at en fejl stopper hele funktionen, og at en bruger kun får en fejl ad gangen.
#Ens struktur i alle routes gør koden lettere at læse og vedligeholde
#Det gør det nemmere at tilføje nye felter uden at ændre ret meget
#Desuden har jeg også forbedret name feedback - før sagde den bare invalid input, nu forklarer den hvad problemet er, og vises både på dansk og engelsk.
    #Jeg manglede variabler og oversættelser i language.py, der tog sig af dette. Ved at tilføje dem virker det nu.
@app.post("/signup/<lan>")
def signup(lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        # Vi opretter en liste af tuples. Hver tuple består af:
        # - navnet på et inputfelt i HTML'en (name="...")
        # - referencen til den valideringsfunktion i x.py, som skal bruges
        validators = [
            ("user_username",   x.validate_user_username),
            ("user_name",       x.validate_user_name),
            ("user_last_name",  x.validate_user_last_name),
            ("user_email",      x.validate_user_email),
            ("user_password",   x.validate_user_password),
        ]

        # Vi opretter to tomme dictionaries:
        # - values gemmer de validerede inputværdier
        # - form_errors gemmer fejlbeskeder for de input der fejler
        values, form_errors = {}, {}

        # Vi looper igennem hver tuple i validators-listen.
        # Ved hjælp af tuple unpacking kalder vi fn (valideringsfunktionen)
        # og gemmer resultatet i values under det korrekte inputnavn.
        # Valideringsfunktionen henter selv værdien fra formularen via
            # request.form.get("fieldname", "").strip() – det sker direkte inde i x.py.
        # Hvis valideringen fejler, gemmer vi fejlbeskeden i form_errors.
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
            <mixhtml mix-update=".form-feedback">
              {error_html}
            </mixhtml>
            """, 400

        hashed_password = generate_password_hash(values["user_password"])
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
            values["user_username"],
            values["user_name"],
            values["user_last_name"],
            values["user_email"],
            hashed_password,
            user_created_at, 0, 0, 0, verification_key
        ))

        if cursor.rowcount != 1:
            raise Exception("System under maintenance")

        db.commit()
        x.send_email(
            values["user_name"],
            values["user_last_name"],
            values["user_email"],
            verification_key
        )

        return f"""
        <mixhtml mix-redirect='/login/{lan}?message={getattr(languages, f"{lan}_signup_success")}&message_type=success'></mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if "user_email" in str(ex):
            message = getattr(languages, f"{lan}_signup_email_exists")
        elif "user_username" in str(ex):
            message = getattr(languages, f"{lan}_signup_username_exists")
        else:
            message = getattr(languages, f"{lan}_signup_unknown_error").replace("{str(ex)}", str(ex))

        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{message}</div>
        </mixhtml>
        """, 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***login get***
@app.get("/login")
@app.get("/login/<lan>")
def show_login(lan="en"):
    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"

    active_login = "active"
    profile_deleted_msg = request.args.get("profile_deleted", "")
    default_message = request.args.get("message", "")
    message = profile_deleted_msg if profile_deleted_msg else default_message

    message_type = request.args.get("message_type", "error")

    return render_template(
        "login.html",
        title="Login",
        active_login=active_login,
        message=message,
        message_type=message_type,
        lan=lan,
        languages=languages
    ), 200

##############################
# ***login post***
@app.post("/login/<lan>")
def login(lan):
    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"

    try:
        user_email = x.validate_user_email()
        user_password = x.validate_user_password()

        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()

        if not user:
            raise Exception(getattr(languages, f"{lan}_login_error_not_found"))

        if not user["user_verified"]:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_login_error_verify_email")}</div>
            </mixhtml>
            """, 403

        if user["user_blocked_at"] != 0:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_login_error_blocked")}</div>
            </mixhtml>
            """, 403

        if not check_password_hash(user["user_password"], user_password):
            raise Exception(getattr(languages, f"{lan}_login_error_credentials"))

        user.pop("user_password")
        session["user"] = user
        ic(user)

        return """
        <mixhtml mix-redirect='/profile'></mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{str(ex)}</div>
        </mixhtml>
        """, 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***logout get***
@app.get("/logout")
@app.get("/logout/<lan>")
def logout(lan="en"):
    session.pop("user", None)

    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"

    return redirect(url_for("show_login", lan=lan)), 302

##############################
# ***admin get***
#***FORBEDRET TIL MUNDTLIG EKSAMEN***
# Tidligere kunne en admin blokere sig selv og dermed blive låst ude af systemet.
# For at forhindre dette sender jeg den loggede brugers user_pk med i render_template som current_user_pk.
# I view_admin.html bruger jeg et if-statement til at sammenligne current_user_pk med hver bruger i listen.
# Hvis user.user_pk == current_user_pk, vises block/unblock-knappen ikke.
# Det betyder, at den loggede admin ikke ser knappen til at blokere eller ophæve blokering af sig selv.
# Da kun admins har adgang til view_admin.html, er det tilstrækkeligt at skjule knappen på denne måde.

@app.get("/admin")
@app.get("/admin/<lan>")
def view_admin(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed:
            lan = "en"

        if not session.get("user") or not session["user"].get("user_is_admin"):
            return render_template(
                "login.html",
                message=getattr(languages, f"{lan}_admin_only"),
                lan=lan,
                languages=languages
            ), 403

        db, cursor = x.db()

        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        cursor.execute("SELECT * FROM items")
        items = cursor.fetchall()

        return render_template(
            "view_admin.html",
            users=users,
            items=items,
            lan=lan,
            languages=languages,
            current_user_pk=session["user"]["user_pk"]
        ), 200

    except Exception as ex:
        ic(ex)
        return str(ex), 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***admin block user***
@app.patch("/admin/block-user")
@app.patch("/admin/block-user/<lan>")
def admin_block_user(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        try:
            user_pk = x.validate_user_pk(request.form.get("user_pk", ""))
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".user-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            """, 400

        db, cursor = x.db()

        cursor.execute("UPDATE users SET user_blocked_at = %s WHERE user_pk = %s", (int(time.time()), user_pk))
        db.commit()

        button = f"""
        <div id="user-actions-{user_pk}">
            <form mix-patch="/admin/unblock-user/{lan}">
                <input type="hidden" name="user_pk" value="{user_pk}" mix-check="^\d+$" title="{getattr(languages, f'{lan}_admin_invalid_user_id')}">
                <button class="btn unblock"
                        mix-await="{getattr(languages, f'{lan}_admin_unblock_button_await')}"
                        mix-default="{getattr(languages, f'{lan}_admin_unblock_button_default')}">
                    {getattr(languages, f'{lan}_admin_unblock_button_default')}
                </button>
            </form>
        </div>
        """

        message = f"""
        <div class='alert success' mix-ttl="3000">
            {getattr(languages, f"{lan}_admin_user_blocked").replace("{user_pk}", str(user_pk))}
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
        return f"""
        <mixhtml mix-update=".user-feedback">
          <div class='alert error'>{getattr(languages, f'{lan}_admin_block_user_error').replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        """, 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***admin unblock user***
@app.patch("/admin/unblock-user")
@app.patch("/admin/unblock-user/<lan>")
def admin_unblock_user(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        try:
            user_pk = x.validate_user_pk(request.form.get("user_pk", ""))
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".user-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            """, 400

        db, cursor = x.db()
        cursor.execute("UPDATE users SET user_blocked_at = 0 WHERE user_pk = %s", (user_pk,))
        db.commit()

        button = f"""
        <div id="user-actions-{user_pk}">
            <form mix-patch="/admin/block-user/{lan}">
                <input type="hidden" name="user_pk" value="{user_pk}" 
                       mix-check="^\d+$" 
                       title="{getattr(languages, f'{lan}_admin_invalid_user_id')}">
                <button class="btn block"
                        mix-await="{getattr(languages, f'{lan}_admin_block_button_await')}"
                        mix-default="{getattr(languages, f'{lan}_admin_block_button_default')}">
                  {getattr(languages, f'{lan}_admin_block_button_default')}
                </button>
            </form>
        </div>
        """

        message = f"""
        <div class='alert success' mix-ttl="3000">
          {getattr(languages, f'{lan}_admin_user_unblocked').replace("{user_pk}", str(user_pk))}
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
        return f"""
        <mixhtml mix-update=".user-feedback">
          <div class='alert error'>{getattr(languages, f'{lan}_admin_block_user_error').replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        """, 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***admin block item***
@app.patch("/admin/block-item")
@app.patch("/admin/block-item/<lan>")
def admin_block_item(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        try:
            item_pk = x.validate_item_pk(request.form.get("item_pk", ""))
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".item-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            """, 400

        db, cursor = x.db()

        cursor.execute("UPDATE items SET item_blocked_at = %s WHERE item_pk = %s", (int(time.time()), item_pk))
        db.commit()

        button = f"""
        <div id="item-actions-{item_pk}">
            <form mix-patch="/admin/unblock-item/{lan}">
                <input type="hidden" name="item_pk" value="{item_pk}"
                       mix-check="^\d+$"
                       title="{getattr(languages, f'{lan}_admin_invalid_user_id')}">
                <button class="btn unblock"
                        mix-await="{getattr(languages, f'{lan}_admin_unblock_button_await')}"
                        mix-default="{getattr(languages, f'{lan}_admin_unblock_button_default')}">
                    {getattr(languages, f'{lan}_admin_unblock_button_default')}
                </button>
            </form>
            <div class="item-feedback"></div>
        </div>
        """

        message = f"""
        <div class='alert success' mix-ttl="3000">
            {getattr(languages, f'{lan}_admin_item_blocked').replace("{item_pk}", str(item_pk))}
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
        return f"""
        <mixhtml mix-update=".item-feedback">
          <div class='alert error'>{getattr(languages, f'{lan}_admin_block_user_error').replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        """, 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***admin unblock item***
@app.patch("/admin/unblock-item")
@app.patch("/admin/unblock-item/<lan>")
def admin_unblock_item(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        try:
            item_pk = x.validate_item_pk(request.form.get("item_pk", ""))
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".item-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            """, 400

        db, cursor = x.db()

        cursor.execute("UPDATE items SET item_blocked_at = 0 WHERE item_pk = %s", (item_pk,))
        db.commit()

        button = f"""
        <div id="item-actions-{item_pk}">
            <form mix-patch="/admin/block-item/{lan}">
                <input type="hidden" name="item_pk" value="{item_pk}"
                       mix-check="^\d+$"
                       title="{getattr(languages, f'{lan}_admin_invalid_user_id')}">
                <button class="btn block"
                        mix-await="{getattr(languages, f'{lan}_admin_block_button_await')}"
                        mix-default="{getattr(languages, f'{lan}_admin_block_button_default')}">
                    {getattr(languages, f'{lan}_admin_block_button_default')}
                </button>
            </form>
            <div class="item-feedback"></div>
        </div>
        """

        message = f"""
        <div class='alert success' mix-ttl="3000">
          {getattr(languages, f'{lan}_admin_item_unblocked').replace("{item_pk}", str(item_pk))}
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
        return f"""
        <mixhtml mix-update=".item-feedback">
          <div class='alert error'>{getattr(languages, f'{lan}_admin_block_user_error').replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        """, 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***forgot password get***
@app.get("/forgot-password")
@app.get("/forgot-password/<lan>")
def show_forgot_password(lan="en"):
    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"
    return render_template("forgot_password.html", old_values={}, lan=lan, languages=languages), 200

##############################
# ***forgot password post***
@app.post("/forgot-password/<lan>")
def forgot_password(lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        user_email = request.form.get("user_email", "").strip()

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", user_email):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class="alert error">{getattr(languages, f'{lan}_forgot_invalid_email')}</div>
            </mixhtml>
            """, 400

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

        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class="alert success" mix-ttl="4000">
            {getattr(languages, f'{lan}_forgot_email_sent')}
          </div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">
          {getattr(languages, f'{lan}_forgot_button_default')}
        </mixhtml>
        """, 200

    except Exception as ex:
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class="alert error">
            {getattr(languages, f'{lan}_dry_unknown_error').replace("{str(ex)}", str(ex))}
          </div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">
          {getattr(languages, f'{lan}_forgot_button_default')}
        </mixhtml>
        """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***verify get***
@app.get("/verify/<verification_key>")
@app.get("/verify/<verification_key>/<lan>")
def verify_user(verification_key, lan="en"):
    try:
        if lan not in ["en", "dk"]:
            lan = "en"

        verification_key = x.validate_verification_key(verification_key)
        db, cursor = x.db()

        q = "SELECT * FROM users WHERE user_verification_key = %s AND user_verified = 0"
        cursor.execute(q, (verification_key,))
        user = cursor.fetchone()

        if not user:
            message = getattr(languages, f"{lan}_verify_invalid")
            return render_template(
                "login.html",
                message=message,
                message_type="error",
                lan=lan,
                languages=languages
            ), 400

        q = """
        UPDATE users
        SET user_verified = 1,
            user_verification_key = NULL
        WHERE user_verification_key = %s
        """
        cursor.execute(q, (verification_key,))
        db.commit()

        message = getattr(languages, f"{lan}_verify_success")
        return render_template(
            "login.html",
            message=message,
            message_type="success",
            lan=lan,
            languages=languages
        ), 200

    except Exception as ex:
        return str(ex), 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***reset password get***
@app.get("/reset-password/<reset_key>")
@app.get("/reset-password/<reset_key>/<lan>")
def show_reset_form(reset_key, lan="en"):
    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"

    return render_template(
        "reset_password.html",
        reset_key=reset_key,
        lan=lan,
        languages=languages
    ), 200

##############################
# ***reset password post***
@app.post("/reset-password/<reset_key>")
@app.post("/reset-password/<reset_key>/<lan>")
def reset_password(reset_key, lan="en"):
    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"

    try:
        try:
            new_password = x.validate_user_password()
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            <mixhtml mix-function="resetButtonText">
              {getattr(languages, f'{lan}_reset_password_button_default')}
            </mixhtml>
            """, 400

        db, cursor = x.db()

        q = "SELECT * FROM users WHERE user_reset_key = %s AND user_deleted_at = 0"
        cursor.execute(q, (reset_key,))
        user = cursor.fetchone()

        if not user:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f'{lan}_reset_password_invalid')}</div>
            </mixhtml>
            """, 403

        now = int(time.time())
        if user["user_reset_requested_at"] < now - 3600:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f'{lan}_reset_password_expired')}</div>
            </mixhtml>
            """, 403

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
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f'{lan}_reset_password_invalid')}</div>
            </mixhtml>
            <mixhtml mix-function="resetButtonText">
              {getattr(languages, f'{lan}_reset_password_button_default')}
            </mixhtml>
            """, 403

        db.commit()

        return f"""
        <mixhtml mix-redirect="/login?message={getattr(languages, f'{lan}_reset_password_success')}"></mixhtml>
        """, 200

    except Exception as ex:
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{getattr(languages, f'{lan}_reset_password_error').replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">
          {getattr(languages, f'{lan}_reset_password_button_default')}
        </mixhtml>
        """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***profile get***
@app.get("/profile")
@app.get("/profile/<lan>")
def profile(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        user = x.validate_user_logged()
        profile_message = request.args.get("profile_message", "")
        item_message = request.args.get("item_message", "")

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
            title=getattr(languages, f"{lan}_profile_title"),
            form=None,
            errors=None,
            profile_message=profile_message,
            item_message=item_message,
            lan=lan,
            languages=languages
        ), 200

    except Exception as ex:
        ic(ex)
        return redirect(url_for("show_login")), 302

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***profile edit get***
@app.get("/profile/edit")
@app.get("/profile/edit/<lan>")
def edit_profile(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed:
            lan = "en"

        if "user" not in session:
            return redirect(url_for("show_login")), 302

        user = session["user"]
        return render_template(
            "edit_profile.html",
            user=user,
            old_values=user,
            message="",
            lan=lan,
            languages=languages
        ), 200

    except Exception as ex:
        return str(ex), 500

##############################
# ***profile edit patch***
@app.patch("/profile/edit/<lan>")
def update_profile(lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        user = x.validate_user_logged()
        user_pk = user["user_pk"]

        # Valider input
        validators = [
            ("user_username",   x.validate_user_username),
            ("user_name",       x.validate_user_name),
            ("user_last_name",  x.validate_user_last_name),
            ("user_email",      x.validate_user_email),
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
            <mixhtml mix-update=".form-feedback">
              {error_html}
            </mixhtml>
            <mixhtml mix-function="resetButtonText">{getattr(languages, f"{lan}_edit_profile_button_default")}</mixhtml>
            """, 400

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
            values["user_username"],
            values["user_name"],
            values["user_last_name"],
            values["user_email"],
            int(time.time()),
            user_pk
        ))
        db.commit()

        # Opdater session
        session["user"].update(values)

        return f"""
        <mixhtml mix-redirect="/profile/{lan}?profile_message={getattr(languages, f'{lan}_profile_message_success')}"></mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{getattr(languages, f"{lan}_profile_item_error").replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">{getattr(languages, f"{lan}_edit_profile_button_default")}</mixhtml>
        """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
# ***profile delete get***
@app.get("/profile/delete")
@app.get("/profile/delete/<lan>")
def delete_profile(lan="en"):
    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"

    if "user" not in session:
        return redirect(url_for("show_login")), 302

    return render_template(
        "delete_profile.html",
        message="",
        user_password_error="",
        old_values={},
        lan=lan,
        languages=languages
    ), 200


##############################
# ***profile delete***
@app.post("/profile/delete/<lan>")
def confirm_delete_profile(lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        if "user" not in session:
            return redirect(url_for("show_login")), 302

        user_pk = session["user"]["user_pk"]
        user_email = session["user"]["user_email"]
        user_password = request.form.get("user_password", "").strip()

        db, cursor = x.db()

        # Tjek password
        cursor.execute("SELECT user_password FROM users WHERE user_pk = %s", (user_pk,))
        result = cursor.fetchone()

        if not result or not check_password_hash(result["user_password"], user_password):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_delete_profile_invalid_password")}</div>
            </mixhtml>
            """, 403

        # Soft delete
        timestamp = int(time.time())
        cursor.execute("UPDATE users SET user_deleted_at = %s WHERE user_pk = %s", (timestamp, user_pk))
        db.commit()

        x.send_delete_confirmation(user_email)
        session.pop("user", None)

        return f"""
        <mixhtml mix-redirect="/login/{lan}?profile_deleted={getattr(languages, f'{lan}_delete_profile_success')}"></mixhtml>
        """, 200

    except Exception as ex:
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{getattr(languages, f"{lan}_delete_profile_unknown_error").replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***search get GAMMEL VERSION***
# @app.get("/search")
# def search():
#     try:
#         search_for = request.args.get("q", "").strip()
#         search_for = x.validate_search_query(search_for)

#         db, cursor = x.db()
#         q = """
#         SELECT items.*, (
#             SELECT image_name
#             FROM images
#             WHERE images.image_item_fk = items.item_pk
#             ORDER BY image_pk ASC
#             LIMIT 1
#         ) AS item_image
#         FROM items
#         WHERE item_blocked_at = 0 AND item_name LIKE %s
#         """
#         cursor.execute(q, (f"{search_for}%",))
#         rows = cursor.fetchall()
#         return jsonify(rows), 200

#     except Exception as ex:
#         ic(ex)
#         return "x", 400

#     finally:
#         if "cursor" in locals(): cursor.close()
#         if "db" in locals(): db.close()

# ***search get***
#***FORBEDRET TIL MUNDTLIG EKSAMEN***
#Jeg havde før aflevering af projektet ikke tilføjet fulltext search, men brugt LIKE.
@app.get("/search")
def search():
    try:
        search_for = request.args.get("q", "").strip()
        search_for = x.validate_search_query(search_for)

        # Tilføj wildcard (*) og skift til BOOLEAN MODE
        boolean_search = f"{search_for}*"

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
        AND MATCH(item_name)
            AGAINST (%s IN BOOLEAN MODE)
        """
        cursor.execute(q, (boolean_search,))
        rows = cursor.fetchall()
        return jsonify(rows), 200

    except Exception as ex:
        ic(ex)
        return "x", 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
        # Vi bruger nu FULLTEXT-søgning med BOOLEAN MODE i stedet for NATURAL LANGUAGE MODE.
        # Forklaring på forskellen:
        # - NATURAL LANGUAGE MODE: Matcher kun hele ord og ignorerer kortere ord (typisk < 4 karakterer).
        #   Det betyder, at søgning på 'engh' ikke matcher 'Enghave', da 'engh' ikke er et komplet ord.
        # - BOOLEAN MODE: Tillader brug af specialtegn som '*' (wildcard), så vi kan finde ord, der starter med noget.
        #   F.eks. 'engh*' matcher både 'Enghave', 'Enghøj' osv.

        # Derudover gælder for begge modes:
        # - FULLTEXT-søgning i MySQL virker som standard kun på ord med mindst 4 tegn,
        #   medmindre man ændrer databasekonfigurationen (ft_min_word_len).

        # Ved at tilføje '*' og bruge BOOLEAN MODE kan vi nu matche på delvise ord, hvilket gør "instant search" muligt.
        # Eksempel: bruger skriver 't', søgning bliver 't*' og matcher f.eks. 'Tivoli' og 'The Little Mermaid'

