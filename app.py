import streamlit as st
import requests
import pandas as pd
from datetime import date
from PIL import Image
from pyzbar.pyzbar import decode

# --- OPSÆTNING ---
st.set_page_config(page_title="Min Mad", page_icon="🥗", layout="centered")

# --- STYLE ---
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .css-1y4p8pa {padding-top: 0rem;}
    </style>
    """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# --- DINE FAVORITTER (Madvarer du spiser tit) ---
# Tallene er per 100g (Kcal, Protein, Kulhydrat, Fedt)
FAVORITTER = {
    "Kylling (Frost, Dagrofa)": {"kcal": 105, "prot": 23.0, "kulh": 0.0,  "fedt": 1.2},
    "Rugbrød (Almindeligt)":    {"kcal": 210, "prot": 6.5,  "kulh": 38.0, "fedt": 2.5},
    "Tortellini (m/fyld)":      {"kcal": 290, "prot": 11.0, "kulh": 45.0, "fedt": 7.0},
    "Pasta (Tørret/Rå)":        {"kcal": 350, "prot": 12.0, "kulh": 72.0, "fedt": 1.5},
    "Ris (Hvide/Rå)":           {"kcal": 350, "prot": 7.0,  "kulh": 78.0, "fedt": 0.5},
    "Burgerbolle (Brioche)":    {"kcal": 280, "prot": 8.0,  "kulh": 50.0, "fedt": 5.0},
    "Grønt (Blandet/Frost)":    {"kcal": 40,  "prot": 2.5,  "kulh": 5.0,  "fedt": 0.5},
    "Skyr (Vanilla)":           {"kcal": 60,  "prot": 10.0, "kulh": 3.5,  "fedt": 0.2},
    "Havregryn":                {"kcal": 370, "prot": 13.0, "kulh": 58.0, "fedt": 7.0},
    "Proteinshake (1 scoop)":   {"kcal": 120, "prot": 24.0, "kulh": 3.0,  "fedt": 1.5}
}

# --- DINE MÅL ---
GOALS = {
    "Træning": {"kcal": 2900, "prot": 220, "kulh": 330, "fedt": 75},
    "Hvide":   {"kcal": 2500, "prot": 200, "kulh": 255, "fedt": 75}
}

# --- FUNKTIONER ---
def get_product_by_barcode(barcode):
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    try:
        res = requests.get(url).json()
        if res.get("status") == 1:
            return res["product"]
    except:
        pass
    return None

# --- SESSION STATE ---
if 'log' not in st.session_state:
    st.session_state.log = []
if 'dagstype' not in st.session_state:
    st.session_state.dagstype = "Hvide"

# --- 1. DASHBOARD ---
st.title(f"Dagens Status 🥗")

col_train, col_reset = st.columns([3, 1])
with col_train:
    mode = st.radio("Dagsform", ["Hviledag (2500)", "Træningsdag (2900)"], horizontal=True)
    st.session_state.dagstype = "Træning" if "Træning" in mode else "Hvide"

mål = GOALS[st.session_state.dagstype]

sum_kcal = sum(i['Kcal'] for i in st.session_state.log)
sum_prot = sum(i['Prot'] for i in st.session_state.log)
sum_fedt = sum(i['Fedt'] for i in st.session_state.log)

st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.metric("Kcal", f"{sum_kcal}", f"Af {mål['kcal']}")
c2.metric("Prot", f"{int(sum_prot)}g", f"Af {mål['prot']}g")
fedt_delta = mål['fedt'] - sum_fedt
c3.metric("Fedt", f"{int(sum_fedt)}g", f"{int(fedt_delta)}g tilbage", 
          delta_color="inverse" if sum_fedt > 75 else "normal")

st.progress(min(sum_kcal / mål['kcal'], 1.0))
st.markdown("---")

# --- 2. TILFØJ MAD ---
st.subheader("➕ Tilføj Mad")

# Nu med 3 tabs
tab1, tab2, tab3 = st.tabs(["⭐ Favoritter", "📸 Scan", "🔍 Søg"])

# --- TAB 1: FAVORITTER (Dropdown) ---
with tab1:
    st.caption("Vælg fra din faste liste")
    
    valgt_favorit = st.selectbox("Vælg madvare:", list(FAVORITTER.keys()))
    
    # Hent data for valgte
    fav_data = FAVORITTER[valgt_favorit]
    
    col_g, col_btn = st.columns([2, 1])
    with col_g:
        gram_fav = st.number_input("Gram:", value=100, step=10, key="fav_gram")
    
    # Vis info live
    f_faktor = gram_fav / 100
    f_kcal = int(fav_data['kcal'] * f_faktor)
    f_prot = round(fav_data['prot'] * f_faktor, 1)
    f_fedt = round(fav_data['fedt'] * f_faktor, 1)
    f_kulh = round(fav_data['kulh'] * f_faktor, 1)
    
    st.info(f"👉 **{f_kcal} kcal** (P:{f_prot}, F:{f_fedt}, K:{f_kulh})")
    
    if st.button("Tilføj Favorit", type="primary"):
        st.session_state.log.append({
            "Navn": valgt_favorit, "Gram": gram_fav,
            "Kcal": f_kcal, "Prot": f_prot, "Fedt": f_fedt, "Kulh": f_kulh
        })
        st.success("Tilføjet!")
        st.rerun()

# --- TAB 2: SCANNER ---
with tab2:
    img_file = st.camera_input("Start Kamera")
    if img_file:
        image = Image.open(img_file)
        decoded = decode(image)
        if decoded:
            bc = decoded[0].data.decode("utf-8")
            prod = get_product_by_barcode(bc)
            if prod:
                p_navn = prod.get("product_name", "Ukendt")
                nutri = prod.get("nutriments", {})
                
                scan_gram = st.number_input("Gram:", value=100, key="scan_gram")
                s_fak = scan_gram/100
                s_kcal = int(nutri.get("energy-kcal_100g", 0) * s_fak)
                s_prot = round(nutri.get("proteins_100g", 0) * s_fak, 1)
                s_fedt = round(nutri.get("fat_100g", 0) * s_fak, 1)
                s_kulh = round(nutri.get("carbohydrates_100g", 0) * s_fak, 1)
                
                st.write(f"**{p_navn}**: {s_kcal} kcal")
                if st.button("Gem Scan"):
                    st.session_state.log.append({
                        "Navn": p_navn, "Gram": scan_gram,
                        "Kcal": s_kcal, "Prot": s_prot, "Fedt": s_fedt, "Kulh": s_kulh
                    })
                    st.rerun()
            else:
                st.error("Vare ikke fundet.")

# --- TAB 3: SØGNING ---
with tab3:
    query = st.text_input("Søg navn (OpenFoodFacts)", "")
    if query:
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=3"
        res = requests.get(url).json()
        if "products" in res and res["products"]:
            opts = {f"{p.get('product_name','?')}": p for p in res["products"]}
            sel = st.selectbox("Resultater:", list(opts.keys()))
            p_data = opts[sel]
            
            man_gram = st.number_input("Gram:", value=100, key="man_gram")
            nu = p_data.get("nutriments", {})
            m_fak = man_gram/100
            
            m_kcal = int(nu.get("energy-kcal_100g", 0) * m_fak)
            m_prot = round(nu.get("proteins_100g", 0) * m_fak, 1)
            m_fedt = round(nu.get("fat_100g", 0) * m_fak, 1)
            m_kulh = round(nu.get("carbohydrates_100g", 0) * m_fak, 1)
            
            if st.button("Tilføj Søgning"):
                st.session_state.log.append({
                    "Navn": sel, "Gram": man_gram,
                    "Kcal": m_kcal, "Prot": m_prot, "Fedt": m_fedt, "Kulh": m_kulh
                })
                st.rerun()

# --- 3. LOG ---
st.subheader("📋 Logbog")
if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    st.dataframe(df[["Navn", "Gram", "Kcal", "Prot", "Fedt"]], use_container_width=True)
    if st.button("🗑️ Nulstil Dag"):
        st.session_state.log = []
        st.rerun()
