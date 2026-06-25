import os
import json
import time
import subprocess
import glob
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import cv2
import time
from ultralytics import YOLO
from fastapi.responses import StreamingResponse
import asyncio


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

# Active inference streams keyed by stream_id. STOP sets this False and the generator exits.
active_streams = {}

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

@app.get("/api/runs")
async def get_runs():
    runs_dir = os.path.join("data", "runs")
    if not os.path.exists(runs_dir):
        return {"runs": []}
    
    run_list = []
    for run_id in os.listdir(runs_dir):
        run_path = os.path.join(runs_dir, run_id)
        if os.path.isdir(run_path):
            # 1. Fetch the target tags
            tags = []
            targets_file = os.path.join(run_path, "current_targets.json")
            if os.path.exists(targets_file):
                with open(targets_file, "r") as f:
                    tags = json.load(f)
            
            # 2. Get the creation datetime
            timestamp = os.path.getctime(run_path)
            dt = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            
            # 3. Check if weights actually exist for this run
            has_weights = os.path.exists(os.path.join(run_path, "train_results", "weights", "best.pt"))
            
            run_list.append({
                "id": run_id,
                "tags": tags,
                "datetime": dt,
                "has_weights": has_weights
            })
    
    # Sort with newest runs at the top
    run_list.sort(key=lambda x: x["datetime"], reverse=True)
    return {"runs": run_list} 

