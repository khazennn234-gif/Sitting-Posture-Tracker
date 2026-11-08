from ultralytics import YOLO
import torch

# ============================================================
# Training YOLOv11 dengan Dataset Gabungan Lengkap (v1, v3, & v4 Webcam)
# ============================================================
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Training pada device: {device}")

# Menggunakan yolo11n.pt (nano) agar ringan, cepat, dan akurat
model = YOLO("yolo11n.pt")
model.to(device)

# Training model
results = model.train(
    data="dataset_combined/data.yaml",
    epochs=8,               # 8 epoch optimal untuk konvergensi & akurasi tinggi di CPU
    imgsz=416,              # ukuran citra input
    batch=16,               # ukuran batch
    name="sitting_posture_model",
    exist_ok=True,
    patience=5,
    save=True,
    plots=True
)

print("\n" + "=" * 55)
print("  TRAINING SELESAI!")
print("  Model tersimpan di: runs/detect/sitting_posture_model/weights/best.pt")
print("=" * 55)
