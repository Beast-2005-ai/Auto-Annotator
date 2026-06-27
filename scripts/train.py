import os
from ultralytics import YOLO

def main():
    workspace = os.environ.get("PIPELINE_WORKSPACE", "data")
    yaml_path = os.path.abspath(os.path.join(workspace, "dataset.yaml"))
    project_path = os.path.abspath(workspace) 
    status_path = os.path.join(workspace, "status.txt")
    
    print(f"[*] Starting YOLO training inside {project_path}...")
    model = YOLO('yolov8n.pt')
    
    # --- Live Epoch Tracker Callback ---
    def on_train_epoch_end(trainer):
        epoch = trainer.epoch + 1
        total = trainer.epochs
        with open(status_path, "w") as f:
            f.write(f"TRAINING STUDENT MODEL (GPU ACTIVE)... ({epoch}/{total})")
            
    model.add_callback("on_train_epoch_end", on_train_epoch_end)
    
    # --- UPDATED: 30 Epochs & Heavy Augmentation ---
    model.train(
        data=yaml_path, 
        epochs=30,  # Increased from 10 for better accuracy
        project=project_path,
        name="train_results", 
        exist_ok=True,
        workers=0,
        batch=8,
        # Manually forcing Data Augmentations:
        hsv_v=0.6,    # 60% variance in brightness/value (helps with dark images)
        fliplr=0.5,   # 50% chance to flip horizontally
        degrees=10.0, # Rotate images slightly
        mosaic=1.0    # Stitches images together for context scaling
    )
    
    print("[*] Training Complete. Weights saved to workspace.")

if __name__ == "__main__":
    main()