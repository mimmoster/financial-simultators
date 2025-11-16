import streamlit as st
import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Simulatore Pensione Contributiva",
    page_icon="💰",
    layout="wide"
)

# --- CSS (DAL FILE UTENTE) ---
hide_streamlit_style = """
<style>
[data-testid="stDeployButton"] {visibility: hidden;}
[data-testid="main-menu-button"] {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# --- INIZIALIZZAZIONE SESSION STATE ---
if 'last_run_params' not in st.session_state:
    st.session_state.last_run_params = {}
if 'results' not in st.session_state:
    st.session_state.results = None

# --- FUNZIONI DI CALCOLO ---

def calcola_montante_futuro(eta_attuale, eta_fine_contribuzione, eta_pensionamento, 
                            montante_attuale, ral_attuale, ral_crescita, 
                            tasso_capitalizzazione, aliquota_contributiva):
    
    current_montante = montante_attuale
    current_ral = ral_attuale
    anni_lavorati = 0
    
    # Simula anno per anno fino all'età di pensionamento
    for eta_corrente in range(eta_attuale, eta_pensionamento):
        
        # 1. Rivalutazione (si applica al montante dell'anno precedente)
        current_montante *= (1 + tasso_capitalizzazione)
        
        # 2. Contribuzione (solo se si sta ancora lavorando)
        if eta_corrente < eta_fine_contribuzione:
            # Calcola la contribuzione sull'RAL dell'anno corrente
            contribuzione_annua = current_ral * aliquota_contributiva
            # Aggiungi al montante
            current_montante += contribuzione_annua
            
            # Aggiorna la RAL per l'anno successivo
            current_ral *= (1 + ral_crescita)
            anni_lavorati += 1
            
    return current_montante, anni_lavorati

def calcola_netto(pensione_lorda_annua, stima_addizionali=0.015):
    # Aliquote IRPEF 2024 (esempio)
    scaglioni = {
        28000: 0.23,
        50000: 0.35,
        float('inf'): 0.43
    }
    
    imposta_lorda = 0
    reddito_residuo = pensione_lorda_annua
    
    # Calcolo IRPEF progressiva
    imposta_scaglione_1 = min(max(0, pensione_lorda_annua), 28000) * scaglioni[28000]
    imposta_scaglione_2 = min(max(0, pensione_lorda_annua - 28000), 50000 - 28000) * scaglioni[50000]
    imposta_scaglione_3 = max(0, pensione_lorda_annua - 50000) * scaglioni[float('inf')]
    
    imposta_lorda = imposta_scaglione_1 + imposta_scaglione_2 + imposta_scaglione_3
    
    # Aggiungi addizionali stimate
    addizionali = pensione_lorda_annua * stima_addizionali
    
    imposta_totale = imposta_lorda + addizionali
    pensione_netta_annua = pensione_lorda_annua - imposta_totale
    
    return pensione_netta_annua

def stima_eta_pensionabile(eta_attuale):
    # Logica di stima MOLTO semplificata
    # (Calcolo anno nascita basato su oggi)
    anno_nascita = datetime.date.today().year - eta_attuale

    # FIX: Corretta la logica di stima (top-down) per rispettare le ipotesi
    # La logica deve andare dal più vecchio (o più certo) al più giovane
    
    if anno_nascita <= 1965: # Oltre 60 anni (nel 2025)
        return 67
    elif anno_nascita <= 1975: # Tra 50 e 60 anni (nati 1966-1975)
        return 68
    elif anno_nascita <= 1985: # Tra 40 e 50 anni (nati 1976-1985)
        return 69 # <-- Corretto a 69 per i 40enni (nati 1985)
    else: # Più giovani di 40 anni (nati dopo 1985)
        return 70

# --- DATI DI DEFAULT ---
DEFAULT_ETA_ATTUALE = 25
DEFAULT_MONTANTE_ATTUALE = 0.0
DEFAULT_RAL_ATTUALE = 28000.0
DEFAULT_RAL_CRESCITA = 0.02 # 2%
DEFAULT_TASSO_CAPITALIZZAZIONE = 0.015 # 1.5%
DEFAULT_ALIQUOTA = 0.33 # 33%
# Coefficienti 2025-2026 (età: coeff)
COEFFICIENTI_ATTUALI = {
    67: 0.05608,
    68: 0.05808,
    69: 0.06024,
    70: 0.06258,
    71: 0.06510,
    72: 0.06782
}
DEFAULT_VAR_COEFF = -10.0         # Default prudente (prevede peggioramento)

# --- TESTO GUIDA ---
# Spostato qui per essere riutilizzato
GUIDA_DETTAGLIATA = """
Questa app calcola una **stima di massima** della tua pensione, basandosi sul **metodo contributivo** (valido per chi ha iniziato a versare dopo il 1996). La logica è simile a un "conto di risparmio":

