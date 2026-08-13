import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="THY Teknik ÜPK - İş Kartı Önceliklendirme",
    page_icon="✈️",
    layout="wide"
)

# --- TITLE & HEADER ---
st.title("✈️ THY Teknik ÜPK - Akıllı İş Kartı Önceliklendirme Paneli")
st.caption("Uçak bakım operasyonlarında kritik yol, AOG riski ve parça durumuna göre otomatik önceliklendirme aracı.")
st.markdown("---")

# --- MOCK DATA GENERATOR ---
@st.cache_data
def generate_mock_data():
    np.random.seed(42)
    aircraft_types = ["A320-200", "A330-300", "B737-800", "B777-300ER", "B787-9"]
    tail_numbers = ["TC-JFP", "TC-LNC", "TC-JRO", "TC-LGA", "TC-JJU"]
    work_scopes = [
        "Alet / Avyonik Sistem Kontrolü", "Kabin İçi Koltuk / Galley Onarımı",
        "Fren Diski ve İniş Takımı Değişimi", "Hidrolik Sızıntı Testi",
        "Motor Fan Bıçağı Muayenesi (NDT)", "Korozyon Temizliği ve Boya",
        "Uçuş Kontrol Yüzeyleri Kalibrasyonu", "Oksijen Sistemi Basınç Testi"
    ]
    
    data = []
    for i in range(1, 41):
        job_id = f"JC-2026-{1000 + i}"
        aircraft = np.random.choice(aircraft_types)
        tail = np.random.choice(tail_numbers)
        scope = np.random.choice(work_scopes)
        is_critical = np.random.choice([1, 0], p=[0.3, 0.7])
        is_aog_risk = np.random.choice([1, 0], p=[0.2, 0.8])
        part_status = np.random.choice(["Hazır", "Siparişte", "Karantina / Testte"], p=[0.6, 0.3, 0.1])
        dependencies = np.random.randint(0, 6)
        planned_hours = np.random.choice([1.5, 3.0, 4.5, 8.0, 12.0])
        hours_remaining = np.random.randint(2, 48)
        
        data.append({
            "İş Kartı ID": job_id,
            "Uçak Tipi": aircraft,
            "Kuyruk Tescil": tail,
            "İş Tanımı": scope,
            "Kritik Yol Mi?": is_critical,
            "AOG Riski Var mı?": is_aog_risk,
            "Parça Durumu": part_status,
            "Bağımlı İş Sayısı": dependencies,
            "Planlanan Süre (Saat)": planned_hours,
            "Hangardan Çıkışa Kalan (Saat)": hours_remaining
        })
    return pd.DataFrame(data)

# --- SIDEBAR: PARAMETERS & FILTERS ---
st.sidebar.header("⚙️ Öncelik Algoritması Ağırlıkları")
st.sidebar.write("Hangi parametrenin önceliğe ne kadar etki edeceğini ayarlayın:")

w_critical = st.sidebar.slider("Kritik Yol Ağırlığı", 0, 50, 35, step=5)
w_aog = st.sidebar.slider("AOG Riski Ağırlığı", 0, 50, 30, step=5)
w_part = st.sidebar.slider("Parça Hazır Olma Ağırlığı", 0, 30, 20, step=5)
w_dep = st.sidebar.slider("Bağımlı İş Çarpanı", 0, 5, 3)

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtreleme Options")
selected_aircraft = st.sidebar.multiselect(
    "Uçak Tipi Seçin", 
    options=["A320-200", "A330-300", "B737-800", "B777-300ER", "B787-9"],
    default=["A320-200", "B737-800"]
)

part_filter = st.sidebar.radio("Parça Durumu Filtresi", ["Tümü", "Sadece Parçası Hazır Olanlar"])

# --- PRIORITY SCORE CALCULATION ENGINE ---
def calculate_priority_scores(df):
    part_score_map = {"Hazır": 1.0, "Karantina / Testte": 0.3, "Siparişte": 0.0}
    
    # Skorlama mantığı
    scores = (
        (df["Kritik Yol Mi?"] * w_critical) +
        (df["AOG Riski Var mı?"] * w_aog) +
        (df["Parça Durumu"].map(part_score_map) * w_part) +
        (df["Bağımlı İş Sayısı"] * w_dep) +
        (100 / (df["Hangardan Çıkışa Kalan (Saat)"] + 1))  # Zaman sıkışıklığı primi
    )
    df["Öncelik Skoru"] = np.round(scores, 1)
    return df.sort_values(by="Öncelik Skoru", ascending=False)

# Load and Filter Data
raw_df = generate_mock_data()

filtered_df = raw_df[raw_df["Uçak Tipi"].isin(selected_aircraft)].copy()
if part_filter == "Sadece Parçası Hazır Olanlar":
    filtered_df = filtered_df[filtered_df["Parça Durumu"] == "Hazır"]

processed_df = calculate_priority_scores(filtered_df)

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Toplam İş Kartı", len(processed_df))
with col2:
    st.metric("Kritik Yoldaki İşler", len(processed_df[processed_df["Kritik Yol Mi?"] == 1]))
with col3:
    st.metric("AOG Riski Taşıyanlar", len(processed_df[processed_df["AOG Riski Var mı?"] == 1]))
with col4:
    parca_bekleyen = len(processed_df[processed_df["Parça Durumu"] != "Hazır"])
    st.metric("Parça Bekleyen İşler", parca_bekleyen, delta_color="inverse")

st.markdown("---")

# --- DATA TABLE WITH HIGHLIGHTING ---
st.subheader("📌 Öncelik Sıralamasına Göre İş Kartları")

# Tablo Görünümü Ayarları
def highlight_priority(val):
    if val >= 70:
        return 'background-color: #ff4b4b; color: white; font-weight: bold;'
    elif val >= 45:
        return 'background-color: #ffa726; color: black;'
    return ''

# Tabloyu Göster
st.dataframe(
    processed_df.style.map(highlight_priority, subset=["Öncelik Skoru"]),
    use_container_width=True,
    height=400
)

# --- EXPORT TO EXCEL FEATURE ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Oncelikli_Is_Kartlari')
    processed_data = output.getvalue()
    return processed_data

excel_data = to_excel(processed_df)

st.download_button(
    label="📥 Önceliklendirilmiş Vardiya Raporunu İndir (Excel)",
    data=excel_data,
    file_name="THY_Teknik_UPK_Vardiya_Raporu.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)