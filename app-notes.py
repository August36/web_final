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
#Når man tilgår index siden, køres en get request, der starter view_index funktionen
@app.get("/<lan>")
#dynamic route parameter lan, tjekker hvilket sprog der er valgt, hvis der er valgt et, så den ved hvilket sprog sidens tekst skal vises på - er dette korrekt?
def view_index(lan="en"):
#Men hvis overstående kommentar er korrekt, hvorfor sætter vi så lan til at være engelsk her? Er det en slags fallback sikring?
    try:
        #try block startes, man bruger try/catch blocks for at kunne opfange hvis fejl opstår
        languages_allowed = ["en", "dk"]
        #Vi siger hvilke languages der er tilladt, ved ikke helt hvorfor det er nødvendigt
        if lan not in languages_allowed: lan = "en"
        #Fallback til engelsk - Kan du forklare alle disse langauge dele? Jeg tror måske noget af det er fra noget debugging, og ved ikke om det hele er nødvendigt?
        db, cursor = x.db()
        #Vi henter db og cursor, som skaber forbindelse til databasen via en funktion fra x filen
        q = """
        #opretter query - tre apostropher bruges til multiline queries
        SELECT items.*, (
        #Vi vælger alt fra items tabellen, punktommet sikre det kun er items der vælges
        # parantesen igang sætter en sub query, der henter et enkelt billede per item - det første billede sorteret efter stigning/ascending.
            SELECT image_name
            #Vi henter image_name som angiver hvilket image der skal hentes fra vores upload mappe?
            FROM images
            WHERE images.image_item_fk = items.item_pk
            #Vi henter de images hvor image_item_fk hænger sammen med item_pk, så vi kun får de images vi har brug for
            ORDER BY image_pk ASC
            #Vi sortere dem ascending, altså det laveste image_pk vises først og de efterfølgende efter
            LIMIT 1
            #Limit 1 fordi vi item_mini kun skal vise et enkelt billede
        ) AS item_image
        #Hvad gør AS - AS gør at vi gemmer værdierne der hentes fra sub query i item_image - og item_image er en et alias
        #Et alias gør at man kan gemme resultaterne som et ekstra felt i vores resultat.
        FROM items
        WHERE item_blocked_at = 0
        #tjekker item ikke er blokeret
        ORDER BY item_created_at
        #sorterer
        LIMIT 2
        #henter max 2 items, fordi der kun skal vises to mini_items som start
        """
        #Men hvordan hænger overstående query sammen med view_index? Er det fordi item mini som udgangspunkt er tom html - eller altså ikke tom, men uden image og tekst, og images og tekst hentes og indsættes så via denne query, og ved at sende det med
        #i return template?
        cursor.execute(q)
        #Vi udføre querien
        items = cursor.fetchall()
        #Vi gemmer alt der er hentet fra databasen i en variabel

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
#get request der aktiveres ved klik på markør på kortet eller klik på item_mini.
@app.get("/items/<item_pk>/<lan>")
#route decorater der bruger dynamisk route parameter til at tjekke om et sprog er valgt
def get_item_by_pk(item_pk, lan="en"):
#det pågældende item_pk bruges som parameter i funktionen -
# klik på markør eller item_mini vil sende det pågældende item_pk til funktionen. 
#Vi bruger lan="en" som fallback, hvis intet lan eksistere i forvejen.
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"
#fallback der sikrer appen i crasher hvis brugeren prøver at indsætte f.eks. spansk
        db, cursor = x.db()
#opretter forbindelse til vores db funktion fra x.py

        # Hent selve item
        q_item = "SELECT * FROM items WHERE item_pk = %s AND item_blocked_at = 0"
        cursor.execute(q_item, (item_pk,))
        item = cursor.fetchone()
#query der henter data item data til det pågældende item_pk. gemmes i en item variabel

        # Hent billeder til item
        q_images = "SELECT * FROM images WHERE image_item_fk = %s"
        cursor.execute(q_images, (item_pk,))
        images = cursor.fetchall()
#Billeder der passer til det pågældende item_pk hentes og gemmes i images variabel

        rates = {}
        with open("rates.txt", "r") as file:
            rates = json.loads(file.read())
#rates hentes fra txt, parses med json.loads

        html_item = render_template("_item.html", item=item, images=images, rates=rates, lan=lan, languages=languages, request=request)
#vi opretter en variabel der hedder html_item, fordi vi så kan bruge den med mix-replace
# html_item indeholder render template som sender _item.html filen med, samt den nye item data i form af item, det samme for images, rates og languages.
#Hvad gør requests?

        return f"""
            <mixhtml mix-replace="#item">
                {html_item}
            </mixhtml>
        """, 200
# Vi bruger mix-replace, til at erstatte det indhold der allerede er i #item div'en i _item.html
# Og grunden til der allerede er noget, er fordi vi indsatte det i view_index routen

    except Exception as ex:
        ic(ex)
        return f"""
            <mixhtml mix-top="body">
                {getattr(languages, f"{lan}_dry_unknown_error")}
            </mixhtml>
        """, 500
#Hvis der opstår en fejl - vises det i toppen af body'en i _item.html, samt statuscode 500 som betyder intern serverfejl.

