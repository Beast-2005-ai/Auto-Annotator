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

os.makedirs("data/runs", exist_ok=True)
app.mount("/runs", StaticFiles(directory="data/runs"), name="runs")

# Live inference confidence threshold used for webcam detection
# Lowered further because the bottle model may produce weak-confidence detections.
LIVE_CONF_THRESHOLD = 0.05

active_streams = {}
LOG_FILE = "data/system.log"

# --- NEW: System Logging Engine ---
def log_event(message: str):
    """Writes a clean timestamped log to the system log file."""
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    # Prevent repeated identical logs
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            if lines and message in lines[-1]:
                return  

    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    print(log_entry.strip())

@app.get("/api/logs")
def get_logs():
    if not os.path.exists(LOG_FILE):
        return {"logs": []}
    with open(LOG_FILE, "r") as f:
        return {"logs": f.readlines()[-100:]}

@app.post("/api/logs/clear")
def clear_logs():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    log_event("SYSTEM LOGS CLEARED.")
    return {"status": "success"}


# --- Phase argument added to pipeline task ---
def run_pipeline_task(workspace: str, phase: str = "1"):
    env = os.environ.copy()
    env["PIPELINE_WORKSPACE"] = workspace
    env["PIPELINE_PHASE"] = phase 
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

    with open(os.path.join(workspace, "status.txt"), "w") as f:
        f.write("INITIALIZING PIPELINE...")

    log_event(f"STARTED PHASE 1 (EXTRACTION): Session {run_id} loaded tape '{file.filename}'.")
    background_tasks.add_task(run_pipeline_task, workspace, "1")
    return {"status": "success", "run_id": run_id}

@app.post("/api/continue_pipeline")
async def continue_pipeline(background_tasks: BackgroundTasks, run_id: str = Form(...)):
    workspace = f"data/runs/{run_id}"
    with open(os.path.join(workspace, "status.txt"), "w") as f:
        f.write("RESUMING PIPELINE...")
        
    log_event(f"STARTED PHASE 2 (TRAINING): Session {run_id} resuming after manual curation.")
    background_tasks.add_task(run_pipeline_task, workspace, "2")
    return {"status": "success"}

@app.delete("/api/discard/{run_id}/{filename}")
async def discard_frame(run_id: str, filename: str):
    workspace = f"data/runs/{run_id}"
    base_name = os.path.splitext(filename)[0]

    paths_to_delete = [
        os.path.join(workspace, "extracted_frames", filename),
        os.path.join(workspace, "visual_proof", filename),
        os.path.join(workspace, "labels", base_name + ".txt")
    ]
    
    for p in paths_to_delete:
        if os.path.exists(p):
            os.remove(p)
            
    log_event(f"CURATION: Discarded frame {filename} from {run_id}.")
    return {"status": "deleted"}

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
    for filename in os.listdir(proof_dir):
        if filename.lower().endswith((".jpg", ".png")):
            images.append(f"http://localhost:8000/runs/{run_id}/visual_proof/{filename}")
            
    return {"images": images}

@app.get("/api/download/{run_id}")
async def download_weights(run_id: str):
    weights_path = f"data/runs/{run_id}/train_results/weights/best.pt"
    if os.path.exists(weights_path):
        log_event(f"DOWNLOAD: User downloaded weights for {run_id}.")
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
            tags = []
            targets_file = os.path.join(run_path, "current_targets.json")
            if os.path.exists(targets_file):
                with open(targets_file, "r") as f:
                    tags = json.load(f)
            
            timestamp = os.path.getctime(run_path)
            dt = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            has_weights = os.path.exists(os.path.join(run_path, "train_results", "weights", "best.pt"))
            
            run_list.append({
                "id": run_id,
                "tags": tags,
                "datetime": dt,
                "has_weights": has_weights
            })
    run_list.sort(key=lambda x: x["datetime"], reverse=True)
    return {"runs": run_list} 

