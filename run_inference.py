import cv2
import torch
import os
from ultralytics import YOLO

def main():
    print("=== STARTING LIVE INFERENCE ===")
    
    # This path matches the name parameter in your train.py script
    # Update "steel_bottle_proto" if you changed the 'name' argument in train.py
    WEIGHTS_PATH = "runs/detect/steel_bottle_proto/weights/best.pt"
    
    if not os.path.exists(WEIGHTS_PATH):
        print(f"[!] Error: Weights not found at {WEIGHTS_PATH}")
        print("Did you run the training pipeline first?")
        return

    # GPU Check
    device = 0 if torch.cuda.is_available() else "cpu"
    gpu_name = torch.cuda.get_device_name(0) if device == 0 else "CPU"
    print(f"[*] Loading custom weights onto: {gpu_name}")

    # Load Model
    model = YOLO(WEIGHTS_PATH).to(device)
    
    # Initialize Camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[!] Error: Could not access webcam.")
        return

    cv2.namedWindow("Live Multi-Class Inference", cv2.WINDOW_NORMAL)
    print("\n[*] Camera active. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Inference (Using 0.35 threshold to balance augmented training)
        results = model(frame, stream=True, device=device, conf=0.35)

        for r in results:
            annotated_frame = r.plot()

        cv2.imshow("Live Multi-Class Inference", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("=== INFERENCE CLOSED ===")

if __name__ == "__main__":
    main()