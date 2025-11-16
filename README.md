# Simulatore Finanziario Multi-Pagina

Questa è un'applicazione web multi-pagina costruita con Streamlit che ospita vari strumenti di simulazione finanziaria per la pianificazione personale.

## ⚠️ Avvertenza Importante sull'Affidabilità
> I simulatori presenti in questa applicazione (Pensione e FIRE) forniscono stime puramente matematiche e **non costituiscono una consulenza finanziaria o previdenziale.**
>
> I calcoli si basano interamente sulle ipotesi inserite (crescita della RAL, tassi di interesse, andamento del PIL, ecc.). Queste variabili sono per natura **imprevedibili** e soggette a grande incertezza.
>
> **NON FARE AFFIDAMENTO ESCLUSIVO SU QUESTI NUMERI:**
>
> * I risultati possono **differire significativamente** dalla tua situazione reale futura.
>
> * Usali esclusivamente per farti un'**idea di massima** dei numeri in gioco e per comprendere l'impatto delle diverse variabili.
>
> * **Non basare decisioni** finanziarie, di investimento o di carriera su queste simulazioni.
>
> Si raccomanda di consultare sempre un professionista qualificato e di fare riferimento agli strumenti ufficiali (come "La Mia Pensione Futura" sul sito INPS) per proiezioni più attendibili.

## Funzionalità

Questa applicazione contiene i seguenti simulatori:

1. **💰 Simulatore Pensione (Contributivo):**

   * Stima l'assegno pensionistico futuro per chi rientra nel sistema contributivo puro (post 1996).

   * Permette di simulare scenari complessi, come l'interruzione dei contributi, la variazione dell'età pensionabile (automatica o manuale) e l'impatto di ipotesi macroeconomiche (PIL, crescita RAL).

2. **🔥 Simulatore FIRE (Financial Independence, Retire Early):**

   * *(Aggiungi qui la descrizione del tuo simulatore FIRE)*

## Stack Tecnologico

* **Python 3.11**

* **Streamlit** (per la UI web)

* **Docker** (per la containerizzazione)

## Struttura del Progetto

Il progetto utilizza la struttura multi-pagina nativa di Streamlit:

```

/financial-simulators/
├── Home.py             \# Script principale (landing page)
├── pages/
│   ├── 1\_Simulatore\_Pensione.py
│   └── 2\_Simulatore\_FIRE.py
├── Dockerfile          \# Definizioni per il container
├── requirements.txt    \# Dipendenze Python
└── .dockerignore       \# File da ignorare durante il build Docker

```

## Come Avviare (Sviluppo Locale)

1. **Clona il repository:**

```

git clone [URL\_DEL\_TUO\_REPOSITORY\_GIT]
cd financial-simulators

```

2. **Crea e attiva un ambiente virtuale (consigliato):**

```

python -m venv venv

# Su Windows

.\\venv\\Scripts\\activate

# Su macOS/Linux

source venv/bin/activate

```

3. **Installa le dipendenze:**

```

pip install -r requirements.txt

```

4. **Avvia l'app Streamlit:**
Il comando deve puntare allo script `Home.py`.

```

streamlit run Home.py

```

## Come Avviare (con Docker)

Assicurati di avere Docker installato e in esecuzione sulla tua macchina.

1. **Costruisci l'immagine Docker:**
Dalla cartella principale del progetto, esegui:

```

docker build -t financial-simulators .

```

2. **Avvia il container:**
Questo comando avvia il container, mappa la porta 8501 e lo esegue in background.

```

docker run -p 8501:8501 financial-simulators

```

3. **Accedi all'app:**
Apri il tuo browser e vai su `http://localhost:8501`
