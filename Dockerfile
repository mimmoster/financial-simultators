# Usa un'immagine Python ufficiale e leggera
FROM python:3.11-slim

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Copia prima il file dei requisiti
COPY requirements.txt .

# Installa i requisiti
RUN pip install --no-cache-dir -r requirements.txt

# Copia lo script della tua app
COPY . .

# Esponi la porta 8501, quella standard di Streamlit
EXPOSE 8501

# Comando per avviare l'app quando il container parte
CMD ["streamlit", "run", "🏠Home.py", "--server.port=8501", "--server.address=0.0.0.0"]