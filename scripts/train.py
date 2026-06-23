import os
import torch
from ultralytics import YOLO

def main():
    # 1. Verify CUDA is active for Ultralytics
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Using device: {torch.cuda.get_device_name(0) if device == 0 else 'CPU'}")

    # 2. Load a pre-trained YOLOv8 Nano model
    # This downloads 'yolov8n.pt' automatically (around 6MB)
    model = YOLO("yolov8n.pt")

    # 3. Freeze the Backbone
    # YOLOv8 has 22 layers. Layers 0 to 9 make up the backbone (features/edges).
    # We freeze them to drastically speed up training and prevent over-fitting.
    freeze_layer_count = 10 
    freeze_list = [f"model.{x}." for x in range(freeze_layer_count)]
    
    for k, v in model.model.named_parameters():
        if any(x in k for x in freeze_list):
            v.requires_grad = False
            
    print(f"Successfully froze the first {freeze_layer_count} layers (Backbone).")

    # 4. Train the Model
    # Since we are working with a small 71-image dataset, 30 epochs is plenty 
    # to see if the concept succeeds.
    model.train(
        data="dataset.yaml",      
        epochs=100,                # Bumped to 50 epochs to let it learn the rotations
        imgsz=640,                
        batch=16,                 
        device=device,            
        workers=2,                
        name="steel_bottle_proto",
        exist_ok=True,
        
        # --- DATA AUGMENTATION HYPERPARAMETERS ---
        degrees=90.0,             # Randomly rotate images by up to 90 degrees (Fixes horizontal issue)
        flipud=0.5,               # 50% chance to flip image upside down
        fliplr=0.5,               # 50% chance to flip image left-to-right
        scale=0.5,                # Scale object up/down by 50% to handle distance
        perspective=0.001         # Slight 3D perspective distortion
    )

if __name__ == "__main__":
    main()