@app.post("/api/upload_external")
async def upload_external(file: UploadFile = File(...)):
    os.makedirs("data/external_models", exist_ok=True)
    file_path = os.path.join("data/external_models", file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    log_event(f"EXTERNAL UPLOAD: Loaded external weights '{file.filename}'.")
    return {"status": "success", "id": f"EXT_{file.filename}"}

# --- The Live AI Video Streamer ---
def _open_video_capture(src):
    backends = []
    try: backends.append(cv2.CAP_DSHOW)
    except Exception: pass
    try: backends.append(cv2.CAP_MSMF)
    except Exception: pass
    backends.append(0)

    for b in backends:
        try:
            cap = cv2.VideoCapture(src, b) if b != 0 else cv2.VideoCapture(src)
            if cap is not None and cap.isOpened():
                print(f"[i] Opened camera src={src} with backend={b}")
                return cap
            else:
                try: cap.release()
                except Exception: pass
        except Exception as e:
            print(f"[!] VideoCapture attempt with backend={b} failed: {e}")
            
    try:
        cap = cv2.VideoCapture(src)
        if cap is not None and cap.isOpened():
            print(f"[i] Opened camera src={src} with default backend (fallback)")
            return cap
    except Exception: pass
    return None

async def generate_annotated_frames(model_path, camera_source, request: Request, stream_id: str):
    src = int(camera_source) if str(camera_source).isdigit() else camera_source
    cap = _open_video_capture(src)
    
    if cap is None or not cap.isOpened():
        print(f"[!] Failed to open camera src={src}.")
        return

    await asyncio.sleep(1.0)
    
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return
        
    try:
        if hasattr(model, 'model') and hasattr(model.model, 'names'):
            print(f"[i] Loaded model classes: {model.model.names}")
        elif hasattr(model, 'names'):
            print(f"[i] Loaded model classes: {model.names}")
    except Exception: pass

    log_event(f"INFERENCE: Stream {stream_id} started on camera {src}.")
    
    last_log = time.time()
    frame_count = 0

    try:
        while True:
            try:
                if await request.is_disconnected():
                    print("[i] Client disconnected, stopping stream and releasing camera.")
                    break
            except Exception: pass

            if stream_id and not active_streams.get(stream_id, False):
                print(f"[i] Stream {stream_id} was stopped by client.")
                break
                
            start_time = time.time()
            success, frame = cap.read()

            if not success:
                print("[!] Camera dropped a frame or disconnected.")
                break

            frame = cv2.resize(frame, (640, 480))

            # --- RESTORED: Your original diagnostic logic ---
            results = model(frame, conf=LIVE_CONF_THRESHOLD, verbose=False)
            frame_count += 1
            num_boxes = 0
            det_details = []

            if hasattr(results[0], 'boxes') and results[0].boxes is not None:
                try:
                    print(f"[DEBUG] raw boxes data: {results[0].boxes}")
                except Exception:
                    pass

            annotated_frame = results[0].plot()
            parsed_boxes = []
            
            try:
                if hasattr(results[0], 'boxes') and results[0].boxes is not None:
                    try:
                        xy = results[0].boxes.xyxy
                        cls = results[0].boxes.cls if hasattr(results[0].boxes, 'cls') else None
                        confs = results[0].boxes.conf if hasattr(results[0].boxes, 'conf') else None
                        num_boxes = len(xy)
                        print(f"[DEBUG] xyxy count={num_boxes}")
                        for i in range(num_boxes):
                            c = int(cls[i]) if cls is not None else None
                            conf = float(confs[i]) if confs is not None else None
                            det_details.append({'class': c, 'conf': conf})
                            parsed_boxes.append((xy[i][0], xy[i][1], xy[i][2], xy[i][3], conf, c))
                    except Exception:
                        try:
                            data = results[0].boxes.data
                            if hasattr(data, 'cpu'):
                                data = data.cpu()
                            raw = data.numpy() if hasattr(data, 'numpy') else data
                            print(f"[DEBUG] boxes.data shape={getattr(raw, 'shape', 'unknown')}")
                            for row in raw:
                                arr = row.tolist()
                                if len(arr) >= 6:
                                    conf = float(arr[4]); c = int(arr[5])
                                elif len(arr) >= 5:
                                    conf = float(arr[4]); c = None
                                else:
                                    conf = None; c = None
                                det_details.append({'class': c, 'conf': conf})
                                parsed_boxes.append((arr[0], arr[1], arr[2], arr[3], conf, c))
                            num_boxes = len(det_details)
                        except Exception as e:
                            print(f"[DEBUG] raw box parse failed: {e}")
            except Exception as e:
                print(f"[i] Inference parse error: {e}")

            if parsed_boxes:
                try:
                    for x1, y1, x2, y2, conf, cls_id in parsed_boxes:
                        cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)
                        label = f"{cls_id if cls_id is not None else 'obj'} {conf:.2f}"
                        cv2.putText(annotated_frame, label, (int(x1), max(int(y1) - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                except Exception as e:
                    print(f"[DEBUG] manual box overlay failed: {e}")

            if num_boxes > 0:
                print(f"[i] Inference frame {frame_count}: detections={num_boxes} details={det_details[:5]}")
                try:
                    os.makedirs('data/debug', exist_ok=True)
                    ts = int(time.time() * 1000)
                    cv2.imwrite(f"data/debug/frame_{ts}.jpg", annotated_frame)
                    with open(f"data/debug/frame_{ts}.json", 'w') as jf:
                        json.dump({
                            'frame': frame_count,
                            'class_ids': [d['class'] for d in det_details],
                            'confs': [d['conf'] for d in det_details],
                            'raw_boxes': [row.tolist() for row in results[0].boxes.data] if hasattr(results[0].boxes, 'data') else []
                        }, jf)
                except Exception as e:
                    print(f"[i] Debug save error: {e}")
            else:
                if time.time() - last_log > 3.0:
                    print(f"[i] Inference frame {frame_count}: detections=0")
                    last_log = time.time()

            # FPS Tracker
            fps = 1.0 / max((time.time() - start_time), 0.001) 
            cv2.putText(annotated_frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            ret, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret: continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    finally:
        try: cap.release()
        except Exception: pass

@app.post("/api/stop_inference")
async def stop_inference(stream_id: str = Form(...)):
    if stream_id in active_streams:
        active_streams[stream_id] = False
        log_event(f"INFERENCE: Stream {stream_id} stopped manually.")
        return {"status": "stopped"}
    return {"status": "unknown_stream"}

@app.get("/api/inference_stream")
def inference_stream(request: Request, model_id: str, camera: str = "0", stream_id: str = ""):
    if not stream_id: return {"error": "stream_id is required"}

    if model_id.startswith("EXT_"):
        filename = model_id.replace("EXT_", "")
        model_path = f"data/external_models/{filename}"
    else:
        model_path = f"data/runs/{model_id}/train_results/weights/best.pt"

    if not os.path.exists(model_path): return {"error": "Model weights not found."}

    active_streams[stream_id] = True
    return StreamingResponse(generate_annotated_frames(model_path, camera, request, stream_id), media_type="multipart/x-mixed-replace; boundary=frame")