`Pensione Annua Lorda = Montante Finale * Coefficiente di Trasformazione`

Ecco come usare i parametri per stimare questi valori:

### 1. Dati Anagrafici e Lavorativi

* **Età attuale:** Serve come punto di partenza per il calcolo.
* **Età pensionamento (AdV):** Puoi usare la stima automatica (che si adegua all'aspettativa di vita, AdV) o inserirla manually. **Questa è l'età in cui incasserai la pensione.**
* **Interrompi contribuzione:** Questo slider ti permette di simulare scenari in cui smetti di lavorare (es. a 50 anni) ma incassi la pensione all'età di vecchiaia (es. 69).
    * **Se = Età Pensionamento:** L'app simula che tu lavori e versi contributi fino alla pensione.
    * **Se < Età Pensionamento:** L'app simula che tu smetta di versare contributi all'età indicata. Il tuo montante accumulato smette di crescere per i nuovi contributi, ma **continua a rivalutarsi** ogni anno (in base al PIL) fino alla pensione.

### 2. Dati Economici

* **Montante contributivo attuale:** È la base di partenza. È la somma (già rivalutata) di tutti i contributi versati fino ad oggi. Lo trovi sull'estratto conto INPS ("La Mia Pensione Futura"). Se inizi ora, lascia 0.
* **RALattuale:** Il tuo Reddito Annuo Lordo. L'app usa questo dato per calcolare i contributi futuri (il **33%** della RAL, per i dipendenti).
* **Crescita media RAL:** L'app usa questa percentuale per stimare l'aumento del tuo stipendio (e quindi dei tuoi contributi futuri) anno dopo anno.

### 3. Ipotesi Macroeconomiche

* **Tasso Capitalizzazione / PIL:** Questo è uno dei parametri **più importanti**. È il "tasso di interesse" annuo con cui l'INPS rivaluta il tuo montante totale accumulato. Si basa sulla media del PIL italiano degli ultimi 5 anni.
    * Un'ipotesi **1.5%** è considerata prudente/media.
    * Un'ipotesi **1.0%** è molto prudente (pessimistica).
    * Un'ipotesi **2.0%** è ottimistica.

### 4. Coefficienti (Avanzate)

* **Coefficiente di Trasformazione:** È la percentuale che **converte il tuo montante finale in pensione annua**. Dipende *solo* dall'età in cui vai in pensione.
* **Logica:** Più si vive a lungo (aspettativa di vita alta), più questo coefficiente **si abbassa**, perché lo stesso "tesoretto" deve essere distribuito su più anni.
* **Variazione stima:** Poiché tra 20-30 anni l'aspettativa di vita sarà più alta, i coefficienti attuali (che vedi come "base") saranno quasi certamente più bassi. Inserire **-10%** o **-20%** è un'ipotesi prudente e realistica per simulare questo peggioramento.

---

**Disclaimer:** Questa è una simulazione puramente matematica e non sostituisce una consulenza previdenziale o il servizio "La Mia Pensione Futura" dell'INPS. Le variabili future (PIL, inflazione, riforme) sono imprevedibili.
"""
# --- FINE TESTO GUIDA ---


# --- SIDEBAR (INPUTS - Codice utente) ---

st.sidebar.title("Configura la Simulazione")

st.sidebar.header("👤 Dati Anagrafici e Lavorativi")
eta_attuale = st.sidebar.number_input(
    "Età attuale", 
    min_value=18, max_value=70, 
    value=DEFAULT_ETA_ATTUALE, step=1
)

# --- Logica Età Pensionamento (AdV) ---
stima_adv_default = stima_eta_pensionabile(eta_attuale) # Ora stima 69 per 40 anni
default_manuale = stima_adv_default if stima_adv_default in COEFFICIENTI_ATTUALI else 67

usa_stima_adv = st.sidebar.toggle(
    "Usa stima Aspettativa di Vita (AdV)", 
    value=True, 
    help=f"Attivato: usa la stima automatica ({stima_adv_default} anni). Disattivato: imposta manualmente."
)

if usa_stima_adv:
    eta_pensionamento = stima_adv_default
    st.sidebar.markdown(f"Età pensionamento (stima AdV): **{eta_pensionamento} anni**")
    # Assicurati che l'età stimata sia nel dizionario, altrimenti usa la più vicina
    if eta_pensionamento not in COEFFICIENTI_ATTUALI:
        eta_pensionamento = min(COEFFICIENTI_ATTUALI.keys(), key=lambda k: abs(k-eta_pensionamento))
else:
    eta_pensionamento = st.sidebar.number_input(
        "Età di pensionamento (manuale)", 
        min_value=eta_attuale + 1, max_value=72, 
        value=default_manuale, 
        step=1
    )
# --- Fine Logica Età Pensionamento ---


# --- MODIFICA RICHIESTA: Slider Interruzione ---
eta_interruzione_slider = st.sidebar.slider(
    "Interrompi contribuzione all'età di", # Label aggiornato (rimosso "0 = ...")
    min_value=eta_attuale,                 # min aggiornato
    max_value=eta_pensionamento,           # max è l'età di pensione
    value=eta_pensionamento,               # default è l'età di pensione
    step=1,
    help="Imposta l'età in cui smetti di lavorare. Se imposti 48, l'anno 47 sarà l'ultimo anno di contributi."
)

# Logica Didascalia Aggiornata
eta_fine_contribuzione = eta_interruzione_slider # Assegnazione diretta

if eta_fine_contribuzione == eta_pensionamento:
    st.sidebar.caption("Contribuirai fino al pensionamento.")
else:
    st.sidebar.caption(f"Ultimo anno di contributi: {eta_fine_contribuzione - 1}. Rivalutazione passiva fino a {eta_pensionamento} anni.")
# --- Fine Modifica ---


st.sidebar.header("💰 Dati Economici")
montante_attuale = st.sidebar.number_input(
    "Montante contributivo attuale (€)", 
    min_value=0.0, 
    value=DEFAULT_MONTANTE_ATTUALE, 
    step=1000.0, format="%.2f"
)
ral_attuale = st.sidebar.number_input(
    "RALattuale (€)", 
    min_value=0.0, 
    value=DEFAULT_RAL_ATTUALE, 
    step=1000.0, format="%.2f"
)
ral_crescita = st.sidebar.slider(
    "Crescita media RAL (% annua)", 
    min_value=0.0, max_value=10.0, 
    value=DEFAULT_RAL_CRESCITA * 100, step=0.1
) / 100.0

st.sidebar.header("📈 Ipotesi Macroeconomiche")
tasso_capitalizzazione = st.sidebar.slider(
    "Tasso Capitalizzazione / PIL (% annua)", 
    min_value=0.0, max_value=5.0, 
    value=DEFAULT_TASSO_CAPITALIZZAZIONE * 100, step=0.1,
    help="La rivalutazione annua del montante, basata sulla media del PIL a 5 anni."
) / 100.0

st.sidebar.header("🎛️ Coefficienti (Avanzate)")
coeff_base_attuale = COEFFICIENTI_ATTUALI.get(eta_pensionamento, COEFFICIENTI_ATTUALI[67])
st.sidebar.markdown(f"Coefficiente base (a {eta_pensionamento} anni): **{coeff_base_attuale*100:.3f}%**")

variazione_coeff = st.sidebar.slider(
    "Variazione stima coefficiente (%)", 
    min_value=-50.0, max_value=50.0, 
    value=DEFAULT_VAR_COEFF, step=0.5,
    help="Simula l'impatto di un coefficiente futuro diverso da quello attuale (es. -20% per scenario prudente)."
)

coeff_finale_perc = (coeff_base_attuale * (1 + (variazione_coeff / 100.0))) * 100.0
coeff_finale_ratio = coeff_finale_perc / 100.0

# --- RACCOLTA PARAMETRI ATTUALI ---
# Raccoglie tutti i parametri in un dizionario per il confronto
current_params = {
    "eta_attuale": eta_attuale,
    "eta_pensionamento": eta_pensionamento,
    "eta_fine_contribuzione": eta_fine_contribuzione,
    "montante_attuale": montante_attuale,
    "ral_attuale": ral_attuale,
    "ral_crescita": ral_crescita,
    "tasso_capitalizzazione": tasso_capitalizzazione,
    "coeff_base_attuale": coeff_base_attuale,
    "variazione_coeff": variazione_coeff,
    "coeff_finale_perc": coeff_finale_perc,
    "coeff_finale_ratio": coeff_finale_ratio
}

# --- CONTROLLO STATO "DIRTY" ---
params_are_dirty = (current_params != st.session_state.last_run_params)

# --- PAGINA PRINCIPALE (GUIDA E RISULTATI) ---

st.title("💰 Simulatore Pensione (Sistema Contributivo)")
st.markdown("""
<style>
    /* 1. Nascondo Menu e Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 2. Nascondo il tasto DEPLOY */
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

    /* --- 3. Allineamento Altezza --- */
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
    
    /* Questo forza il pulsante a riempire il suo contenitore */
    div[data-testid="stButton"] > button {
        height: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGICA DI VISUALIZZAZIONE PRINCIPALE ---

# Se i parametri sono cambiati o non abbiamo risultati, mostra il pulsante
if params_are_dirty or st.session_state.results is None:
    
    # Nascondi i risultati vecchi se i parametri sono cambiati
    if params_are_dirty and st.session_state.results is not None:
        st.session_state.results = None
    
    
    # --- MODIFICA: Pulsante e Info SOPRA la guida ---
    top_col1, top_col2 = st.columns([3, 1], vertical_alignment="center")
    
    with top_col1:
        st.info("👈 Modifica i parametri nella barra laterale, quindi clicca 'Avvia Simulazione'.")
    
    with top_col2:
        if st.button("🚀 Avvia Simulazione", use_container_width=True, type="primary"):
            # Esegui i calcoli
            montante_finale, anni_lavorati = calcola_montante_futuro(
                eta_attuale, eta_fine_contribuzione, eta_pensionamento,
                montante_attuale, ral_attuale, ral_crescita,
                tasso_capitalizzazione, DEFAULT_ALIQUOTA
            )
            
            pensione_lorda_annua = montante_finale * coeff_finale_ratio
            pensione_netta_annua = calcola_netto(pensione_lorda_annua)
            
            # Salva i risultati e i parametri nello stato
            st.session_state.results = {
                "montante_finale": montante_finale,
                "pensione_lorda_annua": pensione_lorda_annua,
                "pensione_netta_annua": pensione_netta_annua,
                "anni_lavorati": anni_lavorati
            }
            st.session_state.last_run_params = current_params.copy()
            
            # Ricarica la pagina per mostrare i risultati
            st.rerun()

    st.markdown("---") # Separatore
            
    # --- GUIDA VISIBILE PRIMA DELLA SIMULAZIONE ---
    with st.container(border=True):
        st.subheader("Guida Rapida all'Uso del Simulatore")
        st.markdown(GUIDA_DETTAGLIATA)
    # --- FINE GUIDA ---
    # --- FINE MODIFICA ---

else:
    # --- STATO "PULITO": Mostra i risultati salvati ---
    
    # Recupera i dati salvati
    results = st.session_state.results
    params = st.session_state.last_run_params
    
    montante_finale = results["montante_finale"]
    pensione_lorda_annua = results["pensione_lorda_annua"]
    pensione_lorda_mensile = pensione_lorda_annua / 13
    pensione_netta_annua = results["pensione_netta_annua"]
    pensione_netta_mensile = pensione_netta_annua / 13
    anni_lavorati = results["anni_lavorati"]
            
    # --- Visualizzazione Risultati (CON CONTAINER) ---
    with st.container(border=True): # MODIFICA: Aggiunto container per risalto
        st.subheader(f"Risultati della Simulazione (Uscita a {params['eta_pensionamento']} anni)")
        
        st.metric(
            label=f"Montante Contributivo Finale Stimato (dopo {anni_lavorati} anni di contributi)",
            value=f"€ {montante_finale:,.2f}"
        )
        
        st.markdown("---")
        
        col_lordo, col_netto = st.columns(2)
        
        with col_lordo:
            st.markdown("### Assegno Pensionistico LORDO")
            st.metric(label="Pensione Annua Lorda", value=f"€ {pensione_lorda_annua:,.2f}")
            st.metric(label="Pensione Mensile Lorda (su 13 mensilità)", value=f"€ {pensione_lorda_mensile:,.2f}")
            
        with col_netto:
            st.markdown("### Stima Assegno Pensionistico NETTO")
            st.metric(label="Stima Pensione Annua Netta", value=f"€ {pensione_netta_annua:,.2f}")
            st.metric(label="Stima Pensione Mensile Netta (su 13 mensilità)", value=f"€ {pensione_netta_mensile:,.2f}")
            st.caption("Il netto è una stima basata sulle aliquote IRPEF 2024 e non tiene conto di detrazioni/deduzioni personali.")
    # --- Fine container risultati ---

    # Riepilogo Ipotesi
    with st.expander("Dettaglio Ipotesi Utilizzate per questo Calcolo"):
        # FIX: Corretto SyntaxError (invalid decimal literal)
        # Bisogna usare '%%' per mostrare il carattere '%' in una f-string dopo una formattazione
        st.markdown(f"""
        - **Anni di Contribuzione Futuri:** {anni_lavorati} anni (da {params['eta_attuale']} a {params['eta_fine_contribuzione'] - 1} anni)
        - **Anni di Rivalutazione Passiva:** {max(0, params['eta_pensionamento'] - params['eta_fine_contribuzione'])} anni
        - **Crescita RAL:** {params['ral_crescita']:.1f}%% annua
        - **Tasso Capitalizzazione (PIL):** {params['tasso_capitalizzazione']:.1f}%% annuo
        - **Coefficiente di Trasformazione Applicato:** {params['coeff_finale_perc']:.4f}%% 
          (Base {params['coeff_base_attuale']:.3f}%% con variazione del {params['variazione_coeff']:.1f}%%)
        """)

    # --- Guida (Spostata in fondo e nascosta di default) ---
    st.write("") # Spacer
    with st.expander("Mostra Guida Rapida all'Uso", expanded=False):
        # --- MODIFICA: Guida ora usa la variabile ---
        st.markdown(GUIDA_DETTAGLIATA)
        # --- FINE MODIFICA ---