##############################
# ***item pagination***
@app.get("/items/page/<page_number>")
@app.get("/items/page/<page_number>/<lan>")
def get_items_by_page(page_number, lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        page_number = x.validate_page_number(page_number)
#page number er side-nummeret i pagineringen.
#Hvis page number er 1 = første 2 items, 2 = det næste set items
#Vi validere page number via en validator fra x.py - sikre at page_number ikke har et 0 foran
        items_per_page = 2
#opretter variabel items_per_page = 2
        offset = (page_number - 1) * items_per_page
#opretter en offset variabel der minusser pagenumber med 1 og ganger det med items_per_page
        extra_item = items_per_page + 1
#extra item variabel =items per page +1

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
#query der henter data til item_mini fra databasen. Limit bruges til at hente det extra item
#offset bruges til at tage de næste værdier i rækken, så vi ikke bare viser de samme items igen
#
        cursor.execute(q, (extra_item, offset))
        items = cursor.fetchall()

        rates = {}
        with open("rates.txt", "r") as file:
            rates = json.loads(file.read())

        html = ""
        for item in items[:items_per_page]:
            html += render_template("_item_mini.html", item=item, rates=rates, lan=lan, languages=languages)
#Vi indsætter html'en, og bruger list slicing til at fjerne det extra item der kun bruges til tjek
        button = ""
        if len(items) == extra_item:
            button = render_template("_button_more_items.html", page_number=page_number + 1, lan=lan, languages=languages)
#Vi bruger len - som udregner lengden af items variabelen. vi bruger == til at tjekke om værdien er = med extra_item - altså om der er flere items
#Hvis der, rendere vi en ny show more button, og sender page number med, så vi kan bruge det opdaterede page number til at hente de næste items.
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
#Vi bruger mixhtml til at indsætte de nye item_minis i bunden af mid column(#items), og til at opdatere show more button
#Vi tilføjer nye markers til kortet via add_markers_to_map() fra app.js
    except Exception as ex:
        ic(ex)

        if "skatespots_ex page_number" in str(ex):
            return f"""
                <mixhtml mix-top="body">
                    {getattr(languages, f"{lan}_pagination_invalid_page")}
                </mixhtml>
            """, 400
#Hvis der opstår en fejl med page_number, vises en fejl besked fra language.py - enten på dansk eller engelsk alt efter hvilket sprog er valgt, med errorcode 400 - ugyldig anmodning
        return f"""
            <mixhtml mix-top="body">
                {getattr(languages, f"{lan}_dry_unknown_error")}
            </mixhtml>
        """, 500
#Hvis der opstår nogen anden fejl, vises det som en fejlbesked med errorcode 500 - internal server error

##############################
# ***item post***
#Post item via profile.html
@app.post("/item/<lan>")
def post_item(lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        user = x.validate_user_logged()
        #Validate that the user is logged before they can post
        #Er dette nødvendigt når nu vi også bruger g session til at tjekke om user findes? Man kan ikke have for meget sikkerhed måske?

        validators = [
            # "Hvert inputfelt i min HTML har en name-attribut, f.eks. name="item_lon" eller name="files". Når formularen bliver sendt, kommer værdierne med i request.form eller request.files.
            # I validators-listen bruger jeg disse navne som keys og matcher dem med valideringsfunktioner, som henter data fra requesten. Det gør det muligt at validere alt dynamisk og struktureret."
            ("item_name",        x.validate_item_name),
            ("item_description", x.validate_item_description),
            ("item_price",       x.validate_item_price),
            ("item_lat",         x.validate_item_lat),
            ("item_lon",         x.validate_item_lon),
            ("item_address",     x.validate_item_address),
            ("files",            x.validate_item_images),
        ]
#Vi opretter en liste af tuples, hvor hvert tuple består af:
    # field: navnet på inputfeltet (som en string)
    # fn: en reference til den tilhørende valideringsfunktion fra x.py

        values, form_errors = {}, {}
# Vi opretter to tomme dictionaries:
    # values bruges til at gemme de validerede inputværdier
    # form_errors bruges til at gemme fejlbeskeder, hvis noget input er ugyldigt

        for field, fn in validators:
            try:
                values[field] = fn()
            except Exception as ex:
                form_errors[field] = str(ex)
        # Vi bruger tuple-unpacking, så field bliver inputfeltets navn og fn bliver funktionen.
        # fn() kaldes og returnerer en valideret værdi (f.eks. "Fælledparken")
        # Den gemmes i values[field], f.eks. values["item_name"] = "Fælledparken"
        # Hvis der opstår en fejl, gemmes den i form_errors som form_errors["item_name"] = "Field is required"

        # Opsummering:
        # “Vi gennemgår hvert felt og den tilhørende valideringsfunktion med et loop. Funktionen kaldes, og værdien gemmes i values. Hvis noget går galt, gemmer vi fejlen i form_errors. På den måde håndterer vi alle felter effektivt og ensartet.”

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
        #Hvis der opstår fejl gemmes de i form_errors dictet vi oprettede tidliger
        # Og renderes i html'en.

        db, cursor = x.db()
        item_created_at = int(time.time())
        #Item creates at bliver indsat som et unix timestamp via time som vi har importeret

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
        #Værdierne indsættes i databasen, og der bruges placeholders
        item_pk = cursor.lastrowid
        #Vi gemmer item_pk på det item der lige er blevet valgt til upload.

        images, value_rows = [], []
        # Vi bruger list til billederne, fordi vi bare skal samle flere ens dataobjekter – ét pr. billede. Vi har ikke behov for at tilgå dem via en nøgle som med dict, men skal blot loope over dem og gemme dem i databasen. En liste er oplagt, fordi den bevarer rækkefølgen og kan tilføjes med .append().
        # images skal indeholde dictionaries med billeddata, skal til html senere
        # value rows skal indeholde tekststrenge med sql-vlrdier, som vi bruger til at bygge et bulk insert
        for image_name in values["files"]:
        #values["files"] er en liste de filnavne som billederne, brugeren har uploadet, har. De er allerede blevet valideret i tidligere for loop.
        # Vi looper over hvert billede, f.eks. engahve.jpg, fælledparken.jpg osv.
        # image bliver i hver runde af loopet en string som "enghave.jpg"
            image_pk = uuid.uuid4().hex
            #Tilføjer uuid til image_pk for hvert af billederne 
            images.append({"image_pk": image_pk, "image_name": image_name})
            #Vi indsætter et dictionary for hvert uploadet billede i images-listen. Dette skal ikke ind i databasen, men bruges senere til at vise billederne i html'en.
            value_rows.append(
                f"('{image_pk}', '{user['user_pk']}', '{item_pk}', '{image_name}')"
            )
            # i values_rows listen indsætter vi en tekststreng der svarer til én række i SQL
            # f.eks. "abc123", "userpk5", "item_pk19", "enghave.jpg"
            # Vi bygger denne tekst så vi senere kan sammensætte alle billeder i et sql insert som:
                # INSERT INTO images (image_pk, image_user_fk, image_item_fk, image_name)
                # VALUES
                #"abc123", "userpk5", "item_pk19", "enghave.jpg"
                #"def456", "userpk6", "item_pk20", "fælledparken.jpg"
                #Det er en form for bulk insert hvor vi bruger ','.join(value_rows) i næste del af koden.

        # Hvis der er billeder at indsætte, fortsætter vi
        if value_rows:

            # Udfør en SQL INSERT direkte til databasen
            cursor.execute(
                f"""
                INSERT INTO images (
                    image_pk, image_user_fk, image_item_fk, image_name
                ) VALUES 
                    {','.join(value_rows)}
                # Vi indsætter alle billeder i ét kald – et bulk insert.
                # {','.join(value_rows)} samler alle værdierne i value_rows-listen og adskiller dem med komma.
                # Det kan f.eks. ende som:
                # ('abc123', 'user1', 'item1', 'img1.jpg'),
                # ('def456', 'user1', 'item1', 'img2.jpg')
                # Derfor bliver hele queryen:
                # INSERT INTO images (...) VALUES 
                # ('abc123', 'user1', 'item1', 'img1.jpg'),
                # ('def456', 'user1', 'item1', 'img2.jpg');
                #
                # Vi bruger f-strings fordi placeholders (%s) ikke understøtter flere rækker direkte i én VALUES-blok.
                # Det er en hurtig og effektiv måde at gemme flere billeder på.
                #
                # ⚠️ MEN: Det er ikke 100% sikkert, fordi vi bygger SQL'en som tekst.
                # Det kan være sårbart over for SQL injection, hvis input ikke er valideret.
                # Her er risikoen lav, fordi filnavne er valideret og image_pk er et UUID.
                # Men i en produktion burde man overveje `executemany()` eller en ORM.
                """
            )

        # Når alt er udført korrekt, gemmes ændringerne i databasen
        db.commit()

        # Vi bygger HTML'en til det nye item, som skal vises på profilsiden efter upload
        item_html = f"""
            <div class="item-card" id="x{item_pk}">
                <h3>{values['item_name']}</h3>
                <p><strong>{getattr(languages, f"{lan}_dry_price")}</strong> {values['item_price']} DKK</p>
                <p><strong>{getattr(languages, f"{lan}_dry_address")}</strong> {values['item_address']}</p>
                <p>{values['item_description']}</p>

                <a href="/items/{item_pk}/edit/{lan}">
                    {getattr(languages, f"{lan}_profile_edit_spot")}
                </a>

                <button mix-delete="/items/{item_pk}/{lan}">
                    {getattr(languages, f"{lan}_profile_delete_item_btn")} {values['item_name']}
                </button>

                <div class="item-images">
        """
        # Vi starter med at opbygge kortet (item card) med navn, pris, adresse og beskrivelse
        # Derefter tilføjer vi link til redigering og slet-knap
        # Vi starter også en container-div til billederne

        for img in images:
            item_html += f"""
                <div id="x{img['image_pk']}">
                    <img class="uploaded_imgs_profile"
                        src="/static/uploads/{img['image_name']}"
                        alt="{img['image_name']}">
                </div>
            """
        # Vi looper over billederne og tilføjer hver som et <img>-element med korrekt filnavn og ID

        item_html += "</div></div>"
        # Vi afslutter både billed-containeren og hele item-card div'en

        blank_form_html = render_template(
            "upload_item_form.html",
            form=None,
            errors=None,
            lan=lan,
            languages=languages
        )
        # Vi renderer formularen igen – uden værdier – så den bliver ryddet efter succesfuldt upload


        # Vi returnerer 3 mixhtml-blokke:
        return f"""
        <mixhtml mix-after="#item-form">
        <div class='alert success' mix-ttl="3000">
            {getattr(languages, f"{lan}_upload_item_success")}
        </div>
        </mixhtml>
        # Viser en succesbesked lige under formularen – forsvinder automatisk efter 3 sekunder

        <mixhtml mix-update="#item-form">
        {blank_form_html}
        </mixhtml>
        # Erstat formularen med en ny, tom version

        <mixhtml mix-after="#items-h2">
        {item_html}
        </mixhtml>
        # Indsæt det nye item lige efter overskriften på profilsiden – uden at reloade siden
        """, 200


        # Hvis der opstår fejl undervejs
        except Exception as ex:
            ic(ex)
            return f"""
            <mixhtml mix-update=".form-feedback">
            <div class='alert error'>
                {getattr(languages, f"{lan}_upload_item_error").replace("{str(ex)}", str(ex))}
            </div>
            </mixhtml>
            <mixhtml mix-function="resetButtonText">
            {getattr(languages, f"{lan}_upload_item_button_default")}
            </mixhtml>
            """, 500
        # Vi fanger fejlen, udskriver den til terminalen med icecream, og viser en fejlbesked i frontend

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
        # Vi lukker altid cursor og db-forbindelse til sidst, så vi undgår forbindelseslæk


##############################
# ***item edit patch***
@app.patch("/items/<item_pk>/<lan>")
def edit_item_post(item_pk, lan):
# I denne route modtager vi item_pk som route-parameter fra frontend.
# Det bruges til at identificere hvilket item der skal redigeres.
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
        #List med tuples som indeholer hvert input felt samt deres tilhørende validerings funktioner

        values, form_errors = {}, {}
        #Opretter tomme dicts. Values tager i loopet værdierne fra inputsne, form_errors fanger fejl
        for field, fn in validators:
        # field er navnet på inputfeltet (f.eks. "item_name"), og fn er den tilhørende valideringsfunktion.
        # Vi bruger tuple unpacking i for-loopet, hvor rækkefølgen i hver tuple bestemmer hvad der pakkes ud i field og fn.
        # Funktionen fn() validerer inputtet, og hvis det lykkes, gemmes den validerede værdi i values[field].
        # Hvis der opstår en fejl, gemmes fejlbeskeden i form_errors[field].
            try:
                values[field] = fn()
            except Exception as ex:
                form_errors[field] = str(ex)
                #Opstår der validerings fejl, gemmes de som en string i form_errors dictet
        if form_errors:
            #Hvis der er form errors, opret html element til at vise beskederne.
            error_html = (
                "<ul class='alert error'>"
                + "".join(f"<li>{msg}</li>" for msg in form_errors.values())
                + "</ul>"
            )
            return f"""
            <mixhtml mix-update=".form-feedback">
              {error_html}
              #Vi bruger mixhtml til at vise fejlene i den div i html'en der har class .form-feedback
            </mixhtml>
            <mixhtml mix-function="resetButtonText">{getattr(languages, f"{lan}_dry_save_changes")}</mixhtml>
            #Resetter knappens tekst, da jeg havde en bug med at den forsvandt.
            """, 400

        db, cursor = x.db()
        #Opretter db forbindelse

        cursor.execute(
            #udfør querien, hvor vi opdatere kolonnerne i items tablet, med brugerens nye værdier
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
            #WHERE item_pk = %s AND item_user_fk = %s sikrer, at brugeren kun kan redigere sit eget item – ikke andres.
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
            #Vi bruger sql placeholders, og vi har lavet en tuple til hver værdi, som indsættes i stedet for %s så værdierne sendes skjult
        )

        db.commit()

        return f"""
        <mixhtml mix-redirect="/profile/{lan}?item_message={getattr(languages, f'{lan}_profile_item_updated')}"></mixhtml>
        """, 200
        #Brugeren redirectes til profilsiden med en query parameter (item_message) som vises som succesbesked i frontend.

    except Exception as ex:
        ic(ex)
        #Vi bruger ic til at vise den variabel hvor vi har gemt mulige fejlbeskeder.
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{getattr(languages, f"{lan}_profile_item_error").replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">{getattr(languages, f"{lan}_dry_save_changes")}</mixhtml>
        """, 500
        #fejl beskeder vises hvsi der er nogen

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
        #locals() bruges for at tjekke om variablen overhovedet blev defineret (så man undgår NameError hvis fx fejlen sker tidligt i funktionen). og forbindelsen lukkes

##############################
# ***item edit get***
# Viser edit-item-siden for det valgte item, hvis det tilhører den loggede bruger.
@app.get("/items/<item_pk>/edit")
# Brugeren kommer hertil via klik på "Rediger"-knappen på et item.
# item_pk sendes med som route-parameter for at finde det korrekte item.@app.get("/items/<item_pk>/edit/<lan>")
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
        #Vi henter det item, som passer til det item_pk - Det matches med item_user_fk, da brugeren kun kan ændre i de items de selv har oprettet.
        item = cursor.fetchone()
        #Vi gemmer item'et der bliver hentet fra databasen i en variabel
        if not item:
            raise Exception("Item not found")
       # Hvis der ikke blev fundet et item (f.eks. fordi det ikke eksisterer eller ikke tilhører brugeren),
        # kaster vi en fejl for at aktivere except-blokken og sende brugeren tilbage til profilsiden.

        return render_template(
            "edit_item.html",
            item=item,
            lan=lan,
            languages=languages
        ), 200
        # Vi renderer edit_item.html og sender item-dataen samt sprogvalg (lan + languages) med, så siden kan vises dynamisk.

    except Exception as ex:
        ic(ex)
        return redirect(url_for("profile")), 302
        # Vi bruger redirect til at sende brugeren tilbage til profilsiden.
        # Flask returnerer automatisk statuskode 302 (Found), som betyder, at brugeren skal lave en ny GET-request til den angivne URL.
        # Jeg har skrevet 302 eksplicit for at vise forståelse for statuskoder, selvom det er standard for redirect().

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
#Denne funktion sletter et item, som brugeren har oprettet. Det sket via klik på delete item knappen, der tilhøre visningen i oversigten over items brugeren har oprettet
@app.delete("/items/<item_pk>/<lan>")
def delete_item(item_pk, lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        user = x.validate_user_logged()
        # Tjekker at brugeren er logget ind.
        # Selvom g.user er sat via before_request, bruger vi denne funktion til at sikre,
        # at brugeren stadig er gyldig og for at hente user-objektet direkte.
        item_pk = x.validate_item_pk(item_pk)
        #der valideres om hvorvidt item_pk er en int, gennem validation funktionen fra x.py

        db, cursor = x.db()

        # Slet billeder tilknyttet item
        q_images = "DELETE FROM images WHERE image_item_fk = %s"
        cursor.execute(q_images, (item_pk,))
        # DELETE-statement der sletter alle billeder knyttet til det valgte item_pk

        # Slet selve item
        q_item = "DELETE FROM items WHERE item_pk = %s AND item_user_fk = %s"
        cursor.execute(q_item, (item_pk, user["user_pk"]))
        # DELETE-statement sletter hele rækken i items-tabellen, så vi behøver ikke angive de enkelte kolonner.

        db.commit()

        return f"""
        <mixhtml mix-remove="#x{item_pk}"></mixhtml>
        #mixhtml bruger mix-remove funktionen til at fjerne den pågældende html.
        <mixhtml mix-after="#items-h2">
        #Efter items h2'en, indsættet en succesbesked der bruger lan til at tjekke hvilekt sprog beskeden skal vises i.
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
        # Hvis brugeren allerede er logget ind, giver det ikke mening at vise signup-formularen.
        # evt. lav ændring der redirecter dem til profilsiden.
        #Hvis brugeren er logget ind og tilgår signup manuelt i url'en, ignoreres overstående linje
        error_message = request.args.get("error_message", "")
        #request.args.get - henter query parametret error_messages fra URL'en hvis den findes.
        #Så hvis brugeren f.eks. lander på URL'en: /signup?error_message=Email+already+in+use
        #Så vil request.args.get("error_message", "") returnere "Email already in use"
        return render_template(
            "signup.html",
            ## Vi bruger render_template til at vise signup.html med de relevante variabler.
            title="Signup",
            #Sætter title
            active_signup=active_signup,
            # Sætter active_signup = "active", så signup-linket i nav'en bliver markeret som aktivt med CSS.
            # Dette har kun effekt hvis brugeren ikke er logget ind, da signup-linket ellers ikke vises.
            error_message=error_message,
            old_values={},
            # Tomt dict – bruges til at gemme brugerens inputfelter i tilfælde af fejl,
            # så felterne ikke nulstilles ved rerendering. (Udfyldes typisk af POST-routen)
            lan=lan,
            languages=languages
            #Valgt language sendes med så signup siden vises i de sprog brugeren har valgt
        ), 200
    except Exception as ex:
        return str(ex), 500

##############################
# ***signup post***
@app.post("/signup/<lan>")
def signup(lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        user_username  = x.validate_user_username()
        user_name      = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email     = x.validate_user_email()
        user_password  = x.validate_user_password()
        #Her validere jeg anderledes end items routes. De skyldes manglende overblik i processen
        #En opdatering der ville bringe bedre consistency i min kode, kunne være at opsætte denne validering på samme måde, med tuples og for loop, som i post og patch items.

        hashed_password = generate_password_hash(user_password)
        #fra werkzeug.security bruger vi funktion til at genere hashede passwords.
        #Vi gør dette ved at sende user password med som parameter

        user_created_at = int(time.time())
        #Opretter unix timestamp til created at
        verification_key = str(uuid.uuid4())
        #Opretter verication key som uuid - denne sendes senere til brugerens email.

        q = """
        INSERT INTO users 
        (user_pk, user_username, user_name, user_last_name, user_email, 
         user_password, user_created_at, user_updated_at, user_deleted_at,
         user_verified, user_verification_key) 
        VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        # INSERT-statement til at oprette en ny bruger i users-tabellen.
        # Vi bruger placeholders (%s) og sender sikre, validerede værdier direkte.
        db, cursor = x.db()
        cursor.execute(q, (
            user_username, user_name, user_last_name,
            user_email, hashed_password,
            user_created_at, 0, 0, 0, verification_key
        ))
        #Udføre query og angiver variablerne, så de kan bruges af palceholdersne

        if cursor.rowcount != 1:
            raise Exception("System under maintenance")
        # Sikrer at én og kun én række blev oprettet. Hvis ikke, kaster vi en generel fejl (f.eks. ved systemfejl).

        db.commit()
        #Commit query til databasen
        x.send_email(user_name, user_last_name, user_email, verification_key)
        #Fra x fil, aktivere vi send_email funktionen, og med sender de nødvendige variabler som parametre.
        # Det bruges til at bekræfte at brugeren ejer e-mailen, via et separat verificeringsflow.


        return f"""
        <mixhtml mix-redirect='/login/{lan}?message={getattr(languages, f"{lan}_signup_success")}'></mixhtml>
        """, 200
        #Mixhtml-redirect funktion redirectger ved succes brugeren til login, og giver succesbesked.

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        #Lav rollback på transaktionen hvis db findes i fejlbeskeden i locals

        if "username" in str(ex):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_signup_username_invalid")}</div>
            </mixhtml>
            """, 400

        if "first name" in str(ex):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_signup_first_name_invalid")}</div>
            </mixhtml>
            """, 400

        if "last name" in str(ex):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_signup_last_name_invalid")}</div>
            </mixhtml>
            """, 400

        if "Invalid email" in str(ex):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_signup_email_invalid")}</div>
            </mixhtml>
            """, 400

        if "password" in str(ex):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_signup_password_invalid")}</div>
            </mixhtml>
            """, 400

        if "user_email" in str(ex):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_signup_email_exists")}</div>
            </mixhtml>
            """, 400

        if "user_username" in str(ex):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_signup_username_exists")}</div>
            </mixhtml>
            """, 400
        #Overstående if statements returnere fejlbeskeder for de forskellige inputs.
        # Vi matcher fejlbeskeder med substrings for at vise relevante valideringsbeskeder.
        # En mere robust tilgang ville være at bruge egne exception-klasser eller error-koder.
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{getattr(languages, f"{lan}_signup_unknown_error").replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        """, 400
        #Hvis der er opstået fejl som ikke indeholder nogle af overstående strings, send en uknown error fejl

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
    # Sætter active_login = "active", så login-linket i nav'en bliver markeret som aktivt med CSS.
    # Dette har kun effekt hvis brugeren ikke er logget ind (linket skjules ellers via g.is_session).
    profile_deleted_msg = request.args.get("profile_deleted", "")
    #Når en bruger sletter sin profil, sendes en deleted msg med, den tages fra url'en med request.args.get
    # Vi bruger request.args.get(...) til at hente beskeder sendt via URL’en (efter ?message=...).
    # Det er en god måde at vise feedback mellem redirects uden at gemme det i session.
    default_message = request.args.get("message", "")
    #Andre beskeder der sendes med fra andre sider
    message = profile_deleted_msg if profile_deleted_msg else default_message
    # Hvis en profil lige er blevet slettet, vises en særlig besked (profile_deleted).
    # Ellers vises en evt. anden besked sendt med som query parameter (message).

    return render_template(
        #Render login.html med de nødvendige variabler
        "login.html",
        title="Login",
        active_login=active_login,
        message=message,
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
        #Valider brugerens inputs

        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()
        ## Query der ud fra user_email henter hele rækken (alle kolonner) fra users-tabellen.
        #Svaret gemmes i en variabel vi kalder user

        if not user:
            raise Exception(getattr(languages, f"{lan}_login_error_not_found"))
        #Hvis query fejler og user dermed er tom - kast fejlbesked

        if not user["user_verified"]:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_login_error_verify_email")}</div>
            </mixhtml>
            """, 403
        #user_verified kolonnen tjekkes - hvis den er 0 send fejlbesked

        if user["user_blocked_at"] != 0:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_login_error_blocked")}</div>
            </mixhtml>
            """, 403
        #user_blocked_at kolonnen tjekkes - hvis den er noget andet end 0, send fejlbesked

        if not check_password_hash(user["user_password"], user_password):
            raise Exception(getattr(languages, f"{lan}_login_error_credentials"))
        # Vi sammenligner det hashede password i databasen med det brugerindtastede password.
        # Funktionen returnerer True hvis det matcher – ellers False.

        user.pop("user_password")
        #Vi fjerner user_password fra user objektet, for sikkerhed
        session["user"] = user
        #Vi gemmer user i session cookie
        ic(user)

        return """
        <mixhtml mix-redirect='/profile'></mixhtml>
        """, 200
        #Hvis ingen fejl findes - redirect til profile

    except Exception as ex:
        ic(ex)
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{str(ex)}</div>
        </mixhtml>
        """, 400
    #Indsætter fejlbeskeder i form-feedback

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***logout get***
@app.get("/logout")
@app.get("/logout/<lan>")
def logout(lan="en"):
    session.pop("user", None)
# Vi fjerner brugeren fra sessionen, så de bliver logget ud.
# Pop fjerner nøglen "user" fra session-dict'en, hvis den findes.

    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"

    return redirect(url_for("show_login", lan=lan)), 302
    #Brugeren redirectes til show_login efter logout, 302 statuskode for redirect.

##############################
# ***admin get***
@app.get("/admin")
@app.get("/admin/<lan>")
def view_admin(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed:
            lan = "en"

        if not session.get("user") or not session["user"].get("user_is_admin"):
        #Hvis enten user ikke findes i session eller hvis user_is_admin er 0 - render login.html med admin only besked
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
        #query's der henter alle users og alle items til at vise i en liste på admin siden.

        return render_template(
            "view_admin.html",
            users=users,
            items=items,
            lan=lan,
            languages=languages
        ), 200

    except Exception as ex:
        ic(ex)
        return str(ex), 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***admin block user***
#Route til at blokere eller eller unblocke en bruger
@app.patch("/admin/block-user")
@app.patch("/admin/block-user/<lan>")
def admin_block_user(lan="en"):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        try:
            user_pk = x.validate_user_pk(request.form.get("user_pk", ""))
        #På admin.html er en liste over brugere, når user klikker på block, sendes user_pk for den pågældende bruger i URL'en, og vi validere det her i try blokken
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".user-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            """, 400
        #Ved fejl vises en error besked

        db, cursor = x.db()

        cursor.execute("UPDATE users SET user_blocked_at = %s WHERE user_pk = %s", (int(time.time()), user_pk))
        #Ved validations succes af det pågældende user_pk - update user_blocked_at kolonnen til det pågældende user_pk med et unix timestamp der viser hvornår brugeren blev blokeret.
        db.commit()

        button = f"""
        <!-- Vi genererer en ny knap, som erstatter den gamle, efter en bruger er blevet blokeret -->
        <div id="user-actions-{user_pk}">
            <!-- Unikt ID så vi kan opdatere denne del af DOM'en dynamisk med mixhtml -->
            <form mix-patch="/admin/unblock-user/{lan}">
                <!-- Formular til at sende en PATCH-request til unblock-route -->
                <input type="hidden" name="user_pk" value="{user_pk}" mix-check="^\d+$"
                    title="{getattr(languages, f'{lan}_admin_invalid_user_id')}">
                <!-- Skjult inputfelt med brugerens ID og validering -->
                
                <button class="btn unblock"
                        mix-await="{getattr(languages, f'{lan}_admin_unblock_button_await')}"
                        mix-default="{getattr(languages, f'{lan}_admin_unblock_button_default')}">
                    {getattr(languages, f'{lan}_admin_unblock_button_default')}
                </button>
                <!-- Unblock-knap med loading-tekst og standardtekst, afhængig af knap-status -->
            </form>
        </div>
        """

        message = f"""
        <div class='alert success' mix-ttl="3000">
            {getattr(languages, f"{lan}_admin_user_blocked").replace("{user_pk}", str(user_pk))}
        </div>
        """
        #Succes besked vises for admin, hvis brugeren er blevet blokeret.

        cursor.execute("SELECT user_email, user_name FROM users WHERE user_pk = %s", (user_pk,))
        user = cursor.fetchone()
        if user:
            x.send_block_user_email(user["user_email"], user["user_name"])
        #Vi henter user_email og user_name fra det user row der passer til det pågældende user_pk fordi de skal bruges i den mail der sendes
        #Vi sender mail der informere brugeren om at de er blevet blokeret via send_block_email fra x.py

        return f"""
        <mixhtml mix-replace="#user-actions-{user_pk}">
          {button}
        </mixhtml>
        <mixhtml mix-update="#user-card-{user_pk} .user-feedback">
          {message}
        </mixhtml>
        """, 200
        #indsætter den ændrede button fra tidligere, samt beskeden om hvorvidt brugeren er blocked eller ej ikke?

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
            #Tager user_pk fra formens patch data. Knappen indeholder en skjult input hvis value er user_pk.
            #Så når man trykker på knappen gør mixHTML at der sendes en patch request til denne route
            #Formen indgår i requesten, og derfor bliver user_pk sendt med som form data og kan derfor læses med request.form.get("user_pk")
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".user-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            """, 400
            #Hvis der opstår en fejl, f.eks. user_pk ikke eksistere vises en error besked

        db, cursor = x.db()
        cursor.execute("UPDATE users SET user_blocked_at = 0 WHERE user_pk = %s", (user_pk,))
        db.commit()
        #Vi åbner database forbindelsen fra x.py
        #Med UPDATE statement sætter vi user_blocked_at = 0, for den valgte bruger

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
        #Efter unblock bygges en ny knap, som giver mulighed for at blokere brugeren igen.

        message = f"""
        <div class='alert success' mix-ttl="3000">
          {getattr(languages, f'{lan}_admin_user_unblocked').replace("{user_pk}", str(user_pk))}
        </div>
        """
        #Ved succes vises en besked, som med mix.ttl=3000 skjules igen efter 3sek.
        #Vi bruger replace() til at indsætte user_pk ind i beskeden.

        cursor.execute("SELECT user_email, user_name FROM users WHERE user_pk = %s", (user_pk,))
        user = cursor.fetchone()
        if user:
            x.send_unblock_user_email(user["user_email"], user["user_name"])
        #Henter e-mail og navn på brugeren og sender en mail om at brugeren er unblocked via send_unblock_user_email fra x.py

        return f"""
        <mixhtml mix-replace="#user-actions-{user_pk}">
          {button}
        </mixhtml>
        <mixhtml mix-update="#user-card-{user_pk} .user-feedback">
          {message}
        </mixhtml>
        """, 200
        #Vi erstatter den knap der før var unblock, med block knappen som vi byggede tidligere, samt viser en besked.

    except Exception as ex:
        return f"""
        <mixhtml mix-update=".user-feedback">
          <div class='alert error'>{getattr(languages, f'{lan}_admin_block_user_error').replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        """, 400
        #Hvis noget går galt, f.eks. en DB fejl, vises en generel fejlbesked

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
        #Sørger for at DB og cursor altid lukkes, også selvom noget fejler undervejs.
        #Det gøres ved at locals() tjekker om variablerne er blevet oprettet, eller ville close() give en fejl

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
            #Vi læser item_pk fra den patch-form som admin netop har sendt, med tryk på knappen
            #knappen indeholder en form, med et skjult input, som indeholder item_pk
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".item-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            """, 400
        #Hvis valideringen af item_pk fejler, vises en fejlbesked i .item-feedback.

        db, cursor = x.db()

        cursor.execute("UPDATE items SET item_blocked_at = %s WHERE item_pk = %s", (int(time.time()), item_pk))
        db.commit()
        #Sætter item_blocked_at kolonnen til nuværende unix timestamp

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
        #Vi bygger en ny unblock knap, så admin kan ophæve blokeringen senere.
        #Brugeren ser aldrig det skjulte input, men det gør flask hvis knappen trykkes - via patch requesten
        #Mix check validerer inputtet - item_pk - og title bruges som fejlbesked.

        message = f"""
        <div class='alert success' mix-ttl="3000">
            {getattr(languages, f'{lan}_admin_item_blocked').replace("{item_pk}", str(item_pk))}
        </div>
        """
        #Succesbesked

        cursor.execute("""
        SELECT users.user_email, users.user_name, items.item_name
        FROM items
        JOIN users ON users.user_pk = items.item_user_fk
        WHERE items.item_pk = %s
        """, (item_pk,))
        data = cursor.fetchone()
        if data:
            x.send_block_item_email(data["user_email"], data["user_name"], data["item_name"])
        #Email om blokering af item sendes til brugeren
        #Fra user tabellen henter vi user_email og user_name, og fra items tabellen item_name
        #Vi bruger JOIN til at få en sammensat række fra både item og user tabellen.
        # WHERE items.item_pk = værdien af det item_pk der er valgt

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
    #Generel fejlhåndtering - hvis noget går galt, DB-fejl, form mangler, e.mail fejler, vises en generel fejlbesked.

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
            #Fordi at tryk på knappen indeholder item_pk i et tomt input, henter vi item_pk fra formdataen via patch requesten der sendes ved trykket på knappen.
            #Vi valdere item_pk - tjekker at det er et tal
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".item-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            """, 400
            #Hvis valideringen fejler, vises en fejlbesked i item-feedback.
            # vi bruger mix-update, til kun at opdatere item-feedback elementet, uden at reloade hele siden.

        db, cursor = x.db()

        cursor.execute("UPDATE items SET item_blocked_at = 0 WHERE item_pk = %s", (item_pk,))
        db.commit()
        #Query der sætter item_blocked_at til 0 - item_blocked_at fjerner altså det unix timestamp vi indsatte i overstående route
        #item_blocked_at virker som en slags boolean, hvor vi routes som bestemmer om det skal vises eller ej, tjekker om hvorvidt det er 0, og hvis det ikke er 0, stopper vi det i at blive vist

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
        #Vi bygger en ny knap der viser at item er blocked, og giver mulighed for at brugeren kan blokere item'et igen senere
        #Mix-patch sender patch request med det skjulte input som indeholder item_pk
        #Mix-check validere at item_pk er et tal
        #Tekster håndteres dynamisk via languages filen. {lan} - som enten er dk eller en, hentes fra url'en i route decoratoren
        # Og her ud fra hvad der er valgt, hentes den version af teksten fra language.py. 

        message = f"""
        <div class='alert success' mix-ttl="3000">
          {getattr(languages, f'{lan}_admin_item_unblocked').replace("{item_pk}", str(item_pk))}
        </div>
        """
        #Succes besked vises

        cursor.execute("""
        SELECT users.user_email, users.user_name, items.item_name
        FROM items
        JOIN users ON users.user_pk = items.item_user_fk
        WHERE items.item_pk = %s
        """, (item_pk,))
        data = cursor.fetchone()
        if data:
            x.send_unblock_item_email(data["user_email"], data["user_name"], data["item_name"])
            #Email sendes. Vi bruger JOIN så vi i mailen kan skrive en besked der fortæller "user_name" at deres "item_name" er blevet unblocked.

        return f"""
        <mixhtml mix-replace="#item-actions-{item_pk}">
          {button}
        </mixhtml>
        <mixhtml mix-update="#item-actions-{item_pk} .item-feedback">
          {message}
        </mixhtml>
        """, 200
        #Mix-replace bruges til at erstatte den eksisterende block item knap med den nye unblock knap vi tidligere byggede
        #Succesbesked vises

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
    #Når forget password liket klikkes, sendes en get request til denne route, der rendere forgot_password.html.

##############################
# ***forgot password post***
@app.post("/forgot-password/<lan>")
def forgot_password(lan):
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        user_email = request.form.get("user_email", "").strip()
        #forgot_password.html indeholder en form med et email input, når knappen til at sende formen klikkes
        #Gemmer vi brugerens email i user_email variabel. Strip() fjerner eventuelle mellemrum i inputtet.

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", user_email):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class="alert error">{getattr(languages, f'{lan}_forgot_invalid_email')}</div>
            </mixhtml>
            """, 400
        #If statement der validere om brugerens email er korrekt format. Kaster fejlbesked hvis ikke.
        #re er pythons standardmodul til regex, som vi har importeret i toppen af filen.
        # Når vi skriver re.match(...) så kalder vi match() funktionen fra re-modulet, og sender det regex-mønster variablen user_email skal tjekkes med.

        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()
        #Fra users tabellen, henter vi kolonnen hvor user_email er = med den email brugeren angav, og tjekker at brugen ikke er slettet.
        #Vi gemmer resultatet i variablen user med cursor.fetchone.

        if user:
            #Hvis der er noget i den user variabel vi lige har oprettet
            reset_key = str(uuid.uuid4())
            #Generere vi et uuid og gemmer det i en reset_key variabel
            now = int(time.time())
            #Vi opretter en variabel - now - og indsætter en unix time stamp via time som er standard modul i python til at lave unix timestamps.
            q = """
            UPDATE users
            SET user_reset_key = %s,
                user_reset_requested_at = %s
            WHERE user_email = %s
            """
            #Vi opdatere users tabellen, vi indsætter user_reset_key med det uuid vi oprettede
            #Vi indsætter i user_reset_request at, værdien(unix timestamp) af den "now" variabel vi oprettede.
            #Vi bruger WHERE til, ud fra user_email, at vælge den korrekte række i users tabellen.
            cursor.execute(q, (reset_key, now, user_email))
            db.commit()
            x.send_reset_email(user_email, reset_key)
            #Via send_reset_email funktionen fra x.py, sender vi mailen til brugerens email, og medsender det uuid som er brugerens reset-key.

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
        #info besked om at mail med reset key er sendt til email
        #Opdatering af reset knappens tekst, da den bliver fjernet ved rerendering at formen.

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
# ***reset password get***
#Når brugeren klikker på linket der blev sendt af overstående funktion, sendes en get request til denne route.
#Denne route rendere reset_password.html, som indeholder en form og et input, hvor brugeren kan indtaste sit nye password.
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
#Når brugeren har indtastet sit nye password gennem reset_password.html, og trykker på knappen i formen til at opdatere sit password, aktiveres denne post route
@app.post("/reset-password/<reset_key>")
@app.post("/reset-password/<reset_key>/<lan>")
def reset_password(reset_key, lan="en"):
    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"

    try:
        try:
            new_password = x.validate_user_password()
            #Vi validere brugerens nye password
        except Exception as ex:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{str(ex)}</div>
            </mixhtml>
            <mixhtml mix-function="resetButtonText">
              {getattr(languages, f'{lan}_reset_password_button_default')}
            </mixhtml>
            """, 400
            #Kaster fejl hvis brugerens nye password ikke består valideringen

        db, cursor = x.db()

        q = "SELECT * FROM users WHERE user_reset_key = %s AND user_deleted_at = 0"
        cursor.execute(q, (reset_key,))
        user = cursor.fetchone()
        #Forbind til databasen, og find den pågældende bruger ud fra reset_key

        if not user:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f'{lan}_reset_password_invalid')}</div>
            </mixhtml>
            """, 403
        #Hvis ingen bruger findes, vises en fejl.

        now = int(time.time())
        if user["user_reset_requested_at"] < now - 3600:
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f'{lan}_reset_password_expired')}</div>
            </mixhtml>
            """, 403
        #Vi tjekker om linket er udløbet, ved at oprette et nyt timestamp og sammenligne det timestamp der blev oprettet og gemt i user_reset_requested_at, da brugeren requestede skift af password
        # Vi tjekker om der er gået 60 minutter siden nulstillingen blev requested (3600 sekunder) ved at se om det nye timestamp er inden for den tidsmængde
        #Hvis der er gået længere tid end 60 minutter, er requesten nulstillet, og det vises i en besked. Så koden det overstående if statement aktiveres kun, hvis det er tilfældet.

        hashed = generate_password_hash(new_password)
        #Hvis brugeren har klikket på reset linket i deres mail i tide, hasher vi det nye password

        q = """
        UPDATE users
        SET user_password = %s,
            user_reset_key = NULL,
            user_reset_requested_at = 0
        WHERE user_reset_key = %s
        """
        #Og opdatere user_password kolonnen med det nye hashede password.
        #Vi sletter også reset_key'en og sætter user_reset_requested_at kolonnen til 0
            #Dette sikrer, at samme link ikke kan bruges igen, og at nulstillingsforsøget ikke længere er aktivt.
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
        #Hvis cursor ikke har ændret i præcis 1 row, kastes en fejlbesked.

        db.commit()

        return f"""
        <mixhtml mix-redirect="/login?message={getattr(languages, f'{lan}_reset_password_success')}"></mixhtml>
        """, 200
        #Ved succes, redirectes brugeren til login, så de nu kan logge ind med deres nye password

    except Exception as ex:
        return f"""
        <mixhtml mix-update=".form-feedback">
          <div class='alert error'>{getattr(languages, f'{lan}_reset_password_error').replace("{str(ex)}", str(ex))}</div>
        </mixhtml>
        <mixhtml mix-function="resetButtonText">
          {getattr(languages, f'{lan}_reset_password_button_default')}
        </mixhtml>
        """, 500
        #Hvis der opstår nogle fejl under processen, vises password error teksten i form-feedback.

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
# ***verify get***
#Denne route tilgås ved at brugeren klikker på verification key'en der er blevet sendt til deres mail ved signup.
#Den bruges til at bekræfte brugerens email addresse efter signup.
#Flowet er:
    #Brugeren opretter en konto
        #Der indsættes en verification key i users tabellen i kolonnen user_verification_key
    #Der sendes et link til at verify via email
    #Brugeren trykker på verification linket i emailen hvilket sender en get request til denne route
        #som så opdatere brugeren til at være verified ved at sætte user_verified fra 0 - 1 og sletter verification nøglen fra user_verfication_key 
@app.get("/verify/<verification_key>")
def verify_user(verification_key):
    try:
        verification_key = x.validate_verification_key(verification_key)
        #Verification key'en sendes med i get requesten som udløses via klik på verification link i emailen
        #Vi validere den via funktion fra x.py som tjekker at det er et gyldigt uuid.

        db, cursor = x.db()

        q = "SELECT * FROM users WHERE user_verification_key = %s AND user_verified = 0"
        cursor.execute(q, (verification_key,))
        user = cursor.fetchone()
        #Query der Tjekker om en bruger med denne nøgle findes og ikke allerede er verificeret

        if not user:
            return "Verification key is invalid or already in use", 400
        #Hvis key'en ikke findes, er forkert, eller allerede er valideret kastes en fejl.

        q = """
        UPDATE users
        SET user_verified = 1,
            user_verification_key = NULL
        WHERE user_verification_key = %s
        """
        #Denne query opdatere user_verified til 1 fra 0, og fjerner verificaton key'en, da den nu er brugt.
        #Vi bruger WHERE til at bestemme hvilken række dette skal gøres i, ud fra den pågældende verification key
        cursor.execute(q, (verification_key,))
        db.commit()

        return render_template("login.html", message="Your email is now verified. You can log in."), 200
        #Ved succes, redirectes brugeren til login siden, med en besked om at det er veryfied og kan logge ind.

    except Exception as ex:
        return str(ex), 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
# ***profile get***
@app.get("/profile")
@app.get("/profile/<lan>")
def profile(lan="en"):
    #Denne route tilgås når brugeren går til profile pagen.
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        user = x.validate_user_logged()
        #Tjek at brugeren er logged in - dette gøres også via g objektet så måske overkill
        profile_message = request.args.get("profile_message", "")
        #Hvis brugeren er blevet sendt til profile med en besked - hent den og gem den i en variabel
        #Dette kan være efter at have redigeret sin profil - så sendes succesbeskeden med
        #Der sendes som udgangspunkt ingen beskeder når brugeren bare tilgår profile
        item_message = request.args.get("item_message", "")
        #Samme som overstående, hvis brugeren redirectes til profile efter f.eks. edit_item

        db, cursor = x.db()

        q_items = """
        SELECT * FROM items
        WHERE item_user_fk = %s AND item_blocked_at = 0
        ORDER BY item_created_at DESC
        """
        #query der henter alle itesm brugeren har oprettet
        #Vi tjekker hvilke items der høre til den pågældende bruger ved at se om item_user_fk matcher user_pk
        #Vi tjekker også at et item ikke er blocked
        #Items sorteres i "faldende" altså de nyeste uploadede items vises først og det ældste til sidst.
        cursor.execute(q_items, (user["user_pk"],))
        items = cursor.fetchall()

        for item in items:
            #For loop der køre igennem hvert item vi hentede i overstående query
            q_images = "SELECT * FROM images WHERE image_item_fk = %s"
            #For hvert item, hentes de tilhørende images fra images tabellen - hvor image_item_fk har relation til item_pk 
            cursor.execute(q_images, (item["item_pk"],))
            item["images"] = cursor.fetchall()
            #items variablen fra første query er en liste over samtlige items der er hentet
            #Dette for loop indsætter så billederne i hvert item, altså hvert element i items listen.

        return render_template(
            "profile.html",
            user=user,
            #Vi sender user objektet med som vi har hentet fra session
            #Det gør vi så vi kan vise brugeren en oversigt over deres personlige info.
            items=items,
            #Når vi sender items med, så sender vi alle items med tilhørende billeder. Derfor behøver vi ikke også at sende images med, da de allerede er en del af items variablen.
            active_profile="active",
            #Til nav'en, så det vides om hvorvidt der skal vises profile eller login alt efter om brugeren er logget eller ej
            title=getattr(languages, f"{lan}_profile_title"),
            form=None,
            #Ved rendering af profile nulstiller vi forms der er på pagen
            errors=None,
            #Vi nulstiller også errors
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
    #Når brugeren klikker på profile edit linket, sendes en get request til denne route
    #Denne route renderer edit_profile.html
    try:
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed:
            lan = "en"

        if "user" not in session:
            return redirect(url_for("show_login")), 302
        #Tjek om brugeren er logget ind, hvis ikke redirect til log in.
        user = session["user"]
        #gemmer user objektet fra session i en variabel
        return render_template(
            "edit_profile.html",
            user=user,
            #Sender user info med
            old_values=user,
            # Sender brugerens nuværende værdier med, så inputfelterne i formen er forudfyldt
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
        # Vi opretter en variabel, som indeholder en liste af tuples.
        # Hver tuple består af:
        # - navnet på et inputfelt (f.eks. "user_username")
        # - en reference til den valideringsfunktion, der skal bruges til det felt (f.eks. x.validate_user_username)
        # Dette gør det nemt at loope igennem alle felter og validere dem i et samlet loop senere.


        values, form_errors = {}, {}
        # Vi opretter to tomme dicts:
        # values skal gemme de gyldige (validerede) inputværdier
        # form_errors skal gemme eventuelle fejlbeskeder ved validering

        for field, fn in validators:
            # Vi looper gennem hver tuple i validators-listen
            # field = navnet på feltet i HTML-formen, fx "user_name"
            # fn = tilhørende valideringsfunktion, fx x.validate_user_name

            try:
                values[field] = fn()
                # Vi kalder valideringsfunktionen (fn()), som selv henter data fra request.form - fordi vi i hver validations funktion i x.py, udtrækker værdien af inputfeltet:     address = request.form.get("item_address", "").strip()
                # Hvis validering lykkes, gemmer vi den returnerede værdi i values[field]
                # Fx: values["user_name"] = "John"
            except Exception as ex:
                form_errors[field] = str(ex)
                # Hvis valideringen fejler, gemmer vi fejlbeskeden i form_errors[field]
                # Fx: form_errors["user_name"] = "Name must be at least 2 characters"

            # Hvis der er nogle valideringsfejl gemt i form_errors-dictionaryen
        if form_errors:
                # Opret en HTML ul-liste med klassen 'alert error'
                # Vi laver en liste af <li> fejlbeskeder og samler dem med .join()
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
        #Opdatere users tabellen med brugerens nye inputs som blev gemt i values.
        # Opdater session, fordi user er blevet ændret.
        session["user"].update(values)

        return f"""
        <mixhtml mix-redirect="/profile/{lan}?profile_message={getattr(languages, f'{lan}_profile_message_success')}"></mixhtml>
        """, 200
        #Ved succes redirectes der til profile med en succes message

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
    #Trykkes der på dele profile, sendes der en get request til denne route
    languages_allowed = ["en", "dk"]
    if lan not in languages_allowed: lan = "en"

    if "user" not in session:
        return redirect(url_for("show_login")), 302

    return render_template(
        "delete_profile.html",
        message="",
        user_password_error="",
        #user_password_error skal ikke vises når brugeren tilgår delete_profile første gang
        #Men efter post requesten er sendt, redirectes der igen til delete_profile.html, og her skal beskeden vises, hvis der opstår en.
        #Derfor er sendes denne variabel med
        old_values={},
        lan=lan,
        languages=languages
    ), 200


##############################
# ***profile delete***
@app.post("/profile/delete/<lan>")
def confirm_delete_profile(lan):
    try:
        #Denne post route tilgås, efter en bruger har indtastet sit password og sendt request fra delete_profile.html
        languages_allowed = ["en", "dk"]
        if lan not in languages_allowed: lan = "en"

        if "user" not in session:
            return redirect(url_for("show_login")), 302

        user_pk = session["user"]["user_pk"]
        user_email = session["user"]["user_email"]
        user_password = request.form.get("user_password", "").strip()
        #Vi trækker user_pk og user_email ud af session objektet
        #Vi får user_password fra formen der aktivere denne post request, fra delete_profile.html

        db, cursor = x.db()

        # Tjek password
        cursor.execute("SELECT user_password FROM users WHERE user_pk = %s", (user_pk,))
        result = cursor.fetchone()
        #Vi tjekker at passwordet brugeren sendte med i requesten passer

        if not result or not check_password_hash(result["user_password"], user_password):
            return f"""
            <mixhtml mix-update=".form-feedback">
              <div class='alert error'>{getattr(languages, f"{lan}_delete_profile_invalid_password")}</div>
            </mixhtml>
            """, 403
            #Hvis passwordet ikke stemmer overens med det i databasen, kast fejlbesked

        # Soft delete
        timestamp = int(time.time())
        cursor.execute("UPDATE users SET user_deleted_at = %s WHERE user_pk = %s", (timestamp, user_pk))
        db.commit()
        #Ved succes opdateres user_deleted_at kolonnen med et unix timestamp
        #Det er et soft delete, så profilen findes stadig i databasen, men i frontenden vises det aldrig, fordi vi tjekker user_deleted_at kolonnen før login og andre scenarier.

        x.send_delete_confirmation(user_email)
        session.pop("user", None)
        #email sendes med information om slettet profil til brugerens email
        #Vi fjerner user fra session

        return f"""
        <mixhtml mix-redirect="/login/{lan}?profile_deleted={getattr(languages, f'{lan}_delete_profile_success')}"></mixhtml>
        """, 200
        #Brugeren redirectes til login, med en besked om at profilen er slettet.

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
# ***search get***
@app.get("/search")
def search():
    #Get route der aktiveres når nogen går til /search?q=søgeord
    try:
        search_for = request.args.get("q", "").strip()
        #Henter søgestrengen fra URL'en. F.eks. /search?q=enghave og gem i search_for variabel.
        search_for = x.validate_search_query(search_for)
        #Valider søgestrengen - tjekker at den strengen ikke er længere end 50characters.
        #Jeg tænkte om man burde forhindre at brugeren kan skrive f.eks DROP DATABASE og søge efter dette
            #Men fordi vi bruger paramatiserede queries, bliver værdien af search_for aldrig en direkte del af SQL strengen
            #Den bliver sat ind som et parameter og vil derfor blive behandlet som en værdi og ikke som SQL - derfor er den sikret mod dette.

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
        #Query der henter alt fra items
        #Subquery der henter et billede pr. item - det bliver det første billede fra item_image resultatet
        #Der tjekkes at item ikke er blokeret
        #Og vi søger efter items, hvor item_name starter med søgestrengen.

        cursor.execute(q, (f"{search_for}%",))
        #Vi indsætter search_for(søgestringen) og dette gøres via en fstring, så vi kan indsætte variablen.
        rows = cursor.fetchall()
        # Vi returnerer resultatet som JSON med jsonify().
        # Flask konverterer listen af dicts (rækker fra databasen) til et JSON-array.
        # Dette JSON-array bliver hentet af frontendens fetch()-kald i search() funktionen i JavaScript.
        # JavaScript bruger så response.json() til at parse dataen og gennemløber den
        # med forEach for at vise søgeresultater dynamisk i DOM'en – uden reload.
        return jsonify(rows), 200

    except Exception as ex:
        ic(ex)
        return "x", 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
