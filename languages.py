# ------------------------
# Login - copy from login.html
# ------------------------
en_login_title = "Login"
dk_login_title = "Log ind"

en_login_email_placeholder = "Email"
dk_login_email_placeholder = "Email"

en_login_email_title = "Please enter a valid email address"
dk_login_email_title = "Indtast en gyldig emailadresse"

en_login_password_placeholder = "Password"
dk_login_password_placeholder = "Adgangskode"

en_login_password_title = "Password must be between 2 and 20 characters"
dk_login_password_title = "Adgangskoden skal være mellem 2 og 20 tegn"

en_login_button = "Login"
dk_login_button = "Log ind"

en_login_forgot = "Forgot your password?"
dk_login_forgot = "Glemt din adgangskode?"

# ------------------------
# Login - copy sent to login.html (from routes)
# ------------------------
en_login_error_verify_email = "Please verify your email before logging in."
dk_login_error_verify_email = "Bekræft venligst din email, før du logger ind."

en_login_error_blocked = "Your account is blocked."
dk_login_error_blocked = "Din konto er blevet blokeret."

en_login_error_not_found = "User not found"
dk_login_error_not_found = "Bruger blev ikke fundet"

en_login_error_credentials = "Invalid credentials"
dk_login_error_credentials = "Forkert loginoplysninger"

en_login_error_generic = "Something went wrong: {str(ex)}"
dk_login_error_generic = "Noget gik galt: {str(ex)}"

en_signup_success_verify = "Thank you for signing up. Please verify your email before logging in."
dk_signup_success_verify = "Tak for din tilmelding. Bekræft venligst din email, før du logger ind."

en_verify_success = "Your email is now verified. You can log in."
dk_verify_success = "Din email er nu bekræftet. Du kan logge ind."

en_reset_success = "Password updated. You can now log in."
dk_reset_success = "Adgangskode opdateret. Du kan nu logge ind."

en_delete_success = "Your account has been deleted."
dk_delete_success = "Din konto er blevet slettet."

# ------------------------
# Signup - copy from signup.html
# ------------------------

en_signup_title = "Signup"
dk_signup_title = "Tilmeld dig"

en_signup_username_placeholder = "Username"
dk_signup_username_placeholder = "Brugernavn"

en_signup_username_title = "Username must be between 2 and 20 characters, letters and numbers only"
dk_signup_username_title = "Brugernavn skal være mellem 2 og 20 tegn, kun bogstaver og tal"

en_signup_firstname_placeholder = "First name"
dk_signup_firstname_placeholder = "Fornavn"

en_signup_firstname_title = "First name must be between 2 and 20 characters, letters only"
dk_signup_firstname_title = "Fornavn skal være mellem 2 og 20 tegn, kun bogstaver"

en_signup_lastname_placeholder = "Last name"
dk_signup_lastname_placeholder = "Efternavn"

en_signup_lastname_title = "Last name must be between 2 and 20 characters, letters only"
dk_signup_lastname_title = "Efternavn skal være mellem 2 og 20 tegn, kun bogstaver"

en_signup_email_placeholder = "Email"
dk_signup_email_placeholder = "Email"

en_signup_email_title = "Enter a valid email (e.g. test@example.com)"
dk_signup_email_title = "Indtast en gyldig email (f.eks. test@eksempel.dk)"

en_signup_password_placeholder = "Password"
dk_signup_password_placeholder = "Adgangskode"

en_signup_password_title = "Password must be between 2 and 20 characters"
dk_signup_password_title = "Adgangskode skal være mellem 2 og 20 tegn"

en_signup_button_default = "Signup"
dk_signup_button_default = "Tilmeld"

en_signup_button_await = "Signing up..."
dk_signup_button_await = "Tilmelder..."

# ------------------------
# Signup - copy sent via app.py
# ------------------------

en_signup_success = "Thank you for signing up. Please verify your email before logging in."
dk_signup_success = "Tak for din tilmelding. Bekræft venligst din e-mail før du logger ind."

en_signup_username_invalid = "Username must be 2–20 characters and not already taken."
dk_signup_username_invalid = "Brugernavn skal være 2–20 tegn og må ikke være i brug."

en_signup_first_name_invalid = "First name must be 2–20 characters."
dk_signup_first_name_invalid = "Fornavn skal være 2–20 tegn."

