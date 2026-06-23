import cv2
import torch
from ultralytics import YOLO

def main():
    # 1. Path to your custom trained weights
    # Ultralytics automatically increments folders if you run multiple times (e.g., steel_bottle_proto2)
    # Check your 'runs/detect/' directory to ensure this path matches perfectly.
    WEIGHTS_PATH = "runs/detect/steel_bottle_proto/weights/best.pt"
    
    if not os.path.exists(WEIGHTS_PATH):
        # Fallback search if path differs slightly
        print(f"Looking for weights at default path...")
        WEIGHTS_PATH = "runs/detect/train/weights/best.pt"

    # 2. Check for CUDA
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Loading custom model onto: {torch.cuda.get_device_name(0) if device == 0 else 'CPU'}")

    # 3. Load the model
    model = YOLO(WEIGHTS_PATH).to(device)
    print("Model loaded successfully! Starting webcam feed...")

    # 4. Initialize Webcam (0 is usually the default built-in camera)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Set window to be resizable
    cv2.namedWindow("Steel Bottle Prototype Detection", cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        # Run inference on the current frame
        # We set stream=True for efficient memory management during live video processing
        results = model(frame, stream=True, device=device, conf=0.35)

        # Plot the bounding boxes and labels onto the frame
        for r in results:
            annotated_frame = r.plot()

        # Display the frame
        cv2.imshow("Steel Bottle Prototype Detection", annotated_frame)

        # Break the loop if 'q' key is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up assets safely
    cap.release()
    cv2.destroyAllWindows()
    print("Webcam feed closed.")

if __name__ == "__main__":
    import os
    main()