from flask import Flask, render_template, session, request
from flask_session import Session
import x
import time
import uuid
import os
import json

from icecream import ic
ic.configureOutput(prefix=f'!x!x!x! | ', includeContext=True)

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
        
        return render_template("view_index.html", title="Skatespots CPH", items=items)

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

