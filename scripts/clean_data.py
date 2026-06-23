import cv2
import os

def main():
    img_dir = "data/dataset/train/images"
    lbl_dir = "data/dataset/train/labels"
    
    images = [f for f in os.listdir(img_dir) if f.endswith(('.jpg', '.png'))]
    print("Press 'd' to DELETE a bad label (like if it's on your face).")
    print("Press ANY OTHER KEY to keep the label and move to the next image.")
    print("Press 'q' to quit early.\n")

    for img_name in images:
        img_path = os.path.join(img_dir, img_name)
        lbl_path = os.path.join(lbl_dir, os.path.splitext(img_name)[0] + ".txt")
        
        if not os.path.exists(lbl_path):
            continue # Skip images that already have no labels
            
        img = cv2.imread(img_path)
        h, w, _ = img.shape
        
        # Read the YOLO label
        with open(lbl_path, "r") as f:
            lines = f.readlines()
            
        # Draw all boxes in the file
        for line in lines:
            parts = line.strip().split()
            if len(parts) == 5:
                cx, cy, bw, bh = map(float, parts[1:])
                x1 = int((cx - bw/2) * w)
                y1 = int((cy - bh/2) * h)
                x2 = int((cx + bw/2) * w)
                y2 = int((cy + bh/2) * h)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                
        cv2.imshow("Data Cleaner", img)
        key = cv2.waitKey(0) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('d'):
            os.remove(lbl_path) # Deletes the poisoned text file!
            print(f"Deleted label for: {img_name}")

    cv2.destroyAllWindows()
    print("Dataset cleaned!")

if __name__ == "__main__":
    main()