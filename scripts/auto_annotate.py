import os
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
from tqdm import tqdm

def main():
    # Configuration
    IMAGE_DIR = "data/extracted_frames"
    LABEL_DIR = "data/labels"
    # Grounding DINO works best when prompts end with a period
    PROMPT = "steel water bottle." 
    CONFIDENCE_THRESHOLD = 0.35

    # Ensure output directory exists
    os.makedirs(LABEL_DIR, exist_ok=True)

    # Check for GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Grounding DINO on: {device.upper()}...")

    # Load Model and Processor from Hugging Face
    model_id = "IDEA-Research/grounding-dino-base"
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device)
    print("Model loaded successfully!\n")

    # Get all images
    valid_extensions = (".jpg", ".jpeg", ".png")
    image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(valid_extensions)]

    print(f"Starting auto-annotation for {len(image_files)} images...")
    
    for img_name in tqdm(image_files, desc="Annotating"):
        img_path = os.path.join(IMAGE_DIR, img_name)
        image = Image.open(img_path).convert("RGB")
        img_width, img_height = image.size

        # Process the image and text prompt
        inputs = processor(images=image, text=PROMPT, return_tensors="pt").to(device)
        
        # Run inference (no gradient calculation needed)
        with torch.no_grad():
            outputs = model(**inputs)

        # Post-process results
        results = processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            threshold=CONFIDENCE_THRESHOLD, # Replaced box and text thresholds
            target_sizes=[image.size[::-1]]
        )[0]

        # Prepare YOLO format text file
        label_name = os.path.splitext(img_name)[0] + ".txt"
        label_path = os.path.join(LABEL_DIR, label_name)

        with open(label_path, "w") as f:
            for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                # Grounding DINO outputs [xmin, ymin, xmax, ymax]
                xmin, ymin, xmax, ymax = box.tolist()

                # Convert to YOLO format (normalized center_x, center_y, width, height)
                x_center = ((xmin + xmax) / 2) / img_width
                y_center = ((ymin + ymax) / 2) / img_height
                box_width = (xmax - xmin) / img_width
                box_height = (ymax - ymin) / img_height

                # Ensure values are within 0 and 1
                x_center = max(0, min(1, x_center))
                y_center = max(0, min(1, y_center))
                box_width = max(0, min(1, box_width))
                box_height = max(0, min(1, box_height))

                # Write to file (Class ID 0 for the bottle)
                f.write(f"0 {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}\n")

    print(f"\nFinished! YOLO annotations saved to {LABEL_DIR}")

if __name__ == "__main__":
    main()