import streamlit as st
import pandas as pd
import time
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Dashboard Lalu Lintas",
    page_icon="🚦",
    layout="wide"
)

# Judul Dashboard
st.title("🚦 Sistem Monitoring Kepadatan Lalu Lintas")
st.markdown("---")

# Nama file CSV (Harus SAMA PERSIS dengan di program deteksi)
REALTIME_GRAPH_FILE = "realtime_graph_data.csv"
CSV_FILE = "laporan_kepadatan_multi.csv"

# Fungsi Helper untuk memberi warna status
def get_status_color(status):
    if status == "LANCAR": return "green"
    elif status == "RAMAI LANCAR": return "orange"
    elif status == "PADAT PELAN": return "darkorange"
    elif status == "MACET TOTAL": return "red"
    return "gray"

# --- BAGIAN TAMPILAN DASHBOARD PERMANEN ---

# Placeholder untuk Konten Utama (Status, Metrik, dan Grafik Historis)
# Logika ini akan diupdate lebih jarang (2 detik)
status_metric_placeholder = st.empty() 

# Kontainer untuk Grafik Real-time (Frame-by-Frame)
# Logika ini akan diupdate lebih sering (1 detik)
st.markdown("---")
st.subheader("🚀 Grafik Kepadatan Real-Time (Frame-by-Frame)")

# Kontainer untuk grafik real-time
col_rt_kiri, col_rt_kanan = st.columns(2)
with col_rt_kiri:
    st.markdown("#### Lajur Kiri Real-Time")
    rt_chart_kiri = st.empty() # Placeholder untuk grafik cepat
with col_rt_kanan:
    st.markdown("#### Lajur Kanan Real-Time")
    rt_chart_kanan = st.empty() # Placeholder untuk grafik cepat

# --- LOOP UTAMA ---

# Variabel untuk mengontrol kecepatan update (Polling)
last_historical_update = time.time()
HISTORICAL_UPDATE_INTERVAL = 2 # Update status/metrik/historis setiap 2 detik

while True:
    
    # --- 1. UPDATE GRAFIK REAL-TIME (Cepat: Setiap 1 detik) ---
    if os.path.exists(REALTIME_GRAPH_FILE):
        try:
            # Baca hanya 100 baris terakhir dari file real-time agar cepat
            # Header asumsi: Lajur, Jumlah Objek (dari modifikasi kode deteksi sebelumnya)
            df_rt = pd.read_csv(REALTIME_GRAPH_FILE)
            df_rt_display = df_rt.tail(100) # Hanya tampilkan 100 baris terakhir
            
            rt_kiri = df_rt_display[df_rt_display['Lajur'] == 'Lajur Kiri']
            rt_kanan = df_rt_display[df_rt_display['Lajur'] == 'Lajur Kanan']
            
            # Gambar ulang grafik Kiri
            with rt_chart_kiri:
                if not rt_kiri.empty:
                    st.line_chart(rt_kiri['Jumlah Objek'].reset_index(drop=True), height=300) 
                else:
                    st.info("Menunggu data frame...")

            # Gambar ulang grafik Kanan
            with rt_chart_kanan:
                if not rt_kanan.empty:
                    st.line_chart(rt_kanan['Jumlah Objek'].reset_index(drop=True), height=300)
                else:
                    st.info("Menunggu data frame...")
                    
        except pd.errors.EmptyDataError:
             # File ada tapi kosong (baru di-reset)
            with rt_chart_kiri: st.info("Menunggu data frame pertama...")
            with rt_chart_kanan: st.info("Menunggu data frame pertama...")
        except Exception as e:
            # st.error(f"Error membaca Realtime CSV: {e}") # Nonaktifkan agar tidak mengganggu tampilan
            pass # Lanjutkan loop meskipun ada error baca/tulis

    
    # --- 2. UPDATE STATUS, METRIK, dan GRAFIK HISTORIS (Lambat: Setiap 2 detik) ---
    if (time.time() - last_historical_update) >= HISTORICAL_UPDATE_INTERVAL:
        
        with status_metric_placeholder.container():
            # Cek apakah file CSV Historis ada
            if not os.path.exists(CSV_FILE):
                st.warning("⏳ Menunggu data historis (CSV_FILE)... Jalankan program deteksi terlebih dahulu.")
                time.sleep(1) # Jeda singkat jika file utama belum ada
                
            else:
                try:
                    df = pd.read_csv(CSV_FILE)
                    
                    # Buat 2 Kolom untuk Layout (Lajur Kiri & Lajur Kanan)
                    col1, col2 = st.columns(2)
                    
                    # --- LOGIKA TAMPILAN STATUS/METRIK (Kiri) ---
                    with col1:
                        st.header("⬅️ Lajur Kiri")
                        df_kiri = df[df["Lajur"] == "Lajur Kiri"]
                        
                        if not df_kiri.empty:
                            last_kiri = df_kiri.iloc[-1]
                            status_kiri = last_kiri["Status"]
                            color_kiri = get_status_color(status_kiri)
                            
                            st.metric(label="Jumlah Kendaraan", value=f"{last_kiri['Jumlah Objek']} unit")
                            st.metric(label="Kecepatan Rata-rata", value=f"{last_kiri['Avg Speed']} px/frame")
                            
                            st.markdown(f"""
                                <div style="padding:10px; border-radius:5px; background-color:{color_kiri}; color:white; text-align:center;">
                                    <h2 style="margin:0;">{status_kiri}</h2>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            st.subheader("Grafik Historis (Tren)")
                            # Grafik Historis
                            st.line_chart(df_kiri.tail(100)[["Jumlah Objek"]].reset_index(drop=True))
                        else:
                            st.info("Belum ada data Lajur Kiri")

                    # --- LOGIKA TAMPILAN STATUS/METRIK (Kanan) ---
                    with col2:
                        st.header("➡️ Lajur Kanan")
                        df_kanan = df[df["Lajur"] == "Lajur Kanan"]
                        
                        if not df_kanan.empty:
                            last_kanan = df_kanan.iloc[-1]
                            status_kanan = last_kanan["Status"]
                            color_kanan = get_status_color(status_kanan)
                            
                            st.metric(label="Jumlah Kendaraan", value=f"{last_kanan['Jumlah Objek']} unit")
                            st.metric(label="Kecepatan Rata-rata", value=f"{last_kanan['Avg Speed']} px/frame")
                            
                            st.markdown(f"""
                                <div style="padding:10px; border-radius:5px; background-color:{color_kanan}; color:white; text-align:center;">
                                    <h2 style="margin:0;">{status_kanan}</h2>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            st.subheader("Grafik Historis (Tren)")
                            # Grafik Historis
                            st.line_chart(df_kanan.tail(100)[["Jumlah Objek"]].reset_index(drop=True))
                        else:
                            st.info("Belum ada data Lajur Kanan")
                            
                    # Tabel Data Mentah (Opsional, di bawah)
                    with st.expander("Lihat Data Mentah Historis Terakhir"):
                        st.dataframe(df.tail(10))

                except Exception as e:
                    st.error(f"Terjadi kesalahan fatal membaca data historis: {e}")

                last_historical_update = time.time() # Reset timer historis

    # Jeda pendek, ini mengontrol kecepatan keseluruhan loop, mempengaruhi kecepatan real-time
    time.sleep(0.5)