# --- NEW: External Model Upload ---
@app.post("/api/upload_external")
async def upload_external(file: UploadFile = File(...)):
    os.makedirs("data/external_models", exist_ok=True)
    file_path = os.path.join("data/external_models", file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    # Return a special ID so our streamer knows where to look
    return {"status": "success", "id": f"EXT_{file.filename}"}

# --- NEW: The Live AI Video Streamer ---
def _open_video_capture(src):
    # Try several backends (prefer DirectShow on Windows) to improve device detection
    backends = []
    try:
        # cv2.CAP_DSHOW is best on many Windows machines
        backends.append(cv2.CAP_DSHOW)
    except Exception:
        pass
    try:
        backends.append(cv2.CAP_MSMF)
    except Exception:
        pass
    backends.append(0)  # default backend/CAP_ANY

    for b in backends:
        try:
            cap = cv2.VideoCapture(src, b) if b != 0 else cv2.VideoCapture(src)
            if cap is not None and cap.isOpened():
                print(f"[i] Opened camera src={src} with backend={b}")
                return cap
            else:
                try:
                    cap.release()
                except Exception:
                    pass
        except Exception as e:
            print(f"[!] VideoCapture attempt with backend={b} failed: {e}")
    # Final fallback: try without backend param
    try:
        cap = cv2.VideoCapture(src)
        if cap is not None and cap.isOpened():
            print(f"[i] Opened camera src={src} with default backend (fallback)")
            return cap
    except Exception:
        pass
    return None


async def generate_annotated_frames(model_path, camera_source, request: Request, stream_id: str):
    # Parse the camera source (0, 1, etc.)
    src = int(camera_source) if str(camera_source).isdigit() else camera_source

    # Attempt to open the camera using multiple backends to avoid "index out of range"
    cap = _open_video_capture(src)
    if cap is None or not cap.isOpened():
        print(f"[!] Failed to open camera src={src}.")
        return

    # Give the camera a brief moment to wake up (prevents initial blank frames)
    await asyncio.sleep(1.0)
    
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return
    try:
        # Print model class names for debugging (helps detect class/index mismatches)
        if hasattr(model, 'model') and hasattr(model.model, 'names'):
            print(f"[i] Loaded model classes: {model.model.names}")
        elif hasattr(model, 'names'):
            print(f"[i] Loaded model classes: {model.names}")
    except Exception:
        pass

    # Diagnostic logging controls
    last_log = time.time()
    frame_count = 0

    try:
        while True:
            # Stop if client disconnected or if frontend asked STOP
            try:
                if await request.is_disconnected():
                    print("[i] Client disconnected, stopping stream and releasing camera.")
                    break
            except Exception:
                pass

            if stream_id and not active_streams.get(stream_id, False):
                print(f"[i] Stream {stream_id} was stopped by client.")
                break
            start_time = time.time()
            success, frame = cap.read()

            if not success:
                print("[!] Camera dropped a frame or disconnected.")
                break

            # Safely resize the frame AFTER capturing it (software resize is crash-proof)
            frame = cv2.resize(frame, (640, 480))

            # Run YOLO inference with a lower confidence threshold to improve recall
            results = model(frame, conf=0.07, verbose=False)
            annotated_frame = results[0].plot()

            # Diagnostic: inspect predictions and confidence values
            frame_count += 1
            num_boxes = 0
            det_details = []
            try:
                if hasattr(results[0], 'boxes') and results[0].boxes is not None:
                    try:
                        xy = results[0].boxes.xyxy
                        cls = results[0].boxes.cls if hasattr(results[0].boxes, 'cls') else None
                        confs = results[0].boxes.conf if hasattr(results[0].boxes, 'conf') else None
                        num_boxes = len(xy)
                        for i in range(num_boxes):
                            c = int(cls[i]) if cls is not None else None
                            conf = float(confs[i]) if confs is not None else None
                            det_details.append({'class': c, 'conf': conf})
                    except Exception:
                        try:
                            data = results[0].boxes.data
                            for row in data:
                                arr = row.tolist()
                                if len(arr) >= 6:
                                    conf = float(arr[4]); c = int(arr[5])
                                elif len(arr) >= 5:
                                    conf = float(arr[4]); c = None
                                else:
                                    conf = None; c = None
                                det_details.append({'class': c, 'conf': conf})
                            num_boxes = len(det_details)
                        except Exception:
                            pass
            except Exception as e:
                print(f"[i] Inference parse error: {e}")

            if num_boxes > 0:
                print(f"[i] Inference frame {frame_count}: detections={num_boxes} details={det_details[:5]}")
                try:
                    os.makedirs('data/debug', exist_ok=True)
                    ts = int(time.time() * 1000)
                    cv2.imwrite(f"data/debug/frame_{ts}.jpg", annotated_frame)
                    with open(f"data/debug/frame_{ts}.json", 'w') as jf:
                        json.dump(det_details, jf)
                except Exception as e:
                    print(f"[i] Debug save error: {e}")
            else:
                if time.time() - last_log > 3.0:
                    print(f"[i] Inference frame {frame_count}: detections=0")
                    last_log = time.time()

            # Calculate and draw FPS
            fps = 1.0 / max((time.time() - start_time), 0.001) # Max prevents division by zero
            cv2.putText(annotated_frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            # Yield the stream back to the React frontend
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        try:
            cap.release()
            print("[i] Camera released")
        except Exception:
            pass

@app.post("/api/stop_inference")
async def stop_inference(stream_id: str = Form(...)):
    if stream_id in active_streams:
        active_streams[stream_id] = False
        return {"status": "stopped"}
    return {"status": "unknown_stream"}


@app.get("/api/inference_stream")
def inference_stream(request: Request, model_id: str, camera: str = "0", stream_id: str = ""):
    if not stream_id:
        return {"error": "stream_id is required"}

    # Locate the model based on the ID prefix
    if model_id.startswith("EXT_"):
        filename = model_id.replace("EXT_", "")
        model_path = f"data/external_models/{filename}"
    else:
        model_path = f"data/runs/{model_id}/train_results/weights/best.pt"

    if not os.path.exists(model_path):
        return {"error": "Model weights not found."}

    active_streams[stream_id] = True
    return StreamingResponse(generate_annotated_frames(model_path, camera, request, stream_id), media_type="multipart/x-mixed-replace; boundary=frame")       