en_signup_last_name_invalid = "Last name must be 2–20 characters."
dk_signup_last_name_invalid = "Efternavn skal være 2–20 tegn."

en_signup_email_invalid = "Invalid email."
dk_signup_email_invalid = "Ugyldig email."

en_signup_password_invalid = "Password must be 2–20 characters."
dk_signup_password_invalid = "Password skal være 2–20 tegn."

en_signup_email_exists = "This email is already in use."
dk_signup_email_exists = "Denne email er allerede i brug."

en_signup_username_exists = "This username is already in use."
dk_signup_username_exists = "Dette brugernavn er allerede i brug."

en_signup_unknown_error = "Unknown error: {str(ex)}"
dk_signup_unknown_error = "Ukendt fejl: {str(ex)}"


# ------------------------
# Profile - copy from profile.html
# ------------------------

en_profile_title = "Profile"
dk_profile_title = "Profil"

en_profile_personal_info = "Personal info"
dk_profile_personal_info = "Personlige oplysninger"

en_profile_username = "Username"
dk_profile_username = "Brugernavn"

en_profile_name = "Name"
dk_profile_name = "Navn"

en_profile_email = "Email"
dk_profile_email = "Email"

en_profile_member_since = "Member since"
dk_profile_member_since = "Medlem siden"

en_profile_edit = "Edit profile"
dk_profile_edit = "Rediger profil"

en_profile_delete = "Delete profile"
dk_profile_delete = "Slet profil"

en_profile_upload_spot = "Upload a spot"
dk_profile_upload_spot = "Upload et spot"

en_profile_your_spots = "Your spots"
dk_profile_your_spots = "Dine spots"

en_profile_price = "Price:"
dk_profile_price = "Pris:"

en_profile_address = "Address:"
dk_profile_address = "Adresse:"

en_profile_edit_spot = "Edit spot"
dk_profile_edit_spot = "Rediger spot"

en_profile_delete_image = "Delete image"
dk_profile_delete_image = "Slet billede"

# Bemærk: "Delete item {{ item.item_name }}" er dynamisk — du skal håndtere det i app.py.

en_profile_delete_item_btn = "Delete spot"
dk_profile_delete_item_btn = "Slet spot"


# ------------------------
# Profile - copy sent to profile.html (from routes)
# ------------------------
# ✅ Success messages (query param-based)
en_profile_message_success = "Your profile has been updated."
dk_profile_message_success = "Din profil er blevet opdateret."

en_profile_item_success = "Your item has been saved successfully."
dk_profile_item_success = "Dit spot er blevet gemt."

# ✅ Item updated successfully
en_profile_item_updated = "Item updated successfully"
dk_profile_item_updated = "Spot er blevet opdateret"

# ✅ Spot deleted successfully
en_profile_item_deleted = "Spot deleted successfully"
dk_profile_item_deleted = "Spot er blevet slettet"

# ✅ Image deleted successfully
en_profile_image_deleted = "Image deleted successfully"
dk_profile_image_deleted = "Billede er blevet slettet"

# ❌ Error messages
en_profile_item_error = "Something went wrong: {str(ex)}"
dk_profile_item_error = "Noget gik galt: {str(ex)}"

# ------------------------
# Edit profile - copy from edit_profile.html
# ------------------------

en_edit_profile_title = "Edit Profile"
dk_edit_profile_title = "Rediger profil"

en_edit_profile_username_placeholder = "Username"
dk_edit_profile_username_placeholder = "Brugernavn"

en_edit_profile_username_title = "Username must be 2–20 characters. Letters, numbers and underscores only."
dk_edit_profile_username_title = "Brugernavn skal være 2–20 tegn. Kun bogstaver, tal og understregninger tilladt."

en_edit_profile_firstname_placeholder = "First name"
dk_edit_profile_firstname_placeholder = "Fornavn"

en_edit_profile_firstname_title = "First name must be 2–20 letters only."
dk_edit_profile_firstname_title = "Fornavn skal være 2–20 bogstaver."

en_edit_profile_lastname_placeholder = "Last name"
dk_edit_profile_lastname_placeholder = "Efternavn"

en_edit_profile_lastname_title = "Last name must be 2–20 letters only."
dk_edit_profile_lastname_title = "Efternavn skal være 2–20 bogstaver."

