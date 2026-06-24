import os
from ultralytics import YOLO

def main():
    workspace = os.environ.get("PIPELINE_WORKSPACE", "data")
    yaml_path = os.path.abspath(os.path.join(workspace, "dataset.yaml"))
    project_path = os.path.abspath(workspace) 
    status_path = os.path.join(workspace, "status.txt")
    
    print(f"[*] Starting YOLO training inside {project_path}...")
    model = YOLO('yolov8n.pt')
    
    # --- NEW: Live Epoch Tracker Callback ---
    def on_train_epoch_end(trainer):
        epoch = trainer.epoch + 1
        total = trainer.epochs
        with open(status_path, "w") as f:
            f.write(f"TRAINING STUDENT MODEL (GPU ACTIVE)... ({epoch}/{total})")
            
    # Attach the tracker to the YOLO engine
    model.add_callback("on_train_epoch_end", on_train_epoch_end)
    
    model.train(
        data=yaml_path, 
        epochs=10, 
        project=project_path,
        name="train_results", 
        exist_ok=True,
        workers=0,
        batch=8
    )
    
    print("[*] Training Complete. Weights saved to workspace.")

if __name__ == "__main__":
    main()