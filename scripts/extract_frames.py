import os, cv2, glob
from tqdm import tqdm

def main():
    workspace = os.environ.get("PIPELINE_WORKSPACE", "data")
    video_dir = os.path.join(workspace, "raw_videos")
    output_dir = os.path.join(workspace, "extracted_frames")

    video_files = glob.glob(os.path.join(video_dir, "*.*"))
    if not video_files:
        print("[!] No video found.")
        exit(1)
        
    cap = cv2.VideoCapture(video_files[0])
    frame_interval = 10
    count = 0
    saved = 0
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        if count % frame_interval == 0:
            cv2.imwrite(os.path.join(output_dir, f"frame_{saved:04d}.jpg"), frame)
            saved += 1
        count += 1
    cap.release()
    print(f"Extracted {saved} frames.")

if __name__ == "__main__":
    main()