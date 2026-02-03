import streamlit as st
import requests
import pandas as pd
from datetime import date

# --- OPSÆTNING ---
st.set_page_config(page_title="Min Mad", page_icon="🥗", layout="centered")

# Skjul Streamlit menuer (Giver app-følelse)
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# --- DINE MÅL ---
GOALS = {
    "Træning": {"kcal": 2900, "prot": 220, "kulh": 330, "fedt": 75},
    "Hvide":   {"kcal": 2500, "prot": 200, "kulh": 255, "fedt": 75}
}

# --- STARTER APPEN (Hukommelse) ---
if 'log' not in st.session_state:
    st.session_state.log = []
if 'dagstype' not in st.session_state:
    st.session_state.dagstype = "Hvide"

# --- 1. ØVERSTE DASHBOARD ---
st.title(f"Dagens Status ({date.today().day}/{date.today().month})")

col_train, col_reset = st.columns([3, 1])
with col_train:
    mode = st.radio("Har du trænet i dag?", ["Nej (Hviledag)", "Ja (Træningsdag)"], horizontal=True)
    if "Ja" in mode:
        st.session_state.dagstype = "Træning"
    else:
        st.session_state.dagstype = "Hvide"

mål = GOALS[st.session_state.dagstype]

sum_kcal = sum(i['Kcal'] for i in st.session_state.log)
sum_prot = sum(i['Prot'] for i in st.session_state.log)
sum_fedt = sum(i['Fedt'] for i in st.session_state.log)
sum_kulh = sum(i['Kulh'] for i in st.session_state.log)

st.markdown("---")
k1, k2, k3 = st.columns(3)
k1.metric("🔥 Kalorier", f"{sum_kcal}", f"Mål: {mål['kcal']}")
k2.metric("🥩 Protein", f"{int(sum_prot)}g", f"Mål: {mål['prot']}g")

fedt_delta = mål['fedt'] - sum_fedt
k3.metric("🥑 Fedt", f"{int(sum_fedt)}g", f"{int(fedt_delta)}g tilbage", 
          delta_color="inverse" if sum_fedt > 75 else "normal")

progress = min(sum_kcal / mål['kcal'], 1.0)
st.progress(progress, text=f"Du har spist {int(progress*100)}% af dagens kalorier")

st.markdown("---")

# --- 2. SØG OG TILFØJ MAD (API) ---
st.subheader("➕ Tilføj Mad")

query = st.text_input("Søg madvare (f.eks. 'Skyr', 'Æble')", "")

if query:
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=5"
    res = requests.get(url).json()
    
    if "products" in res and len(res["products"]) > 0:
        vare_liste = {}
        for p in res["products"]:
            navn = p.get("product_name", "Ukendt")
            mærke = p.get("brands", "")
            key = f"{navn} - {mærke}"
            vare_liste[key] = p
            
        valgt_navn = st.selectbox("Vælg vare:", list(vare_liste.keys()))
        valgt_vare = vare_liste[valgt_navn]
        
        nutri = valgt_vare.get("nutriments", {})
        k_100 = nutri.get("energy-kcal_100g", 0)
        p_100 = nutri.get("proteins_100g", 0)
        f_100 = nutri.get("fat_100g", 0)
        c_100 = nutri.get("carbohydrates_100g", 0)
        
        gram = st.number_input("Hvor mange gram?", value=100, step=10)
        
        faktor = gram / 100
        ny_kcal = int(k_100 * faktor)
        ny_prot = round(p_100 * faktor, 1)
        ny_fedt = round(f_100 * faktor, 1)
        ny_kulh = round(c_100 * faktor, 1)
        
        st.info(f"👉 {gram}g giver: **{ny_kcal} kcal** (P: {ny_prot}g, F: {ny_fedt}g, K: {ny_kulh}g)")
        
        if st.button("Tilføj til dagbog", type="primary"):
            entry = {
                "Navn": valgt_navn,
                "Gram": gram,
                "Kcal": ny_kcal,
                "Prot": ny_prot,
                "Fedt": ny_fedt,
                "Kulh": ny_kulh
            }
            st.session_state.log.append(entry)
            st.success("Tilføjet!")
            st.rerun()
            
    else:
        st.warning("Fandt ikke noget. Prøv at søge på engelsk hvis dansk ikke virker.")

# --- 3. DIN DAGBOG ---
st.subheader("📋 Dagens Måltider")

if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    st.dataframe(df[["Navn", "Gram", "Kcal", "Prot", "Fedt", "Kulh"]], use_container_width=True)
    
    if st.button("🗑️ Nulstil hele dagen"):
        st.session_state.log = []
        st.rerun()
else:
    st.caption("Din liste er tom.")
