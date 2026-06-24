import os
import subprocess

def update_status(workspace, message):
    """Writes the current stage to a text file for the API to read."""
    status_path = os.path.join(workspace, "status.txt")
    with open(status_path, "w") as f:
        f.write(message)

def run_script(script_path):
    print(f"\n[*] EXECUTING: {script_path}")
    result = subprocess.run(["python", script_path])
    if result.returncode != 0:
        exit(1)

def main():
    workspace = os.environ.get("PIPELINE_WORKSPACE")
    if not workspace:
        print("[!] ERROR: PIPELINE_WORKSPACE environment variable not set.")
        exit(1)

    print(f"=== STARTING AUTONOMOUS DATA ENGINE: {workspace} ===")
    
    os.makedirs(f"{workspace}/extracted_frames", exist_ok=True)
    os.makedirs(f"{workspace}/labels", exist_ok=True)
    os.makedirs(f"{workspace}/visual_proof", exist_ok=True)
    os.makedirs(f"{workspace}/dataset", exist_ok=True)
    
    update_status(workspace, "EXTRACTING FRAMES...")
    run_script("scripts/extract_frames.py")
    
    update_status(workspace, "AUTO-ANNOTATING VIA FOUNDATION MODEL...")
    run_script("scripts/auto_annotate_v2.py")
    
    update_status(workspace, "PREPARING YOLO DATASET STRUCTURE...")
    run_script("scripts/prepare_dataset.py")
    
    update_status(workspace, "TRAINING STUDENT MODEL (GPU ACTIVE)...")
    run_script("scripts/train.py")
    
    # The magical word that tells the React frontend to move to Stage 4
    update_status(workspace, "COMPLETE")
    print("\n=== PIPELINE COMPLETE! ===")

if __name__ == "__main__":
    main()