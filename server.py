import os
import json
import time
import subprocess
import glob
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the runs directory exists so mounting doesn't crash on startup
os.makedirs("data/runs", exist_ok=True)
# Mount the runs directory so React can load the saved images via URL
app.mount("/runs", StaticFiles(directory="data/runs"), name="runs")

def run_pipeline_task(workspace: str):
    """This runs completely in the background"""
    env = os.environ.copy()
    env["PIPELINE_WORKSPACE"] = workspace
    subprocess.run(["python", "run_training_pipeline.py"], env=env)

@app.post("/api/compile")
async def compile_model(background_tasks: BackgroundTasks, file: UploadFile = File(...), tags: str = Form(...)):
    run_id = f"run_{int(time.time())}"
    workspace = f"data/runs/{run_id}"
    
    os.makedirs(f"{workspace}/raw_videos", exist_ok=True)
    
    video_path = os.path.join(workspace, "raw_videos", file.filename)
    with open(video_path, "wb") as buffer:
        buffer.write(await file.read())

    target_list = json.loads(tags)
    with open(os.path.join(workspace, "current_targets.json"), "w") as f:
        json.dump(target_list, f)

    # Initialize the live tracker file
    with open(os.path.join(workspace, "status.txt"), "w") as f:
        f.write("INITIALIZING PIPELINE...")

    # Kick off the heavy Python scripts in the background
    background_tasks.add_task(run_pipeline_task, workspace)

    # Immediately give the frontend the run_id so it can start tracking progress
    return {"status": "success", "run_id": run_id}

@app.get("/api/status/{run_id}")
async def get_status(run_id: str):
    status_file = f"data/runs/{run_id}/status.txt"
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            return {"status": f.read().strip()}
    return {"status": "UNKNOWN ERROR"}

@app.get("/api/proofs/{run_id}")
async def get_proofs(run_id: str):
    proof_dir = os.path.join("data", "runs", run_id, "visual_proof")
    if not os.path.exists(proof_dir):
        return {"images": []}
    
    images = []
    # os.listdir safely ignores Windows backslash URL issues
    for filename in os.listdir(proof_dir):
        if filename.lower().endswith((".jpg", ".png")):
            # Construct the clean URL for React
            images.append(f"http://localhost:8000/runs/{run_id}/visual_proof/{filename}")
            
    return {"images": images}

@app.get("/api/download/{run_id}")
async def download_weights(run_id: str):
    weights_path = f"data/runs/{run_id}/train_results/weights/best.pt"
    if os.path.exists(weights_path):
        return FileResponse(weights_path, filename=f"{run_id}_best.pt")
    return {"error": "Weights not found."}