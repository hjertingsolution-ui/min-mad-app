import streamlit as st
import requests
import pandas as pd
from datetime import date
from PIL import Image
from pyzbar.pyzbar import decode
import io

# --- OPSÆTNING ---
st.set_page_config(page_title="Min Mad", page_icon="🥗", layout="centered")

# --- STYLE (Det grønne tema styres nu af config.toml, men vi fjerner menuer her) ---
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* Gør kamera-inputtet pænere */
    .css-1y4p8pa {padding-top: 0rem;}
    </style>
    """
st.markdown(hide_menu_style, unsafe_allow_html=True)

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

# --- DINE MÅL ---
GOALS = {
    "Træning": {"kcal": 2900, "prot": 220, "kulh": 330, "fedt": 75},
    "Hvide":   {"kcal": 2500, "prot": 200, "kulh": 255, "fedt": 75}
}

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
    if "Træning" in mode:
        st.session_state.dagstype = "Træning"
    else:
        st.session_state.dagstype = "Hvide"

mål = GOALS[st.session_state.dagstype]

# Beregn totaler
sum_kcal = sum(i['Kcal'] for i in st.session_state.log)
sum_prot = sum(i['Prot'] for i in st.session_state.log)
sum_fedt = sum(i['Fedt'] for i in st.session_state.log)

# Visuelle tal
st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.metric("Kcal", f"{sum_kcal}", f"Af {mål['kcal']}")
c2.metric("Prot", f"{int(sum_prot)}g", f"Af {mål['prot']}g")
fedt_delta = mål['fedt'] - sum_fedt
c3.metric("Fedt", f"{int(sum_fedt)}g", f"{int(fedt_delta)}g tilbage", 
          delta_color="inverse" if sum_fedt > 75 else "normal")

st.progress(min(sum_kcal / mål['kcal'], 1.0))
st.markdown("---")

# --- 2. SCANNER & SØGNING ---
st.subheader("➕ Tilføj Mad")

# Vi bruger tabs for at holde det pænt
tab1, tab2 = st.tabs(["📸 Scan Stregkode", "🔍 Søg Tekst"])

# --- TAB 1: SCANNER ---
with tab1:
    st.caption("Tag et billede af stregkoden (sørg for den er tydelig)")
    img_file = st.camera_input("Start Kamera")
    
    if img_file:
        # Prøv at finde stregkode i billedet
        image = Image.open(img_file)
        decoded = decode(image)
        
        if decoded:
            barcode_data = decoded[0].data.decode("utf-8")
            st.success(f"Fandt stregkode: {barcode_data}")
            
            # Hent data
            product = get_product_by_barcode(barcode_data)
            
            if product:
                p_navn = product.get("product_name", "Ukendt vare")
                nutri = product.get("nutriments", {})
                
                # Vis hvad vi fandt
                st.write(f"**Fandt:** {p_navn}")
                
                # Input gram
                scan_gram = st.number_input("Antal gram:", value=100, step=10, key="scan_gram")
                
                # Beregn
                faktor = scan_gram / 100
                scan_kcal = int(nutri.get("energy-kcal_100g", 0) * faktor)
                scan_prot = round(nutri.get("proteins_100g", 0) * faktor, 1)
                scan_fedt = round(nutri.get("fat_100g", 0) * faktor, 1)
                scan_kulh = round(nutri.get("carbohydrates_100g", 0) * faktor, 1)
                
                st.info(f"{scan_kcal} kcal | P:{scan_prot} | F:{scan_fedt} | K:{scan_kulh}")
                
                if st.button("Gem Scannet Vare"):
                    st.session_state.log.append({
                        "Navn": p_navn,
                        "Gram": scan_gram,
                        "Kcal": scan_kcal,
                        "Prot": scan_prot,
                        "Fedt": scan_fedt,
                        "Kulh": scan_kulh
                    })
                    st.success("Gemt!")
                    st.rerun()
            else:
                st.error("Kunne ikke finde varen i databasen.")
        else:
            st.warning("Kunne ikke se en stregkode. Prøv at gå tættere på.")

# --- TAB 2: TEKST SØGNING (Den gamle metode) ---
with tab2:
    query = st.text_input("Søg navn", "")
    if query:
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=3"
        res = requests.get(url).json()
        
        if "products" in res and res["products"]:
            # Dropdown logik her (samme som før, bare forkortet for overblik)
            opts = {f"{p.get('product_name','?')} ({p.get('brands','')})": p for p in res["products"]}
            valg = st.selectbox("Vælg:", list(opts.keys()))
            p_data = opts[valg]
            
            man_gram = st.number_input("Gram:", value=100, key="man_gram")
            nu = p_data.get("nutriments", {})
            fakt = man_gram/100
            
            # Beregning
            m_kcal = int(nu.get("energy-kcal_100g", 0) * fakt)
            m_prot = round(nu.get("proteins_100g", 0) * fakt, 1)
            m_fedt = round(nu.get("fat_100g", 0) * fakt, 1)
            m_kulh = round(nu.get("carbohydrates_100g", 0) * fakt, 1)
            
            st.write(f"📊 {m_kcal} kcal (P:{m_prot}, F:{m_fedt})")
            
            if st.button("Tilføj Manuelt"):
                st.session_state.log.append({
                    "Navn": p_data.get('product_name'), "Gram": man_gram,
                    "Kcal": m_kcal, "Prot": m_prot, "Fedt": m_fedt, "Kulh": m_kulh
                })
                st.rerun()

# --- 3. LOG ---
st.subheader("Din Dagbog")
if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    st.dataframe(df[["Navn", "Gram", "Kcal", "Prot", "Fedt"]], use_container_width=True)
    if st.button("Nulstil Dag"):
        st.session_state.log = []
        st.rerun()
