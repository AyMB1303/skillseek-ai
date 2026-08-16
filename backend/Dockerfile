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

# PyTorch en version processeur uniquement.
# La version par defaut embarque les bibliotheques CUDA (environ 800 Mo)
# inutiles sans carte graphique : cette variante allege l'image et raccourcit
# nettement la construction.
RUN pip install --no-cache-dir \
    torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu

# numpy est fige en 1.x AVANT le reste des dependances : spaCy et thinc sont
# compiles contre cette version, et numpy 2 provoque une erreur
# d'incompatibilite binaire au chargement du modele linguistique.
RUN pip install --no-cache-dir "numpy==1.26.4"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Modele linguistique francais de spaCy
RUN python -m spacy download fr_core_news_sm

# Modele de plongements telecharge a la construction de l'image :
# evite un premier appel lent en production.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Verification que les bibliotheques cohabitent correctement : mieux vaut
# echouer ici qu'au premier appel en production.
RUN python -c "import spacy, sklearn, pandas, numpy; \
    spacy.load('fr_core_news_sm'); \
    print(f'numpy {numpy.__version__}, spaCy et scikit-learn operationnels')"

COPY . .

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
