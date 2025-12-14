from ultralytics import YOLO
import numpy as np
import cv2
import os
import json
import torch
from deep_sort_realtime.deepsort_tracker import DeepSort
from collections import deque, Counter
import cv2
import numpy as np
import csv, datetime
# ============================
# KONFIGURASI
# ============================
config = {
    "sumberVideo": "videotes2.mp4",
    # "sumberVideo": "vidoetes1.mp4",
    # "sumberVideo": "https://www.youtube.com/watch?v=s4ScRXRLPO0",
    "model": "yolov8m.pt"
}

kendaraan = ["car", "motorcycle", "bus", "truck"]

# ============================
# FUNGSI: KONFIGURASI MODEL
# ============================
def konfig(config):
    video = config["sumberVideo"]
    modelPath = config["model"]
    model = YOLO(modelPath)
    tracking = DeepSort(max_age=25, max_cosine_distance=0.3)
    capture = cv2.VideoCapture(video)
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    last_centers = {}
    if not capture.isOpened():
        print(f"[ERROR] Video {video} tidak bisa dibuka bro.")
        exit()
    return capture, model, tracking,device, last_centers


# ============================
# FUNGSI: GAMBAR ROI POLYGON
# ============================
# ============================
# FUNGSI: GAMBAR MULTI-ROI
# ============================
def gambar_multi_roi(video_path, daftar_lajur):
    nama_file = os.path.splitext(os.path.basename(video_path))[0]
    roi_file = f"{nama_file}_rois.json"

    # Jika file ROI ada, load
    if os.path.exists(roi_file):
        print(f"[INFO] File ROI ditemukan, memuat dari {roi_file}")
        with open(roi_file, "r") as f:
            data = json.load(f)
            # Konversi list ke numpy array
            rois = {k: np.array(v, dtype=np.int32) for k, v in data.items()}
        return rois

    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    if not ret: return None

    rois_selesai = {}
    
    # Loop untuk setiap nama lajur (Kiri, Kanan, dst)
    for nama_lajur in daftar_lajur:
        roi_points = []
        temp_frame = frame.copy()
        print(f"[INFO] Silakan gambar ROI untuk: {nama_lajur}")

        def draw_polygon(event, x, y, flags, param):
            nonlocal roi_points, temp_frame
            if event == cv2.EVENT_LBUTTONDOWN:
                roi_points.append((x, y))
                cv2.circle(temp_frame, (x, y), 4, (0, 255, 0), -1)
                cv2.imshow(f"Gambar ROI: {nama_lajur}", temp_frame)
            elif event == cv2.EVENT_RBUTTONDOWN:
                if len(roi_points) > 2:
                    cv2.polylines(temp_frame, [np.array(roi_points)], isClosed=True, color=(0, 255, 0), thickness=2)
                    cv2.imshow(f"Gambar ROI: {nama_lajur}", temp_frame)

        cv2.namedWindow(f"Gambar ROI: {nama_lajur}")
        cv2.setMouseCallback(f"Gambar ROI: {nama_lajur}", draw_polygon)
        cv2.imshow(f"Gambar ROI: {nama_lajur}", temp_frame)

        # Tunggu sampai user menekan Enter (selesai gambar satu roi)
        print(f"   -> Klik Kiri titik, Klik Kanan sambung. TEKAN SPASI/ENTER JIKA SUDAH SELESAI {nama_lajur}.")
        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == 13 or key == 32: # Enter atau Spasi
                if len(roi_points) > 2:
                    rois_selesai[nama_lajur] = np.array(roi_points, dtype=np.int32)
                    break
                else:
                    print("[WARNING] Buat minimal 3 titik dulu!")
        
        cv2.destroyWindow(f"Gambar ROI: {nama_lajur}")

    # Simpan semua ROI ke JSON
    # Numpy array tidak bisa di-dump json langsung, harus tolist()
    data_simpan = {k: v.tolist() for k, v in rois_selesai.items()}
    with open(roi_file, "w") as f:
        json.dump(data_simpan, f, indent=4)
    
    cap.release()
    cv2.destroyAllWindows()
    return rois_selesai

