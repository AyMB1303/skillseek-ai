FROM python:3.12-slim

WORKDIR /app

# Dependances systeme :
#  - libpq-dev / gcc : compilation du connecteur PostgreSQL
#  - tesseract-ocr (+ langues fra/eng) : reconnaissance optique des CV scannes
#  - poppler-utils : conversion PDF -> image, requise par pdf2image
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Modele linguistique francais de spaCy
RUN python -m spacy download fr_core_news_sm

# Modele de plongements telecharge a la construction de l'image :
# evite un premier appel lent en production.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
