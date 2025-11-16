import streamlit as st

st.set_page_config(
    page_title="Simulazioni Finanziarie",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Simulazioni Finanziarie")
st.markdown("""
<style>
    /* 1. Il tuo codice per nascondere Menu e Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 2. Codice specifico per nascondere il tasto DEPLOY */
    /* Questo selettore punta alla toolbar in alto a destra */
    div[data-testid="stToolbar"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }
    /* Un fallback se il precedente fallisce */
    [data-testid="stDeployButton"] {
        display: none !important;
    }

    /* --- 3. Allineamento Altezza (Metodo robusto) --- */
    /* Questo forza le colonne ad avere la stessa altezza di base */
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }
    
    /* Questo forza il contenitore *interno* della colonna a riempirla */
    div[data-testid="stHorizontalBlock"] > div[data-testid^="stVerticalBlock"] {
         height: 100%;
    }

    /* Questo forza gli elementi (Alert, Info, Button) a riempire il contenitore */
    div[data-testid="stAlert"],
    div[data-testid="stInfo"],
    div[data-testid="stError"],
    div[data-testid="stWarning"],
    div[data-testid="stButton"] {
        height: 100%;
    }
    
    /* Questo forza il pulsante VERO E PROPRIO a riempire il suo contenitore */
    div[data-testid="stButton"] > button {
        height: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.header("Benvenuto nel tuo centro di simulazione finanziaria.")
st.subheader("Usa il menu nella barra laterale (a sinistra) per scegliere quale strumento avviare:")

st.info(
    """
    - **💰 Simulatore Pensione:** Calcola la stima della tua pensione futura (sistema contributivo).
    - **🔥 Simulatore FIRE:** Calcola la tua data di indipendenza finanziaria.
    """
)

warning_html = """
<div style="background-color: rgba(255, 251, 235, 0.8); border-left: 5px solid #F7B538; padding: 1rem; border-radius: 0.25rem; margin-top: 1rem; margin-bottom: 1rem; color: #da9209;">
    <p style="margin-bottom: 0.5rem;">
        <span style="color: #B91C1C; font-weight: bold;">AVVERTENZA IMPORTANTE SULL'AFFIDABILITÀ</span>
    </p>
    <p style="margin: 0;">
        I simulatori presenti in questa applicazione (Pensione e FIRE) forniscono stime puramente matematiche e <b>non costituiscono una consulenza finanziaria o previdenziale.</b>
    </p>
    <br>
    <p style="margin: 0;">
        I calcoli si basano interamente sulle ipotesi inserite (crescita della RAL, tassi di interesse, andamento del PIL, ecc.). Queste variabili sono per natura <b>imprevedibili</b> e soggette a grande incertezza.
    </p>
    <br>
    <p style="margin-bottom: 0.5rem;">
        <span style="color: #B91C1C; font-weight: bold;">NON FARE AFFIDAMENTO ESCLUSIVO SU QUESTI NUMERI:</span>
    </p>
    <ul style="margin: 0; padding-left: 1.5rem;">
        <li>I risultati possono <b>differire significativamente</b> dalla tua situazione reale futura.</li>
        <li>Usali esclusivamente per farti un'<b>idea di massima</b> dei numeri in gioco e per comprendere l'impatto delle diverse variabili.</li>
        <li><b>Non basare decisioni</b> finanziarie, di investimento o di carriera su queste simulazioni.</li>
    </ul>
    <br>
    <p style="margin: 0;">
        Si raccomanda di consultare sempre un professionista qualificato e di fare riferimento agli strumenti ufficiali (come "La Mia Pensione Futura" sul sito INPS) per proiezioni più attendibili.
    </p>
</div>
"""

st.markdown(warning_html, unsafe_allow_html=True)
