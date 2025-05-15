# Brug en letvægts Python-base
FROM python:3.9-slim

# Sæt arbejdsmappen i containeren
WORKDIR /app

# Kopiér først requirements og installer dependencies (god caching-praksis)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Kopiér resten af projektet ind
COPY . .

CMD flask run --host=0.0.0.0 --port=80 --debug --reload

