import os, json, torch, cv2
from PIL import Image
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
from tqdm import tqdm

def generate_yaml(workspace, classes):
    yaml_path = os.path.join(workspace, "dataset.yaml")
    train_path = os.path.abspath(os.path.join(workspace, "dataset", "train", "images"))
    val_path = os.path.abspath(os.path.join(workspace, "dataset", "val", "images"))
    
    names_dict = {i: name.replace(" ", "_") for i, name in enumerate(classes)}
    
    yaml_content = f"path: {workspace}\ntrain: {train_path}\nval: {val_path}\n\nnames:\n"
    for k, v in names_dict.items(): yaml_content += f"  {k}: {v}\n"
        
    with open(yaml_path, "w") as f: f.write(yaml_content)
    return names_dict

def main():
    workspace = os.environ.get("PIPELINE_WORKSPACE", "data")
    
    try:
        with open(os.path.join(workspace, "current_targets.json"), "r") as f:
            TARGET_CLASSES = json.load(f)
    except FileNotFoundError:
        TARGET_CLASSES = ["object"]

    IMAGE_DIR = os.path.join(workspace, "extracted_frames")
    LABEL_DIR = os.path.join(workspace, "labels")
    PROOF_DIR = os.path.join(workspace, "visual_proof")
    
    class_map = generate_yaml(workspace, TARGET_CLASSES)
    dino_prompt = " . ".join(TARGET_CLASSES) + " ." 
    
    os.makedirs(LABEL_DIR, exist_ok=True)
    os.makedirs(PROOF_DIR, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_id = "IDEA-Research/grounding-dino-base"
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device)

    image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".png"))]
    
    annotated_count = 0
    total_count = len(image_files)

    for img_name in tqdm(image_files, desc="Auto-Annotating"):
        img_path = os.path.join(IMAGE_DIR, img_name)
        pil_image = Image.open(img_path).convert("RGB")
        cv2_image = cv2.imread(img_path)
        img_width, img_height = pil_image.size

        inputs = processor(images=pil_image, text=dino_prompt, return_tensors="pt").to(device)
        with torch.no_grad(): outputs = model(**inputs)

        results = processor.post_process_grounded_object_detection(
            outputs, inputs.input_ids, threshold=0.20, target_sizes=[pil_image.size[::-1]]
        )[0]

        labels = []
        for score, label_str, box in zip(results["scores"], results["text_labels"], results["boxes"]):
            class_id = -1
            for idx, target in enumerate(TARGET_CLASSES):
                if target.lower() in label_str.lower():
                    class_id = idx
                    break
            if class_id == -1:
                continue

            xmin, ymin, xmax, ymax = box.tolist()
            labels.append((class_id, xmin, ymin, xmax, ymax, float(score)))

        if labels:
            annotated_count += 1
            label_path = os.path.join(LABEL_DIR, os.path.splitext(img_name)[0] + ".txt")
            with open(label_path, "w") as f:
                for class_id, xmin, ymin, xmax, ymax, score in labels:
                    f.write(f"{class_id} {max(0, min(1, ((xmin + xmax) / 2) / img_width)):.6f} {max(0, min(1, ((ymin + ymax) / 2) / img_height)):.6f} {max(0, min(1, (xmax - xmin) / img_width)):.6f} {max(0, min(1, (ymax - ymin) / img_height)):.6f}\n")

                    color = (0, 255, 0)
                    cv2.rectangle(cv2_image, (int(xmin), int(ymin)), (int(xmax), int(ymax)), color, 2)
                    cv2.putText(cv2_image, f"{class_map[class_id]} {score:.2f}", (int(xmin), int(ymin)-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            cv2.imwrite(os.path.join(PROOF_DIR, img_name), cv2_image)

    print(f"Auto-annotation complete: {annotated_count}/{total_count} images labeled.")

if __name__ == "__main__":
    main()