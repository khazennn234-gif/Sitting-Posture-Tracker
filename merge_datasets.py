import os
import shutil
import glob

COMBINED_DIR = os.path.abspath("dataset_combined")
UAS_DIR = os.path.abspath("UAS-Sitting-Posture.v3i.yolov11")
V1_DIR = os.path.abspath("sitting-posture.v1i.yolov11")
V4_DIR = os.path.abspath("sitting posture.v4i.yolov11")

# Bersihkan direktori gabungan sebelumnya
if os.path.exists(COMBINED_DIR):
    shutil.rmtree(COMBINED_DIR)

for split in ["train", "valid", "test"]:
    os.makedirs(os.path.join(COMBINED_DIR, split, "images"), exist_ok=True)
    os.makedirs(os.path.join(COMBINED_DIR, split, "labels"), exist_ok=True)

# -------------------------------------------------------------------------
# 1. Dataset 1: UAS v3 (0 = baik, 1 = buruk) - Sudut samping / ruangan
# -------------------------------------------------------------------------
print("[1/3] Menggabungkan UAS-Sitting-Posture.v3i.yolov11...")
for split in ["train", "valid", "test"]:
    img_src = os.path.join(UAS_DIR, split, "images")
    lbl_src = os.path.join(UAS_DIR, split, "labels")
    if not os.path.exists(img_src): continue
    for img_path in glob.glob(os.path.join(img_src, "*.*")):
        fname = os.path.basename(img_path)
        base, ext = os.path.splitext(fname)
        if ext.lower() not in [".jpg", ".jpeg", ".png"]: continue
        shutil.copy2(img_path, os.path.join(COMBINED_DIR, split, "images", f"uas_{fname}"))
        lbl_file = os.path.join(lbl_src, f"{base}.txt")
        if os.path.exists(lbl_file):
            shutil.copy2(lbl_file, os.path.join(COMBINED_DIR, split, "labels", f"uas_{base}.txt"))

# -------------------------------------------------------------------------
# 2. Dataset 2: sitting-posture v1 (0 = bad -> 1 buruk, 1 = good -> 0 baik)
# -------------------------------------------------------------------------
print("[2/3] Menggabungkan sitting-posture.v1i.yolov11 (konversi label)...")
v1_mapping = {0: 1, 1: 0}
for split in ["train", "valid", "test"]:
    img_src = os.path.join(V1_DIR, split, "images")
    lbl_src = os.path.join(V1_DIR, split, "labels")
    if not os.path.exists(img_src): continue
    for img_path in glob.glob(os.path.join(img_src, "*.*")):
        fname = os.path.basename(img_path)
        base, ext = os.path.splitext(fname)
        if ext.lower() not in [".jpg", ".jpeg", ".png"]: continue
        shutil.copy2(img_path, os.path.join(COMBINED_DIR, split, "images", f"v1_{fname}"))
        lbl_file = os.path.join(lbl_src, f"{base}.txt")
        if os.path.exists(lbl_file):
            new_lbl_file = os.path.join(COMBINED_DIR, split, "labels", f"v1_{base}.txt")
            with open(lbl_file, "r") as f_in, open(new_lbl_file, "w") as f_out:
                for line in f_in:
                    p = line.strip().split()
                    if p:
                        p[0] = str(v1_mapping.get(int(p[0]), int(p[0])))
                        f_out.write(" ".join(p) + "\n")

# -------------------------------------------------------------------------
# 3. Dataset 3: sitting posture.v4i (Terbaru - Webcam Laptop dari depan!)
# (0 = bad -> 1 buruk, 1 = good -> 0 baik)
# Kita gandakan 3x pada data train agar model sensitif mengenali posisi depan webcam
# -------------------------------------------------------------------------
print("[3/3] Menggabungkan sitting posture.v4i.yolov11 (Webcam Depan Laptop)...")
v4_mapping = {0: 1, 1: 0}
for split in ["train", "valid", "test"]:
    img_src = os.path.join(V4_DIR, split, "images")
    lbl_src = os.path.join(V4_DIR, split, "labels")
    if not os.path.exists(img_src): continue
    
    # Untuk train kita lakukan 3x pembobotan agar webcam laptop terdeteksi optimal
    repeat_count = 3 if split == "train" else 1

    for r in range(repeat_count):
        prefix_tag = f"v4_r{r}_" if split == "train" else "v4_"
        for img_path in glob.glob(os.path.join(img_src, "*.*")):
            fname = os.path.basename(img_path)
            base, ext = os.path.splitext(fname)
            if ext.lower() not in [".jpg", ".jpeg", ".png"]: continue
            
            dest_img_name = f"{prefix_tag}{fname}"
            shutil.copy2(img_path, os.path.join(COMBINED_DIR, split, "images", dest_img_name))
            
            lbl_file = os.path.join(lbl_src, f"{base}.txt")
            if os.path.exists(lbl_file):
                dest_lbl_name = f"{prefix_tag}{base}.txt"
                new_lbl_file = os.path.join(COMBINED_DIR, split, "labels", dest_lbl_name)
                with open(lbl_file, "r") as f_in, open(new_lbl_file, "w") as f_out:
                    for line in f_in:
                        p = line.strip().split()
                        if p:
                            p[0] = str(v4_mapping.get(int(p[0]), int(p[0])))
                            f_out.write(" ".join(p) + "\n")

# Buat konfigurasi data.yaml
yaml_content = f"""path: {COMBINED_DIR.replace(chr(92), '/')}
train: train/images
val: valid/images
test: test/images

nc: 2
names: ['baik', 'buruk']
"""

with open(os.path.join(COMBINED_DIR, "data.yaml"), "w") as f:
    f.write(yaml_content)

print("\n" + "=" * 50)
print("  SEMUA DATASET (TERMASUK WEBCAM v4) TELAH DIGABUNG")
print("=" * 50)
for split in ["train", "valid", "test"]:
    c_img = len(os.listdir(os.path.join(COMBINED_DIR, split, "images")))
    c_lbl = len(os.listdir(os.path.join(COMBINED_DIR, split, "labels")))
    print(f"  {split}: {c_img} images, {c_lbl} labels")
