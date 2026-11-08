# 🪑 Sitting Posture Tracker — YOLOv11 + Webcam & Audio Alert

Sistem pelacakan dan deteksi postur duduk **baik** dan **buruk** secara real-time menggunakan **YOLOv11**, digabungkan dengan modul codingan praktikum (`YOLO.py`, `ReadDisplayVideo.py`, `ReadImageData.py`, `FUZZY.py`).

Sistem ini telah dioptimalkan khusus untuk **webcam laptop dari arah depan**, menggabungkan seluruh dataset yang tersedia termasuk dataset terbaru (`sitting posture.v4i.yolov11`). Ketika postur buruk terdeteksi, audio peringatan ([hey-antek-antek-asing-prabowo.mp3](file:///c:/Users/ADVAN/Downloads/SITTING%20POSE/hey-antek-antek-asing-prabowo.mp3)) akan diputar dengan sistem **anti-spam cooldown**.

---

## 📁 Struktur Dataset & Proyek

```
SITTING POSE/
├── SittingPostureTracker.md          ← Dokumentasi panduan eksekusi
├── merge_datasets.py                 ← Penggabung 3 dataset (termasuk v4 webcam laptop)
├── dataset_combined/                 ← Dataset gabungan (1.502 train, 126 val, 56 test)
│   ├── data.yaml                     ← Konfigurasi YOLO gabungan
│   ├── train/ (images & labels)
│   ├── valid/ (images & labels)
│   └── test/  (images & labels)
├── train_model.py                    ← Script training YOLOv11
├── sitting_posture_tracker.py        ← Script utama deteksi & tracking real-time
├── hey-antek-antek-asing-prabowo.mp3 ← File audio peringatan
│
├── sitting posture.v4i.yolov11/      ← DATASET TERBARU: Khusus webcam laptop dari depan!
├── UAS-Sitting-Posture.v3i.yolov11/  ← Dataset sudut ruangan / samping
├── sitting-posture.v1i.yolov11/      ← Dataset meja kerja
│
├── YOLO.py                           ← Praktikum: Deteksi objek & visualisasi bounding box
├── ReadDisplayVideo.py               ← Praktikum: Baca & tampil video/kamera
├── ReadImageData.py                  ← Praktikum: Pembacaan data citra
└── FUZZY.py                          ← Praktikum: Logika aturan & kontrol sistem
```

---

## 💡 Mengapa Sebelumnya Tidak Terdeteksi dari Depan Webcam?

1. **Dataset Lama Berorientasi Samping**:
   Dataset `UAS-Sitting-Posture.v3i` hampir seluruhnya berisi sudut samping (*side-view*) yang direkam dari kejauhan. Ketika duduk tepat di depan webcam laptop (*front-view* / *close-up* dada ke atas), sudut pandangnya berbeda drastis.
2. **Dataset Terbaru (`sitting posture.v4i`) adalah Webcam Laptop**:
   Dataset `v4` berisi rekaman `WIN_20240921_...` dari aplikasi kamera laptop dengan sudut pandang frontal/depan.
3. **Pembobotan (*Oversampling*)**:
   Dataset v4 diperbanyak 3x pada data training agar model memiliki representasi yang kuat untuk posisi duduk di depan webcam laptop.
4. **Visualisasi Deteksi Person**:
   Label kini menampilkan `Person (BAIK): XX%` atau `Person (BURUK): XX%` dengan ambang batas `CONFIDENCE_THRESHOLD = 0.25` sehingga mendeteksi subjek pengguna secara responsif.

---

## 🔄 Tahap 1: Penggabungan 3 Dataset (`merge_datasets.py`)

Kedua dataset Roboflow menggunakan penamaan kelas yang berbeda:
- `UAS-Sitting-Posture.v3i`: `0: baik`, `1: buruk`
- `sitting-posture.v1i`: `0: bad`, `1: good`
- `sitting posture.v4i` (Terbaru): `0: bad`, `1: good`

Script `merge_datasets.py` menyelaraskan seluruh label menjadi:
- **`0: baik`**
- **`1: buruk`**

Jalankan penggabungan:
```powershell
python merge_datasets.py
```

Hasil gabungan:
- **Train**: 1.502 gambar & label
- **Valid**: 126 gambar & label
- **Test**: 56 gambar & label

---

## 🏋️ Tahap 2: Training YOLOv11 (`train_model.py`)

Menggunakan transfer learning dari `yolo11n.pt` pada dataset gabungan:

```powershell
python train_model.py
```

*Model terbaik akan disimpan di: `runs/detect/sitting_posture_model/weights/best.pt` dan disalin ke `best.pt`.*

---

## 🎯 Tahap 3: Script Utama (`sitting_posture_tracker.py`)

Script mengintegrasikan semua modul praktikum:

```python
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
except Exception:
    import ctypes
    has_pygame = False

def play_alert_audio():
    if has_pygame:
        alert_sound.play()
    else:
        abs_path = os.path.abspath(AUDIO_FILE)
        ctypes.windll.winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias alert', None, 0, None)
        ctypes.windll.winmm.mciSendStringW('play alert from 0', None, 0, None)

def is_audio_playing():
    if has_pygame:
        return pygame.mixer.get_busy()
    else:
        buf = ctypes.create_unicode_buffer(128)
        ctypes.windll.winmm.mciSendStringW('status alert mode', buf, 128, None)
        return buf.value == 'playing'

def close_audio():
    if has_pygame:
        pygame.mixer.quit()
    else:
        ctypes.windll.winmm.mciSendStringW('stop alert', None, 0, None)
        ctypes.windll.winmm.mciSendStringW('close alert', None, 0, None)

# Inisialisasi Model YOLO (dari YOLO.py)
device = "cuda" if torch.cuda.is_available() else "cpu"
model_path = "best.pt"
for candidate in ["runs/detect/sitting_posture_model/weights/best.pt", "best.pt", "yolo11n.pt"]:
    if os.path.exists(candidate):
        model_path = candidate
        break

model = YOLO(model_path)
model.to(device)

focused_classes = ["baik", "buruk"]
CONFIDENCE_THRESHOLD = 0.25

# Inisialisasi Video Capture (dari ReadDisplayVideo.py & YOLO.py)
cap = cv2.VideoCapture(0)  # Webcam laptop

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
output_path = "output_posture.mp4"
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

# Loop Deteksi Real-Time (dari YOLO.py + ReadDisplayVideo.py)
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)
    is_bad_posture = False

    for result in results:
        boxes = result.boxes
        names = model.names
        label_counts = {label: 0 for label in focused_classes}

        for box in boxes:
            x1, y1, x2, y2 = np.asarray(box.xyxy[0]).astype(int)
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            label = names[cls_id] if cls_id in names else str(cls_id)

            if confidence > CONFIDENCE_THRESHOLD:
                if label in label_counts:
                    label_counts[label] += 1

                if label in ["buruk", "bad"]:
                    color = (0, 0, 255)   # Merah
                    is_bad_posture = True
                    display_text = f"Person (BURUK): {confidence*100:.0f}%"
                else:
                    color = (0, 255, 0)   # Hijau
                    display_text = f"Person (BAIK): {confidence*100:.0f}%"

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, display_text, (x1, y1 - 10), cv2.FONT_HERSHEY_PLAIN, 1.2, color, 2)

        summary = ", ".join([f"{k.upper()}: {v}" for k, v in label_counts.items() if v > 0])
        if summary:
            box_padding = 12
            (tw, th), _ = cv2.getTextSize(summary, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            bg = (0, 0, 200) if is_bad_posture else (0, 180, 0)
            cv2.rectangle(frame, (5, 5), (5 + tw + box_padding, 5 + th + box_padding), bg, -1)
            cv2.putText(frame, summary, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        else:
            cv2.putText(frame, "Mencari Postur... Duduk di depan webcam", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # Logika Kontrol Anti-Spam Audio (FUZZY.py)
    if is_bad_posture:
        current_time = time.time()
        cooldown_lewat = (current_time - last_audio_time) >= AUDIO_COOLDOWN
        audio_bebas = not is_audio_playing()

        if cooldown_lewat and audio_bebas:
            print("⚠️  [PERINGATAN] Postur buruk terdeteksi! Memutar audio...")
            play_alert_audio()
            last_audio_time = current_time

    out.write(frame)
    cv2.imshow("Sitting Posture Tracker - YOLOv11", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
out.release()
cv2.destroyAllWindows()
close_audio()
```

---

## 🚀 Panduan Menjalankan

1. Jalankan tracker:
```powershell
python sitting_posture_tracker.py
```
2. Duduk di depan webcam laptop:
   - Jika postur tegak/baik $\rightarrow$ bounding box **Hijau**: `Person (BAIK)`
   - Jika membungkuk/postur buruk $\rightarrow$ bounding box **Merah**: `Person (BURUK)` dan audio `hey-antek-antek-asing-prabowo.mp3` diputar (cooldown 10 detik).
3. Tekan **`q`** pada jendela tampilan untuk keluar.