# ============================
# FUNGSI: CEK TITIK DALAM ROI
# ============================
def dalam_roi(roi, bbox):
    # bbox = [x1, y1, x2, y2]
    x_center = int((bbox[0] + bbox[2]) / 2)
    y_center = int((bbox[1] + bbox[3]) / 2)
    return cv2.pointPolygonTest(roi, (x_center, y_center), False) >= 0

# --- FUNGSI UTILITY LOGGER (MODIFIKASI) ---
def catat_log_csv(filename, nama_lajur, status, kecepatan, jumlah_objek):
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            # Tambah kolom 'Lajur'
            writer.writerow(["Timestamp", "Lajur", "Status", "Avg Speed", "Jumlah Objek"])
            
        waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([waktu, nama_lajur, status, f"{kecepatan:.2f}", jumlah_objek])
        print(f"[LOG DISIMPAN] Status berubah menjadi: {status}")


# ============================
# FUNGSI: DETEKSI + TRACKING
# ============================
# def deteksi(capture, model, tracking, roi_polygon, device, last_centers):
#     pause = False
    
#     # --- 1. HAPUS BOBOT KENDARAAN DAN UBAH AMBANG BATAS ---
#     # Bobot dihapus
    
#     # Ubah ambang batas agar merujuk ke JUMLAH KENDARAAN
#     BATAS_LANCAR = 5   # Ambang batas jumlah kendaraan untuk Lancar
#     BATAS_PADAT = 15   # Ambang batas jumlah kendaraan untuk Macet/Padat
    
#     # Threshold Kecepatan (5 pixel/frame dianggap lambat/diam)
#     BATAS_KECEPATAN_LAMBAT = 5.0
    
#     while True:
#         if not pause:
#             ret, frame = capture.read()
#             if not ret:
#                 print("[INFO] Selesai memproses video.")
#                 break

#             anotasi = model.predict(frame, conf=0.5, device=device)
#             deteksian = anotasi[0].boxes
#             trakingDeteksian = []

#             # Gambar ROI di frame
#             cv2.polylines(frame, [roi_polygon.astype(int)], isClosed=True, color=(0, 255, 0), thickness=2)

#             # Deteksi kendaraan dalam ROI (lanjutan, tidak ada perubahan di sini)
#             for box in deteksian:
#                 x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
#                 conf = float(box.conf[0].cpu().numpy())
#                 kelas = int(box.cls[0].cpu().numpy())
#                 jenisKendaraan = model.names[kelas]

#                 # Asumsi 'kendaraan' sudah didefinisikan di luar fungsi
#                 # Pastikan 'kendaraan' adalah list/set dari jenis kendaraan yang relevan
#                 # if jenisKendaraan in kendaraan: # Baris ini saya non-aktifkan karena 'kendaraan' tidak ada di input fungsi
#                 if True: # Ganti dengan if jenisKendaraan in kendaraan: jika 'kendaraan' tersedia
#                      bbox = [x1, y1, x2, y2]
#                      # Asumsi 'dalam_roi' sudah didefinisikan di luar fungsi
#                      # if dalam_roi(roi_polygon, bbox): # Baris ini saya non-aktifkan karena 'dalam_roi' tidak ada di input fungsi
#                      if True: # Ganti dengan if dalam_roi(roi_polygon, bbox): jika 'dalam_roi' tersedia
#                         trakingDeteksian.append(([x1, y1, x2 - x1, y2 - y1], conf, kelas, jenisKendaraan))


#             tracks = tracking.update_tracks(trakingDeteksian, frame=frame)
            
#             total_speed_pixel = 0
#             tracked_objects_in_roi = 0
#             current_centers = {}
            
#             # Hapus total_poin_kepadatan
#             # total_poin_kepadatan = 0 
            
