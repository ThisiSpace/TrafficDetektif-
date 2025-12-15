import streamlit as st
import pandas as pd
import time
from collections import deque # Digunakan untuk menyimpan data grafik real-time
import firebase_admin
from firebase_admin import credentials, db

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Dashboard Lalu Lintas",
    page_icon="🚦",
    layout="wide"
)

# Judul Dashboard
st.title("🚦 Sistem Monitoring Kepadatan Lalu Lintas")
st.markdown("---")

# --- KONFIGURASI FIREBASE ---
# Buffer dalam memori untuk menampung 100 data count terakhir untuk grafik real-time
MAX_RT_POINTS = 100
realtime_data_buffer = {
    "Lajur Kiri": deque(maxlen=MAX_RT_POINTS),
    "Lajur Kanan": deque(maxlen=MAX_RT_POINTS)
}
LAJUR_KEYS = ["Lajur Kiri", "Lajur Kanan"]

# Variabel global untuk referensi Firebase
firebase_ref = None

# --- FUNGSI FIREBASE (Singletons/Cache) ---

def initialize_firebase():
    """Menginisialisasi Firebase Admin SDK menggunakan Streamlit Secrets."""
    # Mencegah error 'The default Firebase app already exists'
    if not firebase_admin._apps:
        try:
            # Menggunakan st.secrets untuk membuat credential
            cred_dict = dict(st.secrets["firebase"])
            # Inisialisasi dari dictionary secrets
            cred = credentials.Certificate(cred_dict) 
            
            firebase_admin.initialize_app(cred, {
                'databaseURL': st.secrets["firebase"]["database_url"]
            })
            print("[FIREBASE] Inisialisasi Berhasil.")
        except Exception as e:
            st.error(f"Gagal inisialisasi Firebase. Pastikan file secrets.toml sudah benar. Error: {e}")
            return None
    
    # Mengambil referensi dan mengembalikannya
    return db.reference('/traffic_status')

@st.cache_data(ttl=1) # Data di-cache selama 1 detik
def get_realtime_status(ref):
    """Mengambil status real-time terbaru dari Firebase."""
    if ref:
        return ref.get()
    return None

# --- INI DILAKUKAN SEKALI DI AWAL ---
firebase_ref = initialize_firebase()
firebase_status_ok = (firebase_ref is not None)

# Fungsi Helper untuk memberi warna status
def get_status_color(status):
    if status == "LANCAR": return "green"
    elif status == "RAMAI LANCAR": return "orange"
    elif status == "PADAT PELAN": return "darkorange"
    elif status == "MACET TOTAL": return "red"
    return "gray"

# --- BAGIAN TAMPILAN DASHBOARD PERMANEN ---

# Placeholder untuk Konten Utama (Status, Metrik)
status_metric_placeholder = st.empty() 

# Kontainer untuk Grafik Real-time (Frame-by-Frame)
st.markdown("---")
st.subheader("🚀 Grafik Kepadatan Real-Time (Frame-by-Frame)")

col_rt_kiri, col_rt_kanan = st.columns(2)
with col_rt_kiri:
    st.markdown("#### Lajur Kiri Real-Time")
    rt_chart_kiri = st.empty() 
with col_rt_kanan:
    st.markdown("#### Lajur Kanan Real-Time")
    rt_chart_kanan = st.empty() 

# Kontainer untuk Grafik Historis (Hapus ini jika Anda tidak lagi menyimpan log historis terpisah)
# st.markdown("---")
# st.subheader("📊 Grafik Historis (Tren Jangka Panjang)")
# historical_chart_placeholder = st.empty()


# --- LOOP UTAMA ---

# Variabel untuk mengontrol kecepatan update (Polling)
last_historical_update = time.time()
HISTORICAL_UPDATE_INTERVAL = 2 # Update status/metrik setiap 2 detik

while True:
    
    if not firebase_status_ok:
        time.sleep(5)
        continue

    # Ambil data terbaru dari Firebase (Cached selama 1 detik)
    status_data = get_realtime_status(firebase_ref)
    
    if status_data:
        # Perbarui status, metrik, dan grafik real-time
        
        # --- 1. UPDATE STATUS, METRIK, dan GRAFIK HISTORIS (Sekali dalam 2 detik) ---
        if (time.time() - last_historical_update) >= HISTORICAL_UPDATE_INTERVAL:
            
            with status_metric_placeholder.container():
                
                # Buat 2 Kolom untuk Layout (Lajur Kiri & Lajur Kanan)
                col1, col2 = st.columns(2)
                
                for i, nama_lajur in enumerate(LAJUR_KEYS):
                    
                    # Ubah nama lajur menjadi format key Firebase (misal: Lajur Kiri -> Lajur_Kiri)
                    lajur_key = nama_lajur.replace(" ", "_")
                    
                    if lajur_key in status_data:
                        data = status_data[lajur_key]
                        
                        count = data.get('count', 0)
                        speed = data.get('speed', "0.00")
                        status = data.get('status', "UNKNOWN")
                        color = get_status_color(status)
                        
                        target_col = col1 if i == 0 else col2

                        with target_col:
                            st.header(f" {nama_lajur}") # Tambahkan emoji jika perlu
                            
                            st.metric(label="Jumlah Kendaraan", value=f"{count} unit")
                            st.metric(label="Kecepatan Rata-rata", value=f"{speed} px/frame")
                            
                            st.markdown(f"""
                                <div style="padding:10px; border-radius:5px; background-color:{color}; color:white; text-align:center;">
                                    <h2 style="margin:0;">{status}</h2>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Logika Historis dihilangkan atau diganti jika tidak ada log historis terpisah
                            st.info("Grafik Historis Memerlukan Log Data Terpisah (Belum Disediakan)")
                            
                last_historical_update = time.time() # Reset timer historis
                
        # --- 2. UPDATE GRAFIK REAL-TIME (Cepat: Setiap 0.5 detik) ---
        
        # Update buffer dan grafik dalam setiap loop (cepat)
        for i, nama_lajur in enumerate(LAJUR_KEYS):
            lajur_key = nama_lajur.replace(" ", "_")
            
            if lajur_key in status_data:
                count = status_data[lajur_key].get('count', 0)
                
                # Masukkan data count terbaru ke buffer memori
                realtime_data_buffer[nama_lajur].append(count)

                # Siapkan data untuk Line Chart dari buffer
                df_chart = pd.DataFrame(list(realtime_data_buffer[nama_lajur]), columns=["Jumlah Objek"])
                
                # Gambar ulang grafik
                target_chart = rt_chart_kiri if i == 0 else rt_chart_kanan
                
                with target_chart:
                    if not df_chart.empty:
                        # Streamlit akan me-render indeks sebagai sumbu X (Frame-by-Frame)
                        st.line_chart(df_chart, height=300) 
                    else:
                        st.info("Menunggu data frame...")
                        
    else:
        # Jika status_data kosong (misal program deteksi belum jalan)
        with status_metric_placeholder.container():
            st.warning("Menunggu data dari Firebase... Pastikan program deteksi lokal sedang berjalan.")
            
    # Jeda pendek, mengontrol kecepatan keseluruhan loop
    time.sleep(0.5)