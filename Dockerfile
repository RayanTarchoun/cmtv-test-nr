FROM python:3.9-slim

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    bash \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Mettre à jour les certificats
RUN update-ca-certificates

# Mettre à jour pip vers une version spécifique
RUN python -m pip install pip==23.0.1 --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

# Mettre à jour pip avec l'option --trusted-host
RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

# Copier les dépendances Python dans le conteneur
COPY requirements.txt /app/requirements.txt

# Installer les dépendances Python avec l'option --trusted-host
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r /app/requirements.txt

# Copier les fichiers du projet dans le conteneur
WORKDIR /app
COPY . /app

# Définir le point d'entrée pour exécuter le script Python
ENTRYPOINT ["python"]
CMD ["cmtv-test-nr.py"]