import cv2
import os
from tqdm import tqdm

def extract_frames(video_path, output_dir, frame_interval=10):
    """
    Extracts frames from a video at a specified interval.
    
    Args:
        video_path (str): Path to the input video file.
        output_dir (str): Directory where images will be saved.
        frame_interval (int): Extract every N-th frame (e.g., 10 means 3 frames per second for a 30fps video).
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return
    
    total_frames = int(cap.get(cv2.getBuildInformation().find("FRAME_COUNT") if cap.get(7) == 0 else cap.get(7)))
    # Fallback if frame count detection fails
    if total_frames <= 0:
        total_frames = None

    print(f"Processing video: {os.path.basename(video_path)}")
    
    frame_count = 0
    saved_count = 0
    
    # Progress bar visualization
    pbar = tqdm(total=total_frames, desc="Extracting Frames")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Only save every N-th frame
        if frame_count % frame_interval == 0:
            # Pad file name with zeros for easy alphabetical sorting (e.g., frame_0001.jpg)
            filename = f"frame_{saved_count:04d}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            # Save frame as JPEG
            cv2.imwrite(filepath, frame)
            saved_count += 1
            
        frame_count += 1
        pbar.update(1)
        
    cap.release()
    pbar.close()
    print(f"\nSuccessfully extracted {saved_count} frames to: {output_dir}")

if __name__ == "__main__":
    # Example paths - update these based on your filenames
    VIDEO_FILE = "data/raw_videos/bottle_video.mp4"
    OUTPUT_FOLDER = "data/extracted_frames/"
    
    # Extract 1 frame every 10 frames (ideal balance for a panning phone video)
    extract_frames(VIDEO_FILE, OUTPUT_FOLDER, frame_interval=10)