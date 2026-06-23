import os
import random
import shutil
from tqdm import tqdm

def main():
    # Source paths
    IMAGE_SRC = "data/extracted_frames"
    LABEL_SRC = "data/labels"
    
    # Destination paths
    DEST_ROOT = "data/dataset"
    TRAIN_IMG_DIR = os.path.join(DEST_ROOT, "train", "images")
    TRAIN_LBL_DIR = os.path.join(DEST_ROOT, "train", "labels")
    VAL_IMG_DIR = os.path.join(DEST_ROOT, "val", "images")
    VAL_LBL_DIR = os.path.join(DEST_ROOT, "val", "labels")

    # Create directories
    for folder in [TRAIN_IMG_DIR, TRAIN_LBL_DIR, VAL_IMG_DIR, VAL_LBL_DIR]:
        os.makedirs(folder, exist_ok=True)

    # Get all matching pairs
    images = [f for f in os.listdir(IMAGE_SRC) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # Shuffle to ensure random distribution across splits
    random.seed(42)  # Fixed seed for repeatability
    random.shuffle(images)

    # Calculate split index (85% train, 15% val)
    split_idx = int(len(images) * 0.85)
    train_images = images[:split_idx]
    val_images = images[split_idx:]

    print(f"Splitting dataset: {len(train_images)} training images, {len(val_images)} validation images.")

    # Helper function to copy files safely
    def move_files(file_list, dest_img_dir, dest_lbl_dir):
        for img_name in file_list:
            base_name = os.path.splitext(img_name)[0]
            lbl_name = base_name + ".txt"

            src_img = os.path.join(IMAGE_SRC, img_name)
            src_lbl = os.path.join(LABEL_SRC, lbl_name)

            # Copy image
            shutil.copy(src_img, os.path.join(dest_img_dir, img_name))
            
            # Copy label if it exists (handles background frames with no objects safely)
            if os.path.exists(src_lbl):
                shutil.copy(src_lbl, os.path.join(dest_lbl_dir, lbl_name))

    # Execute copies
    move_files(train_images, TRAIN_IMG_DIR, TRAIN_LBL_DIR)
    move_files(val_images, VAL_IMG_DIR, VAL_LBL_DIR)

    print(f"Dataset successfully created at: {DEST_ROOT}")

if __name__ == "__main__":
    main()