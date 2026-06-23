import os
import shutil
import subprocess

def clean_workspace():
    """Wipes generated data folders but protects raw_videos."""
    print("[*] Cleaning workspace...")
    directories_to_reset = [
        "data/extracted_frames",
        "data/labels",
        "data/visual_proof",
        "data/dataset"
    ]
    
    for directory in directories_to_reset:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory, exist_ok=True)
        print(f"    -> Reset: {directory}")

def run_script(script_path):
    """Executes a python script and halts if it fails."""
    print(f"\n========================================")
    print(f"[*] EXECUTING: {script_path}")
    print(f"========================================\n")
    
    result = subprocess.run(["python", script_path])
    
    if result.returncode != 0:
        print(f"\n[!] ERROR: {script_path} failed. Pipeline halted.")
        exit(1)

def main():
    print("=== STARTING AUTONOMOUS DATA ENGINE ===")
    
    # 1. Prepare Environment
    clean_workspace()
    
    # 2. Execute Pipeline Sequence
    run_script("scripts/extract_frames.py")
    run_script("scripts/auto_annotate_v2.py")
    run_script("scripts/prepare_dataset.py")
    
    # 3. Train Model
    # Note: Ensure train.py has exist_ok=True and a static name like name="multi_class_v1"
    run_script("scripts/train.py")
    
    print("\n=== PIPELINE COMPLETE! ===")
    print("Check data/visual_proof/ to see teacher annotations.")
    print("Weights saved in runs/detect/")

if __name__ == "__main__":
    main()