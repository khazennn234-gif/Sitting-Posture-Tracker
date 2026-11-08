from ultralytics import YOLO
import torch
import cv2
import numpy as np
import time
import os

# ============================================================
# Modul Audio (Anti-Spam Peringatan Postur Buruk)
# Mendukung Pygame dan Windows Native MCI (tanpa dependensi luar)
# ============================================================
AUDIO_FILE = "hey-antek-antek-asing-prabowo.mp3"
AUDIO_COOLDOWN = 10  # detik jeda agar tidak spam audio
last_audio_time = 0

has_pygame = False
try:
    import pygame
    pygame.mixer.init()
    alert_sound = pygame.mixer.Sound(AUDIO_FILE)
    has_pygame = True
    print("[INFO] Audio engine: Pygame Mixer")
except Exception:
    import ctypes
    has_pygame = False
    print("[INFO] Audio engine: Windows Native MCI (ctypes)")

def play_alert_audio():
    """Memutar file audio peringatan"""
    global last_audio_time
    if has_pygame:
        alert_sound.play()
    else:
        abs_path = os.path.abspath(AUDIO_FILE)
        ctypes.windll.winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias alert', None, 0, None)
        ctypes.windll.winmm.mciSendStringW('play alert from 0', None, 0, None)

def is_audio_playing():
    """Mengecek apakah audio sedang berlangsung"""
    if has_pygame:
        return pygame.mixer.get_busy()
    else:
        buf = ctypes.create_unicode_buffer(128)
        ctypes.windll.winmm.mciSendStringW('status alert mode', buf, 128, None)
        return buf.value == 'playing'

def close_audio():
    """Menutup engine audio saat program selesai"""
    if has_pygame:
        pygame.mixer.quit()
    else:
        ctypes.windll.winmm.mciSendStringW('stop alert', None, 0, None)
        ctypes.windll.winmm.mciSendStringW('close alert', None, 0, None)

# ============================================================
# Inisialisasi Model YOLO (dari YOLO.py)
# ============================================================
device = "cuda" if torch.cuda.is_available() else "cpu"

# Cari model terbaik hasil training dataset gabungan (v1, v3, & v4 webcam)
model_path = "best.pt"
candidates = [
    "runs/detect/sitting_posture_model/weights/best.pt",
    "best.pt",
    "yolo11n.pt"
]
for candidate in candidates:
    if os.path.exists(candidate):
        model_path = candidate
        break

print(f"[INFO] Memuat model: {model_path} pada device: {device}")
model = YOLO(model_path)
model.to(device)

# Kelas postur yang difokuskan (dari data.yaml dataset gabungan)
focused_classes = ["baik", "buruk"]

# Ambang batas kepercayaan deteksi (dibuat 0.25 agar sensitif menangkap webcam laptop)
CONFIDENCE_THRESHOLD = 0.25

# ============================================================
# Inisialisasi Video Capture (dari ReadDisplayVideo.py & YOLO.py)
# ============================================================
# cap = cv2.VideoCapture("mentahan.mp4")  # untuk video dari file
cap = cv2.VideoCapture(0)                 # untuk video langsung dari webcam laptop

# Check if camera opened successfully (dari ReadDisplayVideo.py)
if not cap.isOpened():
    print("[ERROR] Tidak dapat membuka webcam atau file video!")
    exit()

# Setup VideoWriter untuk menyimpan video output (dari YOLO.py)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
output_path = "output_posture.mp4"
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

print("\n" + "=" * 55)
print("  TRACKER POSTUR DUDUK (WEBCAM & AUDIO ALERT) AKTIF")
print("  Tekan 'q' pada jendela video untuk keluar")
print("=" * 55 + "\n")

# ============================================================
# Loop Deteksi Real-Time (dari YOLO.py + ReadDisplayVideo.py)
# ============================================================
while cap.isOpened():
    # Capture frame-by-frame (dari ReadDisplayVideo.py)
    ret, frame = cap.read()
    if not ret:
        break

    # Lakukan proses deteksi objek (dari YOLO.py)
    results = model(frame, verbose=False)

    is_bad_posture = False
    detected_count = 0

    # Iterasi tiap hasil deteksi (dari YOLO.py)
    for result in results:
        boxes = result.boxes
        names = model.names

        # Hitung jumlah objek per label (dari YOLO.py)
        label_counts = {label: 0 for label in focused_classes}

        for box in boxes:
            x1, y1, x2, y2 = np.asarray(box.xyxy[0]).astype(int)
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])

            # Ambil label kelas dari model
            label = names[cls_id] if cls_id in names else str(cls_id)

            if confidence > CONFIDENCE_THRESHOLD:
                detected_count += 1
                if label in label_counts:
                    label_counts[label] += 1

                # Tentukan warna & status:
                # Merah = Buruk, Hijau = Baik
                if label in ["buruk", "bad"]:
                    color = (0, 0, 255)   # Merah (BGR)
                    is_bad_posture = True
                    display_text = f"Person (BURUK): {confidence*100:.0f}%"
                else:
                    color = (0, 255, 0)   # Hijau (BGR)
                    display_text = f"Person (BAIK): {confidence*100:.0f}%"

                # Gambar bounding box dan label (dari YOLO.py)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    display_text,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_PLAIN,
                    1.2,
                    color,
                    2,
                )

        # Tampilkan teks ringkasan jumlah objek di pojok kiri atas (dari YOLO.py)
        summary = ", ".join([f"{k.upper()}: {v}" for k, v in label_counts.items() if v > 0])
        if summary:
            box_padding = 12
            (text_width, text_height), _ = cv2.getTextSize(summary, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            bg_color = (0, 0, 200) if is_bad_posture else (0, 180, 0)
            cv2.rectangle(frame, (5, 5), (5 + text_width + box_padding, 5 + text_height + box_padding), bg_color, -1)
            cv2.putText(frame, summary, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        else:
            # Jika belum ada postur terdeteksi, tampilkan status panduan
            cv2.putText(frame, "Mencari Postur... Duduk di depan webcam", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # ========================================================
    # Logika Anti-Spam Audio (Kontrol Logika Praktikum FUZZY.py)
    # Aturan: Hanya bunyikan jika terdeteksi buruk, audio tidak jalan,
    # dan jeda cooldown minimal 10 detik sudah terlewati.
    # ========================================================
    if is_bad_posture:
        current_time = time.time()
        cooldown_lewat = (current_time - last_audio_time) >= AUDIO_COOLDOWN
        audio_bebas = not is_audio_playing()

        if cooldown_lewat and audio_bebas:
            print("⚠️  [PERINGATAN] Postur buruk terdeteksi! Memutar audio...")
            play_alert_audio()
            last_audio_time = current_time

    # Simpan frame ke output video (dari YOLO.py)
    out.write(frame)

    # Tampilkan frame dengan deteksi objek (dari YOLO.py & ReadDisplayVideo.py)
    cv2.imshow("Sitting Posture Tracker - YOLOv11", frame)

    # Tekan 'q' untuk keluar (dari ReadDisplayVideo.py & YOLO.py)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Bersihkan resource (dari ReadDisplayVideo.py & YOLO.py)
cap.release()
out.release()
cv2.destroyAllWindows()
close_audio()
print("\n[INFO] Program selesai.")
