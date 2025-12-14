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
st.title("Sistem Monitoring Kepadatan Lalu Lintas")
st.markdown("---")

# Nama file CSV (Harus SAMA PERSIS dengan di program deteksi)
CSV_FILE = "laporan_kepadatan_multi.csv"
# CSV_FILE = "laporan_kepadatan.csv"

# Fungsi Helper untuk memberi warna status
def get_status_color(status):
    if status == "LANCAR": return "green"
    elif status == "RAMAI LANCAR": return "orange"
    elif status == "PADAT PELAN": return "darkorange"
    elif status == "MACET TOTAL": return "red"
    return "gray"

# Placeholder untuk konten agar bisa di-refresh tanpa reload halaman
placeholder = st.empty()

while True:
    with placeholder.container():
        # Cek apakah file CSV ada
        if not os.path.exists(CSV_FILE):
            st.warning("⏳ Menunggu data... Jalankan program deteksi terlebih dahulu.")
            time.sleep(2)
            continue

        try:
            # Baca CSV
            df = pd.read_csv(CSV_FILE)
            
            # Pastikan nama kolom sesuai dengan fungsi catat_log_csv kamu
            # Asumsi header: Timestamp, Lajur, Status, Avg Speed, Jumlah Objek
            
            # Ambil data paling baru untuk setiap lajur
            # Kita filter data 1 menit terakhir saja untuk grafik agar tidak berat
            df_display = df.tail(50) 

            # Buat 2 Kolom untuk Layout (Lajur Kiri & Lajur Kanan)
            col1, col2 = st.columns(2)
            
            # --- KOLOM 1: LAJUR KIRI ---
            with col1:
                st.header("Lajur Kiri")
                # Filter data lajur kiri
                df_kiri = df[df["Lajur"] == "Lajur Kiri"]
                
                if not df_kiri.empty:
                    last_kiri = df_kiri.iloc[-1]
                    status_kiri = last_kiri["Status"]
                    color_kiri = get_status_color(status_kiri)
                    
                    # Tampilkan Metric Besar
                    st.metric(label="Jumlah Kendaraan", value=f"{last_kiri['Jumlah Objek']} unit")
                    st.metric(label="Kecepatan Rata-rata", value=f"{last_kiri['Avg Speed']} px/frame")
                    
                    # Tampilan Status Berwarna
                    st.markdown(f"""
                        <div style="padding:10px; border-radius:5px; background-color:{color_kiri}; color:white; text-align:center;">
                            <h2 style="margin:0;">{status_kiri}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Grafik Tren
                    st.subheader("Grafik Kepadatan")
                    st.line_chart(df_kiri[["Jumlah Objek"]].reset_index(drop=True))
                else:
                    st.info("Belum ada data Lajur Kiri")

            # --- KOLOM 2: LAJUR KANAN ---
            with col2:
                st.header("Lajur Kanan")
                # Filter data lajur kanan
                df_kanan = df[df["Lajur"] == "Lajur Kanan"]
                
                if not df_kanan.empty:
                    last_kanan = df_kanan.iloc[-1]
                    status_kanan = last_kanan["Status"]
                    color_kanan = get_status_color(status_kanan)
                    
                    # Tampilkan Metric Besar
                    st.metric(label="Jumlah Kendaraan", value=f"{last_kanan['Jumlah Objek']} unit")
                    st.metric(label="Kecepatan Rata-rata", value=f"{last_kanan['Avg Speed']} px/frame")
                    
                    # Tampilan Status Berwarna
                    st.markdown(f"""
                        <div style="padding:10px; border-radius:5px; background-color:{color_kanan}; color:white; text-align:center;">
                            <h2 style="margin:0;">{status_kanan}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Grafik Tren
                    st.subheader("Grafik Kepadatan")
                    st.line_chart(df_kanan[["Jumlah Objek"]].reset_index(drop=True))
                else:
                    st.info("Belum ada data Lajur Kanan")

            # Tabel Data Mentah (Opsional, di bawah)
            with st.expander("Lihat Data Mentah Terakhir"):
                st.dataframe(df.tail(10))

        except Exception as e:
            st.error(f"Terjadi kesalahan membaca data: {e}")

        # Tunggu 2 detik sebelum refresh
        time.sleep(2)