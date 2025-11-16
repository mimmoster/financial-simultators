import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import math
import copy # Importato per i "solver"

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Simulatore di Ritiro Anticipato (FIRE)",
    page_icon="🔥",
    layout="wide"
)

# --- LOGICA DI CALCOLO TASSE ---
def calcola_prelievo_tassato(prelievo_netto_desiderato, cap_portafoglio, cap_investito, tassa_cg_perc):
    """
    Calcola quanto prelevare (lordo) per ottenere un certo netto,
    pagando la tassa sul capital gain (es. 26%) solo sulla plusvalenza.
    """
    
    if prelievo_netto_desiderato <= 0 or cap_portafoglio <= 0:
        return 0, 0, 0, 0 # prelievo_lordo, tassa_pagata, cost_basis_prelevato, prelievo_netto_effettivo

    plusvalenza = max(0, cap_portafoglio - cap_investito)
    
    if plusvalenza <= 0:
        prelievo_lordo = min(cap_portafoglio, prelievo_netto_desiderato)
        cost_basis_prelevato = prelievo_lordo
        return prelievo_lordo, 0, cost_basis_prelevato, prelievo_lordo

    prop_plusvalenza = plusvalenza / cap_portafoglio
    
    aliquota_effettiva = prop_plusvalenza * tassa_cg_perc
    if aliquota_effettiva >= 1: 
        aliquota_effettiva = 0.99 
        
    prelievo_lordo = prelievo_netto_desiderato / (1 - aliquota_effettiva)
    prelievo_lordo = min(cap_portafoglio, prelievo_lordo)
    
    tassa_pagata = (prelievo_lordo * prop_plusvalenza) * tassa_cg_perc
    cost_basis_prelevato = prelievo_lordo * (1 - prop_plusvalenza)
    prelievo_netto_effettivo = prelievo_lordo - tassa_pagata
    
    return prelievo_lordo, tassa_pagata, cost_basis_prelevato, prelievo_netto_effettivo