en_edit_profile_email_placeholder = "Email"
dk_edit_profile_email_placeholder = "Email"

en_edit_profile_email_title = "Enter a valid email address like example@example.com"
dk_edit_profile_email_title = "Indtast en gyldig e-mail, fx eksempel@eksempel.dk"

en_edit_profile_button_default = "Save changes"
dk_edit_profile_button_default = "Gem ændringer"

en_edit_profile_button_await = "Saving..."
dk_edit_profile_button_await = "Gemmer..."

en_edit_profile_cancel = "Cancel"
dk_edit_profile_cancel = "Annuller"

# ------------------------
# Delete profile - copy from delete_profile.html
# ------------------------

en_delete_profile_title = "Delete Profile"
dk_delete_profile_title = "Slet profil"

en_delete_profile_password_placeholder = "Enter your password to confirm"
dk_delete_profile_password_placeholder = "Indtast din adgangskode for at bekræfte"

en_delete_profile_password_title = "Password must be between 2 and 20 characters."
dk_delete_profile_password_title = "Adgangskode skal være mellem 2 og 20 tegn."

en_delete_profile_button_default = "Delete my account"
dk_delete_profile_button_default = "Slet min konto"

en_delete_profile_button_await = "Deleting..."
dk_delete_profile_button_await = "Sletter..."

en_delete_profile_cancel = "Cancel"
dk_delete_profile_cancel = "Annuller"


# ------------------------
# Delete profile - copy sent to delete_profile.html (from routes)
# ------------------------
en_delete_profile_invalid_password = "Invalid password. Try again."
dk_delete_profile_invalid_password = "Ugyldig adgangskode. Prøv igen."

en_delete_profile_success = "Your account has been deleted."
dk_delete_profile_success = "Din konto er blevet slettet."

en_delete_profile_unknown_error = "Something went wrong: {str(ex)}"
dk_delete_profile_unknown_error = "Noget gik galt: {str(ex)}"

# ------------------------
# Upload item form - HTML copy
# ------------------------

en_upload_item_name_placeholder = "Name"
dk_upload_item_name_placeholder = "Navn"

en_upload_item_name_title = "Name must be 2–60 characters. Letters, numbers and simple punctuation allowed."
dk_upload_item_name_title = "Navn skal være 2–60 tegn. Bogstaver, tal og enkel tegnsætning tilladt."

en_upload_item_description_placeholder = "Description"
dk_upload_item_description_placeholder = "Beskrivelse"

en_upload_item_description_title = "Description must be 5–400 characters. Letters, numbers and punctuation allowed."
dk_upload_item_description_title = "Beskrivelse skal være 5–400 tegn. Bogstaver, tal og tegnsætning tilladt."

en_upload_item_price_placeholder = "Price"
dk_upload_item_price_placeholder = "Pris"

en_upload_item_price_title = "Enter a price like 199.95. Max 6 digits before dot and 2 after."
dk_upload_item_price_title = "Indtast en pris som 199.95. Max 6 cifre før punktum og 2 efter."

en_upload_item_address_placeholder = "Address"
dk_upload_item_address_placeholder = "Adresse"

en_upload_item_address_title = "Address must be 5–100 characters."
dk_upload_item_address_title = "Adressen skal være 5–100 tegn."

en_upload_item_lat_placeholder = "Latitude"
dk_upload_item_lat_placeholder = "Breddegrad"

en_upload_item_lat_title = "Latitude must be between -90 and 90 (e.g. 55.6761)."
dk_upload_item_lat_title = "Breddegrad skal være mellem -90 og 90 (f.eks. 55.6761)."

en_upload_item_lon_placeholder = "Longitude"
dk_upload_item_lon_placeholder = "Længdegrad"

en_upload_item_lon_title = "Longitude must be between -180 and 180 (e.g. 12.5683)."
dk_upload_item_lon_title = "Længdegrad skal være mellem -180 og 180 (f.eks. 12.5683)."

en_upload_item_file_title = "Please select between 1 and 3 images (PNG, JPG, JPEG, GIF, or WEBP)"
dk_upload_item_file_title = "Vælg mellem 1 og 3 billeder (PNG, JPG, JPEG, GIF eller WEBP)"