#             # Gambar hasil tracking
#             for track in tracks :
#                 if not track.is_confirmed() :
#                     continue
                
#                 track_id = track.track_id
#                 ltrb = track.to_ltrb() 
#                 center_track = (int((ltrb[0] + ltrb[2]) / 2), int((ltrb[1] + ltrb[3]) / 2))
#                 x1, y1, x2, y2 = ltrb
                
#                 if cv2.pointPolygonTest(roi_polygon, center_track, False) >= 0:
#                     tracked_objects_in_roi += 1 # Hanya menghitung jumlah
                    
#                     # --- 1. HITUNG KECEPATAN (VELOCITY) ---
#                     current_centers[track_id] = center_track
#                     if track_id in last_centers:
#                         prev_center = last_centers[track_id]
#                         dx = center_track[0] - prev_center[0]
#                         dy = center_track[1] - prev_center[1]
#                         speed = np.sqrt(dx**2 + dy**2)
#                         total_speed_pixel += speed
                        
#                     # --- 2. HAPUS PERHITUNGAN BOBOT KENDARAAN ---
#                     # Hapus semua baris kode yang bertujuan mencari 'jenis' dan 'bobot'
#                     # total_poin_kepadatan += bobot # Baris ini Dihapus!
                    
#                     # Logika mendapatkan jenis (Sederhana/Cepat) Dihapus
#                     jenis = 'car'
#                     for d in trakingDeteksian:
#                         bx, by, bw, bh = d[0]
#                         if abs(bx - x1) < 50 and abs(by - y1) < 50:
#                             jenis = d[3]
#                             break
                    
#                     # --- Update Visualisasi Kotak ---
#                     cv2.rectangle(frame, (int(x1),int(y1)),(int(x2),int(y2)),(0,255,0),2)
#                     # Teks: Hapus informasi Poin Bobot, hanya tampilkan ID dan Jenis
#                     # teks = f"ID {track_id} {jenis}" 
#                     # cv2.putText(frame,teks, (int(x1) ,int(y1)-10),cv2.FONT_HERSHEY_COMPLEX,0.6,(0,0,0),2)


#             # Update last_centers untuk frame berikutnya
#             last_centers.clear()
#             last_centers.update(current_centers)

#             # --- 3. KLASIFIKASI HYBRID (Menggunakan Jumlah Kendaraan) ---
            
#             if tracked_objects_in_roi > 0:
#                 avg_speed = total_speed_pixel / tracked_objects_in_roi
#             else:
#                 avg_speed = 0
            
#             status_kepadatan = "LANCAR"
#             warna_status = (0, 255, 0) # Hijau
            
#             # Ganti semua total_poin_kepadatan dengan tracked_objects_in_roi
#             jumlah_kendaraan_saat_ini = tracked_objects_in_roi
#             # Ubah ambang batas agar merujuk ke JUMLAH KENDARAAN
#             # BATAS_LANCAR = 5   # Ambang batas jumlah kendaraan untuk Lancar
#             # BATAS_PADAT = 15   # Ambang batas jumlah kendaraan untuk Macet/Padat
#             # BATAS_KECEPATAN_LAMBAT = 5.0
#             if jumlah_kendaraan_saat_ini <= BATAS_LANCAR:
#                  status_kepadatan = "LANCAR"
#                  warna_status = (0, 255, 0)
            
#             elif jumlah_kendaraan_saat_ini > BATAS_LANCAR and avg_speed > BATAS_KECEPATAN_LAMBAT:
#                  status_kepadatan = "RAMAI LANCAR"
#                  warna_status = (0, 165, 255) # Oranye
            
#             elif jumlah_kendaraan_saat_ini > BATAS_PADAT and avg_speed <= BATAS_KECEPATAN_LAMBAT:
#                  status_kepadatan = "MACET TOTAL"
#                  warna_status = (0, 0, 255) # Merah
            