# --- LOGICA DI SIMULAZIONE ---
def esegui_simulazione_completa(params):
    
    eta_attuale = params['profilo']['eta_attuale']
    anno_attuale = params['profilo']['anno_attuale']
    eta_ritiro_desiderata = params['obiettivo']['eta_ritiro_desiderata']
    eta_pensione_inps = params['obiettivo']['eta_pensione_inps']
    eta_fine_simulazione = params['obiettivo']['eta_fine_simulazione']
    logica_decumulo = params['logica_decumulo']
    tassa_cg_perc = params['tassazione']['capital_gain_perc']

    rend_netto_portafoglio = (params['portafoglio']['rendimento_lordo'] - 
                              params['portafoglio']['imposta_di_bollo'])
    rend_netto_fonte = params['fondo_pensione']['rendimento_netto']
    
    cap_portafoglio = params['portafoglio']['capitale_iniziale']
    cap_investito = params['portafoglio']['capitale_iniziale'] 
    cap_fonte = params['fondo_pensione']['capitale_iniziale']
    cap_liquidita = 0.0
    
    cap_al_ritiro = 0.0
    cap_all_inizio_pensione_inps = 0.0
    
    results = []

    for i in range(eta_fine_simulazione - eta_attuale + 1):
        eta_sim = eta_attuale + i
        anno_sim = anno_attuale + i
        
        anni_da_oggi = eta_sim - eta_attuale
        spesa_annua_infl = params['spese_pensione']['spesa_annua_oggi'] * (1 + params['spese_pensione']['inflazione'])**anni_da_oggi
        
        versamento_portafoglio = 0.0
        versamento_fonte = 0.0
        prelievo_portafoglio_lordo = 0.0
        prelievo_netto_effettivo = 0.0
        entrata_pensione = 0.0
        eredita_anno = 0.0
        tasse_pagate = 0.0
        cost_basis_prelevato = 0.0
        
        if eta_sim == eta_pensione_inps:
            cap_all_inizio_pensione_inps = cap_portafoglio + cap_liquidita

        if eta_sim < eta_ritiro_desiderata:
            fase = "Accumulo"
            versamento_portafoglio = params['portafoglio']['versamento_annuo']
            
            # --- MODIFICA: Versamento F.P. rivalutato in base alla RAL ---
            anni_di_crescita_ral = eta_sim - eta_attuale
            versamento_fonte = params['fondo_pensione']['versamento_annuo_iniziale'] * (1 + params['fondo_pensione']['aumento_ral'])**anni_di_crescita_ral
            
            if anno_sim == params['eventi']['anno_eredita']:
                eredita_anno = params['eventi']['importo_eredita']
        
        else:
            fase = "Decumulo"
            
            if eta_sim == eta_ritiro_desiderata:
                cap_al_ritiro = cap_portafoglio
            
            if anno_sim == params['eventi']['anno_eredita'] and eta_sim >= eta_ritiro_desiderata:
                cap_liquidita += params['eventi']['importo_eredita']
            
            modalita_ritiro_fp = params['fondo_pensione']['modalita_ritiro']
            
            if modalita_ritiro_fp == "Agevolata (12/48 mesi)":
                if eta_sim == eta_ritiro_desiderata + 1:
                    valore_fonte_T1 = cap_fonte * (1 + rend_netto_fonte)**1
                    prelievo_lordo_1 = valore_fonte_T1 * 0.5
                    prelievo_netto_1 = prelievo_lordo_1 * (1 - params['fondo_pensione']['tassa_agevolata'])
                    cap_liquidita += prelievo_netto_1
                    cap_fonte = valore_fonte_T1 * 0.5 
                
                if eta_sim == eta_ritiro_desiderata + 4:
                    valore_fonte_T4 = cap_fonte * (1 + rend_netto_fonte)**3
                    prelievo_lordo_2 = valore_fonte_T4
                    prelievo_netto_2 = prelievo_lordo_2 * (1 - params['fondo_pensione']['tassa_agevolata'])
                    cap_liquidita += prelievo_netto_2
                    cap_fonte = 0.0
            
            elif modalita_ritiro_fp == "Immediata (Tassazione 23%)":
                if eta_sim == eta_ritiro_desiderata + 1:
                    valore_fonte_T1 = cap_fonte * (1 + rend_netto_fonte)**1
                    prelievo_lordo_totale = valore_fonte_T1
                    prelievo_netto_totale = prelievo_lordo_totale * (1 - 0.23) 
                    cap_liquidita += prelievo_netto_totale
                    cap_fonte = 0.0

            if eta_sim >= eta_pensione_inps:
                pensione_annua_infl = (params['spese_pensione']['pensione_inps_mensile'] * params['spese_pensione']['pensione_inps_mesi']) * (1 + params['spese_pensione']['inflazione'])**anni_da_oggi
                entrata_pensione = pensione_annua_infl
                
            prelievo_netto_desiderato = 0.0
            
            if logica_decumulo == "Simulazione (Spesa Definita)":
                shortfall_netto = max(0, spesa_annua_infl - entrata_pensione)
            else: 
                shortfall_netto = (cap_portafoglio * params['assunzioni_ritiro']['swr'])
                shortfall_netto = max(0, shortfall_netto - entrata_pensione)

            prelievo_liquidita = min(cap_liquidita, shortfall_netto)
            cap_liquidita -= prelievo_liquidita
            
            prelievo_netto_da_portafoglio = max(0, shortfall_netto - prelievo_liquidita)
            
            prelievo_portafoglio_lordo, tasse_pagate, cost_basis_prelevato, prelievo_netto_effettivo = \
                calcola_prelievo_tassato(prelievo_netto_da_portafoglio, cap_portafoglio, cap_investito, tassa_cg_perc)

        spesa_coperta = (prelievo_netto_effettivo + prelievo_liquidita + entrata_pensione) if fase == 'Decumulo' else 0
        
        results.append({
            "Anno": anno_sim,
            "Età": eta_sim,
            "Fase": fase,
            "Capitale Portafoglio": cap_portafoglio,
            "Capitale Investito": cap_investito,
            "Capitale Liquidità": cap_liquidita,
            "Prelievo Lordo Portafoglio": prelievo_portafoglio_lordo,
            "Tasse Pagate": tasse_pagate,
            "Spesa Annua Coperta": spesa_coperta, 
            "Spesa Target (Sim)": spesa_annua_infl if logica_decumulo == "Simulazione (Spesa Definita)" and fase == "Decumulo" else 0
        })

        capitale_post_prelievo = cap_portafoglio - prelievo_portafoglio_lordo
        capitale_investito_post_prelievo = cap_investito - cost_basis_prelevato
        
        interessi_p = capitale_post_prelievo * rend_netto_portafoglio
        
        cap_portafoglio = capitale_post_prelievo + interessi_p + versamento_portafoglio + eredita_anno
        cap_investito = capitale_investito_post_prelievo + versamento_portafoglio + eredita_anno
        
        if fase == "Accumulo":
            interessi_f = cap_fonte * rend_netto_fonte
            cap_fonte += interessi_f + versamento_fonte
        
        if cap_portafoglio <= 0:
            cap_portafoglio = 0
            
    df = pd.DataFrame(results)
    cap_rimanente_fine = df.iloc[-1]['Capitale Portafoglio'] + df.iloc[-1]['Capitale Liquidità']
    
    if eta_pensione_inps <= eta_fine_simulazione and not df[df['Età'] == eta_pensione_inps].empty:
         cap_all_inizio_pensione_inps = df[df['Età'] == eta_pensione_inps]['Capitale Portafoglio'].values[0] + \
                                        df[df['Età'] == eta_pensione_inps]['Capitale Liquidità'].values[0]
    else:
        cap_all_inizio_pensione_inps = cap_rimanente_fine

    return df, cap_al_ritiro, cap_rimanente_fine, cap_all_inizio_pensione_inps

