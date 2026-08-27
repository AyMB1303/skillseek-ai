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

# Emplacement des modeles telecharges, deliberement place HORS du dossier
# personnel de root. Sans ces variables, la bibliotheque ecrit dans
# /root/.cache, que le compte sans privileges defini plus bas ne pourrait pas
# lire : le moteur semantique basculerait alors en repli sans rien signaler,
# et vingt-cinq points du bareme disparaitraient en silence.
ENV HF_HOME=/opt/modeles \
    SENTENCE_TRANSFORMERS_HOME=/opt/modeles

# Modele de plongements telecharge a la construction de l'image :
# evite un premier appel lent en production.
RUN mkdir -p /opt/modeles && python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Verification que les bibliotheques cohabitent correctement : mieux vaut
# echouer ici qu'au premier appel en production.
RUN python -c "import spacy, sklearn, pandas, numpy; \
    spacy.load('fr_core_news_sm'); \
    print(f'numpy {numpy.__version__}, spaCy et scikit-learn operationnels')"

COPY . .

# Compte sans privileges. Un processus compromis ne doit pas etre root dans
# son conteneur : root dans le conteneur est la premiere marche vers l'hote,
# et c'est la seule difference qui compte le jour ou une bibliotheque tierce
# se revele vulnerable. L'image du frontend le faisait deja ; celle-ci ne le
# faisait pas, par omission.
#
# Les dossiers ecrits en fonctionnement sont crees ET attribues ici. Les
# volumes montes plus tard heritent de cette appartenance : sans elle, le
# depot d'un CV echouerait sur un refus de permission.
RUN useradd --create-home --uid 1001 skillseek \
    && mkdir -p /app/uploads /app/exports /app/models \
    && chown -R skillseek:skillseek /app /opt/modeles

USER skillseek

EXPOSE 5000

# Sonde de vivacite : distingue un conteneur demarre d'un conteneur qui
# repond. Le delai de grace est long parce que le chargement de torch, de
# spaCy et du modele de plongements prend plusieurs dizaines de secondes.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health')" || exit 1

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
