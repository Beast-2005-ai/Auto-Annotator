import os, shutil, random, glob

def main():
    workspace = os.environ.get("PIPELINE_WORKSPACE", "data")
    images_dir = os.path.join(workspace, "extracted_frames")
    labels_dir = os.path.join(workspace, "labels")
    dataset_dir = os.path.join(workspace, "dataset")

    for split in ['train', 'val']:
        os.makedirs(os.path.join(dataset_dir, split, 'images'), exist_ok=True)
        os.makedirs(os.path.join(dataset_dir, split, 'labels'), exist_ok=True)

    images = glob.glob(os.path.join(images_dir, "*.jpg"))
    random.shuffle(images)
    
    split_idx = int(len(images) * 0.8)
    train_imgs = images[:split_idx]
    val_imgs = images[split_idx:]

    def copy_files(img_paths, split_name):
        for img_path in img_paths:
            base_name = os.path.basename(img_path)
            label_path = os.path.join(labels_dir, base_name.replace(".jpg", ".txt"))
            
            if os.path.exists(label_path):
                shutil.copy(img_path, os.path.join(dataset_dir, split_name, 'images', base_name))
                shutil.copy(label_path, os.path.join(dataset_dir, split_name, 'labels', os.path.basename(label_path)))

    copy_files(train_imgs, 'train')
    copy_files(val_imgs, 'val')
    print("Dataset split complete.")

if __name__ == "__main__":
    main()