# --- FUNZIONI SOLVER ---
@st.cache_data
def trova_piano_sostenibile_eta(_params):
    params = copy.deepcopy(_params) 
    eta_iniziale = params['obiettivo']['eta_ritiro_desiderata']
    eta_massima = params['obiettivo']['eta_pensione_inps']
    
    for eta_test in range(eta_iniziale + 1, eta_massima + 1):
        params['obiettivo']['eta_ritiro_desiderata'] = eta_test
        _, _, cap_rimanente, _ = esegui_simulazione_completa(params)
        if cap_rimanente > 0:
            return eta_test
    return None

@st.cache_data
def trova_piano_sostenibile_investimento(_params):
    params = copy.deepcopy(_params)
    investimento_iniziale = params['portafoglio']['versamento_annuo']
    
    for incremento in [1000, 2500, 5000]: 
        for i in range(1, 21): 
            investimento_test = investimento_iniziale + (i * incremento)
            params['portafoglio']['versamento_annuo'] = investimento_test
            _, _, cap_rimanente, _ = esegui_simulazione_completa(params)
            if cap_rimanente > 0:
                return investimento_test
    return None

# --- FUNZIONE PLOT ---
def plot_risultati(df, params):
    if df.empty:
        return None
        
    eta_ritiro_desiderata = params['obiettivo']['eta_ritiro_desiderata']
    eta_pensione_inps = params['obiettivo']['eta_pensione_inps']

    fig, ax = plt.subplots(figsize=(12, 7))
    
    x = df['Età']
    y1 = df['Capitale Portafoglio']
    y2 = df['Capitale Liquidità']
    
    # Asse Y Sinistro (Capitale)
    ax.stackplot(x, y1, y2, labels=['Capitale Portafoglio', 'Capitale Liquidità (Cash)'],
                 colors=['#0068c9', '#00c9a7']) # Blu e Verde Acqua
    ax.set_xlabel("Età")
    ax.set_ylabel("Euro (Capitale)")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f'€ {x:,.0f}'))

    # Linee Verticali
    ax.axvline(x=eta_ritiro_desiderata, color='red', linestyle=':', label=f"Inizio Ritiro ({eta_ritiro_desiderata} anni)")
    ax.axvline(x=eta_pensione_inps, color='purple', linestyle=':', label=f"Inizio Pensione INPS ({eta_pensione_inps} anni)")

    # Asse Y Destro (Spesa)
    ax_spesa = ax.twinx()
    df_decumulo = df[df['Fase'] == 'Decumulo']
    label_spesa = "Spesa Annua Coperta"
    
    max_spesa = 0
    if not df_decumulo.empty:
        ax_spesa.plot(df_decumulo['Età'], df_decumulo['Spesa Annua Coperta'], 
                color='#dd8800', linestyle='--', label=label_spesa) # Arancio scuro
        max_spesa = df_decumulo['Spesa Annua Coperta'].max()
    
    ax_spesa.set_ylabel("Euro (Spesa Annua)", color='#dd8800')
    ax_spesa.tick_params(axis='y', labelcolor='#dd8800')
    ax_spesa.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f'€ {x:,.0f}'))
    
    # Scala Assi 1.5x e 1.2x
    ax.set_ylim(bottom=0) 
    max_capitale = (y1 + y2).max()
    ax.set_ylim(bottom=0, top=max_capitale * 1.5) # Scala 1.5x
    
    ax_spesa.set_ylim(bottom=0) 
    if max_spesa > 0:
        ax_spesa.set_ylim(bottom=0, top=max_spesa * 1.2) # Scala 1.2x
    else:
        ax_spesa.set_ylim(bottom=0, top=1) # Fallback se la spesa è 0

    # Gestione Legende
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax_spesa.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc='upper left')

    ax.set_title("Evoluzione Capitale Totale vs. Spesa Annua", fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_xlim(x.min(), x.max())
    
    return fig

# --- FUNZIONE README ---
def show_readme():
    """Mostra la guida al simulatore"""
    st.subheader("Guida Rapida al Simulatore")
    st.markdown("""
    Questo simulatore ti aiuta a pianificare il tuo ritiro anticipato (FIRE) calcolando l'evoluzione del tuo patrimonio anno per anno, basandosi su una logica a 3 fasi.

    ### 1. Fase di Accumulo (Oggi -> Ritiro)
    * Il tuo **Portafoglio Principale** (grafico blu) cresce in base ai versamenti annui e al rendimento, al netto del bollo.
    * Il tuo **Fondo Pensione** (se attivato) cresce separatamente. Il versamento annuo cresce in base al parametro "Aumento Annuo RAL".
    * Il tuo **Costo Storico** (visibile nella tabella di dettaglio) viene tracciato per calcolare le future plusvalenze.

    ### 2. Fase di Decumulo "Ponte" (Ritiro -> Pensione INPS)
    Questa è la fase più critica. La simulazione adotta una strategia "Cash Bucket" (serbatoio di liquidità) per proteggere il tuo portafoglio:
    1.  **Versamenti Interrotti:** Smetti di alimentare i portafogli.
    2.  **Creazione del "Cash Bucket" (Liquidità):** Al momento del ritiro, le somme del **Fondo Pensione** (tassate in base alla tua scelta) e degli **Eventi Straordinari** (es. eredità) vengono versate in un "serbatoio" di liquidità (il grafico verde acqua).
    3.  **Prelievi Intelligenti:** Per coprire le tue spese (linea arancione), il simulatore preleva i soldi in questo ordine:
        * **Prima:** Attinge dal "Cash Bucket".
        * **Durante questo periodo,** il tuo Portafoglio Principale (blu) *non* viene toccato e continua a crescere con gli interessi.
        * **Solo quando il "Cash Bucket" è esaurito,** il simulatore inizia a prelevare (decumulare) dal Portafoglio Principale, pagando la Tassa sul Capital Gain (26%) solo sulla plusvalenza.

    ### 3. Fase di Pensione (Pensione INPS -> Fine)
    * Inizi a ricevere la tua pensione INPS (rivalutata all'inflazione).
    * Il prelievo dal tuo portafoglio si riduce drasticamente: ora serve solo a coprire la differenza (`Spesa Annua - Pensione INPS`).

    ---
    
    ### Note Importanti sui Parametri

    * **Logica di Decumulo (Spesa Definita vs. SWR):**
        * **Simulazione (Spesa Definita):** Tu imposti una spesa annua desiderata (es. 40.000 €). La simulazione preleva *esattamente* quella cifra (adeguata all'inflazione) ogni anno. L'obiettivo è rispondere alla domanda: "Se spendo X€ all'anno, il mio capitale dura?"
        * **SWR (Tasso di Prelievo):** Tu imposti un tasso (es. 3.5%). La spesa *non è fissa*, ma variabile: ogni anno prelevi il 3.5% del capitale *rimasto* in quel momento. È una strategia più flessibile che riduce il rischio di esaurire i fondi, ma non garantisce un tenore di vita costante.

    * **Pensione INPS (Netta vs. Lorda):**
        * L'importo della `Pensione INPS mensile` (es. 2.500 €) deve essere **NETTO**. La simulazione confronta spese nette con entrate nette. Inserire un valore lordo porterebbe a risultati pericolosamente ottimistici.

    * **Fondo Pensione (Rendimento vs. Tasse):**
        * `Rendimento Netto F.P.` (es. 2.5%): È il tasso di crescita *annuale* del valore della tua quota (NAV). È già al netto delle imposte *sui rendimenti* che il fondo paga ogni anno.
        * `Modalità Ritiro F.P.` (15% o 23%): Questa è la tassazione *finale* (imposta sostitutiva) pagata *solo* sul capitale che prelevi quando smetti di lavorare, e che andrà a riempire il tuo "Cash Bucket".
        * `Aumento Annuo RAL`: Questo slider (default 2.5%) fa crescere il tuo `Versamento Annuo F.P.` ogni anno, simulando la progressione della tua RAL e del TFR accumulato.

    ### Il Risultato
    * **Sostenibile:** Il piano funziona e ti avanza capitale.
    * **Non Sostenibile:** Il capitale si esaurisce. In questo caso, l'app ti suggerisce (Opzione A) di posticipare il ritiro o (Opzione B) di aumentare i versamenti.
    """)


# --- INTERFACCIA WEB (Streamlit) ---
st.set_page_config(layout="wide")
st.title("🔥 Simulatore di Ritiro Anticipato (FIRE)")

# --- Blocco CSS (DA INSERIRE DOPO st.title) ---
# QUESTO È IL BLOCCO CSS CHE MI HAI FORNITO TU
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
# -------------------------------------------------

# --- 1. BARRA LATERALE PER GLI INPUT ---
st.sidebar.title("Configura la Simulazione")

st.sidebar.subheader("👤 Profilo")
# MODIFICA: Default eta_attuale = 18
eta_attuale = st.sidebar.number_input("La tua età attuale", min_value=18, max_value=60, value=18, format="%d")
anno_attuale = st.sidebar.number_input("Anno attuale", value=2025, format="%d")

# --- CALCOLO ASV ---
auto_calcola_eta = st.sidebar.checkbox("Stima età pensionabile (ASV)", value=True, help="Stima l'età pensionabile in base agli adeguamenti alla speranza di vita (ASV).")

if auto_calcola_eta:
    mesi_adeguamento = st.sidebar.slider("Mesi di adeguamento (ogni 2 anni)", 0, 6, 3, help="Quanti mesi si aggiungono all'età pensionabile ogni 2 anni.")
    # Calcola l'età stimata
    anni_mancanti_base = 67 - eta_attuale
    num_adeguamenti = math.floor(max(0, anni_mancanti_base) / 2)
    eta_pensionabile_stimata = 67 + (num_adeguamenti * mesi_adeguamento / 12)
    eta_pensione_inps = st.sidebar.slider("Età pensione INPS", min_value=65, max_value=80, value=int(round(eta_pensionabile_stimata)), disabled=True, format="%d")
else:
    eta_pensione_inps = st.sidebar.slider("Età pensione INPS", min_value=65, max_value=80, value=70, format="%d")


st.sidebar.subheader("🎯 Obiettivo")
# MODIFICA: Range simulazione e max_value dinamico
eta_ritiro_desiderata = st.sidebar.slider("Età di ritiro desiderata", min_value=eta_attuale + 1, max_value=eta_pensione_inps, value=60)
eta_fine_simulazione = st.sidebar.slider("Età fine simulazione", min_value=eta_attuale + 10, max_value=120, value=95)

st.sidebar.subheader("💵 Logica e Spese")
logica_decumulo = st.sidebar.selectbox("Logica di Decumulo", ["Simulazione (Spesa Definita)", "SWR (Tasso di Prelievo)"])

if logica_decumulo == "Simulazione (Spesa Definita)":
    # Default spesa 20000
    spesa_annua_oggi = st.sidebar.number_input("Spesa Annua (valore oggi)", min_value=10000, value=20000, step=1000, format="%d")
    swr_str = st.sidebar.slider("Tasso Prelievo (SWR) (%)", 1.0, 6.0, 3.5, 0.1, disabled=True)
else: 
    spesa_annua_oggi = st.sidebar.number_input("Spesa Annua (valore oggi)", value=0, disabled=True, help="In modalità SWR, la spesa è calcolata automaticamente", format="%d")
    swr_str = st.sidebar.slider("Tasso Prelievo (SWR) (%)", 1.0, 6.0, 3.5, 0.1)

inflazione_str = st.sidebar.slider("Inflazione Annua Prevista (%)", 0.0, 10.0, 2.0, 0.1)
pensione_inps_mensile = st.sidebar.number_input("Pensione INPS mensile (futura)", value=2500.0, step=100.0, format="%.0f")
pensione_inps_mesi = st.sidebar.number_input("Numero mensilità INPS", value=13, format="%d")

st.sidebar.subheader("🏦 Portafoglio Principale")
capitale_iniziale_p = st.sidebar.number_input("Capitale Iniziale", value=100000.0, step=10000.0, format="%.0f")
versamento_annuo_p = st.sidebar.number_input("Versamento Annuo", value=1200.0, step=100.0, format="%.0f")
rendimento_lordo_p_str = st.sidebar.slider("Rendimento Lordo Annuo (%)", 0.0, 15.0, 5.0, 0.1)
bollo_str = st.sidebar.slider("Imposta di Bollo (%)", 0.0, 1.0, 0.2, 0.01)
tassa_cg_str = st.sidebar.slider("Tassa Capital Gain (%)", 0.0, 30.0, 26.0, 0.5)

st.sidebar.subheader("🌱 Fondo Pensione")
usa_fondo_pensione = st.sidebar.checkbox("Aggiungi Fondo Pensione?", value=True)
if usa_fondo_pensione:
    capitale_iniziale_f = st.sidebar.number_input("Capitale Iniziale F.P.", value=0.0, step=1000.0, format="%.0f")
    versamento_annuo_f = st.sidebar.number_input("Versamento Annuo F.P. (iniziale)", value=5000.0, step=500.0, format="%.0f")
    # --- NUOVO SLIDER ---
    aumento_ral_str = st.sidebar.slider("Aumento Annuo RAL (stima %)", 0.0, 10.0, 2.5, 0.1, help="Usato per far crescere il tuo versamento annuo al fondo pensione, simulando la crescita della RAL.")
    rendimento_netto_f_str = st.sidebar.slider("Rendimento Netto Annuo F.P. (%)", 0.0, 10.0, 2.5, 0.1)
    modalita_ritiro_fp = st.sidebar.selectbox("Modalità Ritiro F.P.", ["Agevolata (12/48 mesi)", "Immediata (Tassazione 23%)"])
    tassa_agevolata_fp = st.sidebar.slider("Tassazione Agevolata F.P. (%)", 0.0, 23.0, 15.0, 0.5, help="Tassazione agevolata per F.P. (tipicamente 15% che scende allo 0.3% all'anno dopo il 15° anno)")
else:
    # Valori nulli se non usato
    capitale_iniziale_f = 0.0
    versamento_annuo_f = 0.0
    aumento_ral_str = 0.0 # Obbligatorio
    rendimento_netto_f_str = 0.0
    modalita_ritiro_fp = "Agevolata (12/48 mesi)"
    tassa_agevolata_fp = 15.0


st.sidebar.subheader("🌟 Eventi Straordinari")
usa_evento_straordinario = st.sidebar.checkbox("Aggiungi Evento Straordinario?")
if usa_evento_straordinario:
    importo_eredita = st.sidebar.number_input("Importo Eredità/Bonus", value=200000.0, step=10000.0, format="%.0f")
    anno_eredita = st.sidebar.number_input("Anno Ricezione Eredità", value=anno_attuale, min_value=anno_attuale, format="%d")
else:
    importo_eredita = 0.0
    anno_eredita = 0

# --- 2. PULSANTE DI ESECUZIONE ---
top_col1, top_col2 = st.columns([3, 1], vertical_alignment="center")

with top_col1:
    st.info("👈 Modifica i parametri nella barra laterale, quindi clicca 'Avvia Simulazione'.")

with top_col2:
    run_simulation = st.button("🚀 Avvia Simulazione", use_container_width=True, type="primary")


if run_simulation:

    # --- 3. RACCOLTA PARAMETRI E SIMULAZIONE ---
    params = {
        "profilo": {"eta_attuale": eta_attuale, "anno_attuale": anno_attuale},
        "obiettivo": {"eta_ritiro_desiderata": eta_ritiro_desiderata, "eta_pensione_inps": eta_pensione_inps, "eta_fine_simulazione": eta_fine_simulazione},
        "logica_decumulo": logica_decumulo,
        "spese_pensione": {"spesa_annua_oggi": spesa_annua_oggi, "inflazione": inflazione_str / 100.0, "pensione_inps_mensile": pensione_inps_mensile, "pensione_inps_mesi": pensione_inps_mesi},
        "portafoglio": {"capitale_iniziale": capitale_iniziale_p, "versamento_annuo": versamento_annuo_p, "rendimento_lordo": rendimento_lordo_p_str / 100.0, "imposta_di_bollo": bollo_str / 100.0},
        "tassazione": {"capital_gain_perc": tassa_cg_str / 100.0},
        "fondo_pensione": {
            "capitale_iniziale": capitale_iniziale_f, 
            "versamento_annuo_iniziale": versamento_annuo_f, # --- MODIFICA NOME ---
            "aumento_ral": aumento_ral_str / 100.0, # --- NUOVO PARAMETRO ---
            "rendimento_netto": rendimento_netto_f_str / 100.0,
            "modalita_ritiro": modalita_ritiro_fp,
            "tassa_agevolata": tassa_agevolata_fp / 100.0 
            },
        "eventi": {"importo_eredita": importo_eredita, "anno_eredita": anno_eredita},
        "assunzioni_ritiro": {"swr": swr_str / 100.0}
    }

    with st.spinner("Calcolo simulazione in corso..."):
        df_simulazione, cap_al_ritiro, cap_rimanente_fine, cap_all_inizio_pensione_inps = esegui_simulazione_completa(params)
        
        if cap_rimanente_fine <= 0:
            with st.spinner("Calcolo opzione A: posticipare il ritiro..."):
                eta_sostenibile = trova_piano_sostenibile_eta(params)
            with st.spinner("Calcolo opzione B: aumentare i versamenti..."):
                investimento_sostenibile = trova_piano_sostenibile_investimento(params)
        else:
            eta_sostenibile = None
            investimento_sostenibile = None
            
        fig_simulazione_completa = plot_risultati(df_simulazione, params)

    # --- 4. VISUALIZZAZIONE RISULTATI (con 4 metriche) ---
    st.header("📈 Risultati della Simulazione")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Età di Ritiro Scelta", f"{eta_ritiro_desiderata} anni")
    col2.metric("Capitale al Ritiro", f"€ {cap_al_ritiro:,.0f}")
    col3.metric(f"Capitale a {eta_pensione_inps} anni (Inizio Pensione)", f"€ {cap_all_inizio_pensione_inps:,.0f}")
    col4.metric(f"Capitale Rimanente a {eta_fine_simulazione} anni", f"€ {cap_rimanente_fine:,.0f}")
    
    if cap_rimanente_fine > 0:
        st.success(f"🎉 Il tuo piano è SOSTENIBILE! Ti rimangono € {cap_rimanente_fine:,.0f} a {eta_fine_simulazione} anni.")
    else:
        st.error(f"⚠️ Attenzione! Il tuo piano NON è sostenibile. Il capitale si esaurisce prima dei {eta_fine_simulazione} anni.")
        st.subheader("Come rendere il piano sostenibile:")
        
        col_a, col_b = st.columns(2)
        if eta_sostenibile:
            col_a.info(f"**Opzione A: Ritardare il Ritiro**\nDovresti ritirarti a **{eta_sostenibile} anni** (invece di {eta_ritiro_desiderata}) per far funzionare questo piano.")
        else:
            col_a.warning("L'opzione di ritardare il ritiro non è sufficiente (o arriva oltre l'età della pensione).")
            
        if investimento_sostenibile:
            col_b.info(f"**Opzione B: Aumentare i Versamenti**\nDovresti versare **€ {investimento_sostenibile:,.0f}/anno** (invece di € {params['portafoglio']['versamento_annuo']:,.0f}).")
        else:
            col_b.warning("L'opzione di aumentare i versamenti non è sufficiente (richiederebbe una cifra troppo alta).")

    if fig_simulazione_completa:
        st.subheader("Simulazione Completa (Accumulo e Decumulo)")
        st.pyplot(fig_simulazione_completa)
    
    with st.expander("📊 Mostra i dati dettagliati della simulazione (anno per anno)"):
        df_display = df_simulazione.rename(columns={
            "Capitale Portafoglio": "Cap. Portafoglio (€)",
            "Capitale Investito": "Costo Storico (€)",
            "Capitale Fon.Te": "Cap. Fon.Te (€)",
            "Capitale Liquidità": "Cash Bucket (€)",
            "Prelievo Lordo Portafoglio": "Prelievo Lordo (€)",
            "Tasse Pagate": "Tasse CG Pagate (€)",
            "Spesa Annua Coperta": "Spesa Coperta (€)",
            "Spesa Target (Sim)": "Spesa Target (€)"
        })
        st.dataframe(df_display.style.format({
            "Cap. Portafoglio (€)": "€ {:,.0f}",
            "Costo Storico (€)": "€ {:,.0f}",
            "Cap. Fon.Te (€)": "€ {:,.0f}",
            "Cash Bucket (€)": "€ {:,.0f}",
            "Prelievo Lordo (€)": "€ {:,.0f}",
            "Tasse CG Pagate (€)": "€ {:,.0f}",
            "Spesa Coperta (€)": "€ {:,.0f}",
            "Spesa Target (€)": "€ {:,.0f}"
        }))

    with st.expander("ℹ️ Come leggere questo simulatore (Guida Rapida)"):
        show_readme()

else:
    st.divider()
    show_readme()