#             elif jumlah_kendaraan_saat_ini > BATAS_LANCAR and avg_speed <= BATAS_KECEPATAN_LAMBAT:
#                  status_kepadatan = "PADAT PELAN"
#                  warna_status = (0, 100, 255) # Merah Oranye

#             # --- 4. TAMPILAN GUI (HUD) ---
#             cv2.rectangle(frame, (0, 0), (500, 150), (0, 0, 0), -1)
            
#             cv2.putText(frame,f"Kendaraan di ROI : {tracked_objects_in_roi}",(30,30),cv2.FONT_HERSHEY_COMPLEX,0.6,(255,255,255),2)
#             # Baris ini diubah: Hapus 'Total Poin Bobot'
#             cv2.putText(frame,f"Amb. Lancar/Padat: {BATAS_LANCAR}/{BATAS_PADAT} Kendaraan",(30,60),cv2.FONT_HERSHEY_COMPLEX,0.6,(255,255,255),2) 
#             cv2.putText(frame,f"Rata-rata Kecepatan : {avg_speed:.2f} p/f",(30,90),cv2.FONT_HERSHEY_COMPLEX,0.6,(255,255,255),2)
#             cv2.putText(frame,f"STATUS: {status_kepadatan}",(30,120),cv2.FONT_HERSHEY_COMPLEX,1,warna_status,3)

#             cv2.imshow("Video",frame)

#         if cv2.waitKey(1) & 0xFF == ord('\x1b') :
#             break
#         elif cv2.waitKey(1) & 0xFF == 32 :
#             pause = True
#         elif cv2.waitKey(1) & 0xFF ==  ord('p'):
#             pause = False


#     capture.release()
#     cv2.destroyAllWindows()