en_upload_item_button_default = "Upload skate spot"
dk_upload_item_button_default = "Upload skate spot"

en_upload_item_button_await = "Uploading..."
dk_upload_item_button_await = "Uploader..."

# Upload item - success
en_upload_item_success = "✅ Spot uploaded successfully"
dk_upload_item_success = "✅ Spot er blevet uploadet"

en_upload_item_error = "Something went wrong: {str(ex)}"
dk_upload_item_error = "Noget gik galt: {str(ex)}"

# ------------------------
# Edit item - HTML copy
# ------------------------

en_edit_item_title = "Edit your spot"
dk_edit_item_title = "Rediger dit spot"

en_edit_item_name_placeholder = "Name"
dk_edit_item_name_placeholder = "Navn"

en_edit_item_name_title = "Name must be 2–60 characters. Letters, numbers and simple punctuation allowed."
dk_edit_item_name_title = "Navn skal være 2–60 tegn. Bogstaver, tal og enkel tegnsætning tilladt."

en_edit_item_description_placeholder = "Description"
dk_edit_item_description_placeholder = "Beskrivelse"

en_edit_item_description_title = "Description must be 5–400 characters. Letters, numbers and punctuation allowed."
dk_edit_item_description_title = "Beskrivelse skal være 5–400 tegn. Bogstaver, tal og tegnsætning tilladt."

en_edit_item_price_placeholder = "Price"
dk_edit_item_price_placeholder = "Pris"

en_edit_item_price_title = "Enter a price like 199.95. Max 6 digits before dot and 2 after."
dk_edit_item_price_title = "Indtast en pris som 199.95. Max 6 cifre før punktum og 2 efter."

en_edit_item_address_placeholder = "Address"
dk_edit_item_address_placeholder = "Adresse"

en_edit_item_address_title = "Address must be 5–100 characters."
dk_edit_item_address_title = "Adressen skal være 5–100 tegn."

en_edit_item_lat_placeholder = "Latitude"
dk_edit_item_lat_placeholder = "Breddegrad"

en_edit_item_lat_title = "Latitude must be between -90 and 90 (e.g. 55.6761)."
dk_edit_item_lat_title = "Breddegrad skal være mellem -90 og 90 (f.eks. 55.6761)."

en_edit_item_lon_placeholder = "Longitude"
dk_edit_item_lon_placeholder = "Længdegrad"

en_edit_item_lon_title = "Longitude must be between -180 and 180 (e.g. 12.5683)."
dk_edit_item_lon_title = "Længdegrad skal være mellem -180 og 180 (f.eks. 12.5683)."

en_edit_item_button_default = "Save changes"
dk_edit_item_button_default = "Gem ændringer"

en_edit_item_button_await = "Saving..."
dk_edit_item_button_await = "Gemmer..."

en_edit_item_cancel = "Cancel"
dk_edit_item_cancel = "Annuller"

# ------------------------
# Edit item - copy sent via app.py
# ------------------------

en_profile_item_updated = "Item updated successfully"
dk_profile_item_updated = "Spot er blevet opdateret"

en_profile_item_error = "Something went wrong: {str(ex)}"
dk_profile_item_error = "Noget gik galt: {str(ex)}"

# ------------------------
# Delete item - copy sent via app.py
# ------------------------

en_profile_item_deleted = "✅ Spot deleted successfully"
dk_profile_item_deleted = "✅ Spot er blevet slettet"














# ------------------------
# Forgot password - copy from forgot_password.html
# ------------------------
# (to be filled in next step)

# ------------------------
# Forgot password - copy sent to forgot_password.html (from routes)
# ------------------------
# (to be filled in next step)

# ------------------------
# Reset password - copy from reset_password.html
# ------------------------
# (to be filled in next step)

# ------------------------
# Reset password - copy sent to reset_password.html (from routes)
# ------------------------
# (to be filled in next step)

# ------------------------
# Upload item - copy from upload_item_form.html
# ------------------------
# (to be filled in next step)

# ------------------------
# Upload item - copy sent to upload_item_form.html (from routes)
# ------------------------
# (to be filled in next step)

# ------------------------
# Admin - copy from view_admin.html
# ------------------------
# (to be filled in next step)

# ------------------------
# Admin - copy sent to view_admin.html (from routes)
# ------------------------
# (to be filled in next step)
