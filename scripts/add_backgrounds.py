import cv2
import os

def main():
    save_dir = "data/dataset/train/images"
    os.makedirs(save_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(0)
    print("Webcam active. Point camera at your background (NO BOTTLE IN FRAME).")
    print("Press SPACEBAR to snap a background photo.")
    print("Press 'q' when you have taken 5 to 10 photos.")
    
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        cv2.imshow("Snap Backgrounds (Press Space)", frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == 32: # Spacebar
            img_name = f"bg_negative_{count}.jpg"
            img_path = os.path.join(save_dir, img_name)
            cv2.imwrite(img_path, frame)
            print(f"Saved negative sample: {img_name}")
            count += 1
            
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"Done! Injected {count} background images into the training set.")

if __name__ == "__main__":
    main()