def deteksi(capture, model, tracking, rois, device, last_centers):
    pause = False
    
    # --- KONFIGURASI UMUM ---
    BATAS_LANCAR = 5
    BATAS_PADAT = 15
    BATAS_KECEPATAN_LAMBAT = 5.0
    BUFFER_SIZE = 45
    filename_csv = "laporan_kepadatan_multi.csv"

    # --- INISIALISASI VARIABEL PER LAJUR ---
    # Kita butuh buffer dan status logging UNTUK SETIAP LAJUR
    # Contoh struktur: buffers = {'Lajur Kiri': deque(...), 'Lajur Kanan': deque(...)}
    lane_buffers = {nama: deque(maxlen=BUFFER_SIZE) for nama in rois.keys()}
    lane_last_status = {nama: None for nama in rois.keys()}

    nama_window = "Sistem Deteksi Multi-Lajur"
    # cv2.namedWindow(nama_window, cv2.WINDOW_NORMAL)
    # cv2.setWindowProperty(nama_window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    while True:
        if not pause:
            ret, frame = capture.read()
            if not ret: break

            anotasi = model.predict(frame, conf=0.5, device=device, verbose=False)
            deteksian = anotasi[0].boxes
            trakingDeteksian = []

            # --- 1. GAMBAR SEMUA ROI ---
            for nama, poly in rois.items():
                cv2.polylines(frame, [poly], isClosed=True, color=(255, 0, 0), thickness=2)
                # Tulis nama lajur di pojok ROI (opsional, ambil titik pertama)
                # cv2.putText(frame, nama, tuple(poly[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

            # --- 2. DETEKSI MASUK KE TRACKER ---
            # Kita masukkan semua kendaraan yang masuk ke ROI MANAPUN
            for box in deteksian:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                kelas = int(box.cls[0].cpu().numpy())
                jenis = model.names[kelas]
                
                if jenis in ["car", "motorcycle", "bus", "truck"]:
                    bbox_center = (int((x1+x2)/2), int((y1+y2)/2))
                    
                    # Cek apakah masuk ke SALAH SATU ROI
                    in_any_roi = False
                    for poly in rois.values():
                        if cv2.pointPolygonTest(poly, bbox_center, False) >= 0:
                            in_any_roi = True
                            break
                    
                    if in_any_roi:
                        trakingDeteksian.append(([x1, y1, x2 - x1, y2 - y1], conf, kelas, jenis))

            tracks = tracking.update_tracks(trakingDeteksian, frame=frame)

            # --- 3. RESET HITUNGAN PER FRAME (PER LAJUR) ---
            # Struktur: {'Lajur Kiri': 0, 'Lajur Kanan': 0}
            lane_counts = {nama: 0 for nama in rois.keys()}
            lane_speeds = {nama: 0.0 for nama in rois.keys()}
            current_centers = {}

            # --- 4. LOOP TRACKING ---
            for track in tracks:
                if not track.is_confirmed(): continue
                
                track_id = track.track_id
                ltrb = track.to_ltrb()
                center = (int((ltrb[0] + ltrb[2]) / 2), int((ltrb[1] + ltrb[3]) / 2))
                
                # Cek kendaraan ini ada di LAJUR MANA?
                obj_lane_name = None
                for nama, poly in rois.items():
                    if cv2.pointPolygonTest(poly, center, False) >= 0:
                        obj_lane_name = nama
                        break # Satu mobil cuma bisa di satu lajur
                
                if obj_lane_name:
                    # Tambah hitungan untuk lajur tersebut
                    lane_counts[obj_lane_name] += 1
                    
                    # Hitung Kecepatan
                    current_centers[track_id] = center
                    if track_id in last_centers:
                        prev = last_centers[track_id]
                        dist = np.sqrt((center[0]-prev[0])**2 + (center[1]-prev[1])**2)
                        lane_speeds[obj_lane_name] += dist # Tambah ke total speed lajur tersebut

                    # Visualisasi
                    cv2.rectangle(frame, (int(ltrb[0]), int(ltrb[1])), (int(ltrb[2]), int(ltrb[3])), (0,255,0), 2)
                    # cv2.putText(frame, f"{track_id}", (int(ltrb[0]), int(ltrb[1])-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

            last_centers.clear()
            last_centers.update(current_centers)

            # --- 5. PROSES STATISTIK & DISPLAY PER LAJUR ---
            
            frame_height, frame_width, _ = frame.shape
            # Background HUD (Lebih besar buat nampung 2 lajur)
            # cv2.rectangle(frame, (0, 0), (400, 50 + (len(rois) * 120)), (0, 0, 0), -1)
            # y_pos = 30 # Posisi Y awal untuk teks

            # Area untuk Lajur Kiri (Kiri Atas)
            # cv2.rectangle(frame, (0, 0), (400, 200), (0, 0, 0), -1) 
            # # Area untuk Lajur Kanan (Kanan Atas)
            # cv2.rectangle(frame, (frame_width - 400, 0), (frame_width, 200), (0, 0, 0), -1)


# ... (kode inisialisasi frame_width, dll) ...

# 1. Buat salinan frame untuk lapisan overlay
            overlay = frame.copy()

            # 2. Gambar rectangle pada lapisan overlay (masih pekat di tahap ini)
            # Area untuk Lajur Kiri (Kiri Atas)
            cv2.rectangle(overlay, (0, 0), (400, 200), (0, 0, 0), -1) 
            # Area untuk Lajur Kanan (Kanan Atas)
            cv2.rectangle(overlay, (frame_width - 400, 0), (frame_width, 200), (0, 0, 0), -1)

            # 3. Tentukan tingkat transparansi (Alpha)
            # 0.3 artinya 30% warna hitam, 70% gambar asli tetap terlihat
            alpha = 0.5  

            # 4. Gabungkan overlay dengan frame asli
            # Rumus: frame = (overlay * alpha) + (frame * (1 - alpha))
            frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

            # Sekarang 'frame' sudah memiliki kotak hitam transparan

            for nama in rois.keys():
                # A. Hitung Rata-rata Speed
                count = lane_counts[nama]
                total_spd = lane_speeds[nama]
                avg_spd = (total_spd / count) if count > 0 else 0

                # B. Tentukan Raw Status
                raw_st = "LANCAR"
                if count <= BATAS_LANCAR: raw_st = "LANCAR"
                elif count > BATAS_LANCAR and avg_spd > BATAS_KECEPATAN_LAMBAT: raw_st = "RAMAI LANCAR"
                elif count > BATAS_PADAT and avg_spd <= BATAS_KECEPATAN_LAMBAT: raw_st = "MACET TOTAL"
                elif count > BATAS_LANCAR and avg_spd <= BATAS_KECEPATAN_LAMBAT: raw_st = "PADAT PELAN"

                # C. Masukkan ke Buffer Lajur Ini
                lane_buffers[nama].append(raw_st)

                # D. Voting Status Final
                if len(lane_buffers[nama]) == BUFFER_SIZE:
                    final_st = Counter(lane_buffers[nama]).most_common(1)[0][0]
                else:
                    final_st = raw_st
                
                # E. Logging CSV (Per Lajur)
                if final_st != lane_last_status[nama]:
                    if lane_last_status[nama] is not None or final_st != "LANCAR":
                        catat_log_csv(filename_csv, nama, final_st, avg_spd, count)
                    lane_last_status[nama] = final_st

                # F. Tampilan HUD (Per Lajur)
                color = (0, 255, 0)
                if final_st == "MACET TOTAL": color = (0, 0, 255)
                elif final_st == "PADAT PELAN": color = (0, 100, 255)
                elif final_st == "RAMAI LANCAR": color = (0, 165, 255)

                if nama == "Lajur Kiri":
                    x_start = 10
                    y_start = 30
                    text_color = (255, 255, 0) # Warna teks untuk header lajur kiri
                elif nama == "Lajur Kanan":
                    x_start = frame_width - 390  # Geser ke kiri dari batas kanan (400 - 10)
                    y_start = 30
                    text_color = (0, 255, 255) # Warna teks untuk header lajur kanan

                cv2.putText(frame, f"--- {nama} ---", (x_start, y_start), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
                cv2.putText(frame, f"Jumlah kendaraan: {count}", (x_start, y_start + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
                cv2.putText(frame, f"Avg. Kecepatan: {avg_spd:.1f} p/f", (x_start, y_start + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
                cv2.putText(frame, f"STATUS: {final_st}", (x_start, y_start + 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # Geser ke bawah untuk lajur berikutnya
                # y_pos += 100 

            cv2.imshow(nama_window, frame)

        # Keyboard control (sama)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('\x1b'): break
        elif key == 32: pause = True
        elif key == ord('p'): pause = False

    capture.release()
    cv2.destroyAllWindows()
# ============================
# MAIN PROGRAM
# ============================
if __name__ == "__main__":
    # capture, model, tracking, device = konfig(config)
    capture, model, tracking,device ,last_centers= konfig(config)

    
    # DAFTAR NAMA LAJUR YANG INGIN DIBUAT
    daftar_lajur_jalan = ["Lajur Kiri", "Lajur Kanan"] 
    
    # Panggil fungsi gambar multi roi
    rois = gambar_multi_roi(config["sumberVideo"], daftar_lajur_jalan)
    
    if rois is None:
        print("ROI tidak dibuat.")
        exit()

    last_centers = {}
    deteksi(capture, model, tracking, rois, device, last_centers)


# konfig(config):
#     video = config["sumberVideo"]
#     modelPath = config["model"]
#     model = YOLO(modelPath)
#     tracking = DeepSort(max_age=25, max_cosine_distance=0.3)
#     capture = cv2.VideoCapture(video)
#     device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
#     last_centers = {}
#     if not capture.isOpened():
#         print(f"[ERROR] Video {video} tidak bisa dibuka bro.")
#         exit()
#     return capture, model, tracking, device, last_centers