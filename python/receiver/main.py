import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2
import time
from PIL import Image
from torchvision import transforms
import matplotlib.pyplot as plt

# Simple depth estimation model using MiDaS (which works out of the box)
def load_model():
    # Use MiDaS small model which is more reliable
    model = torch.hub.load("intel-isl/MiDaS", "DPT_Hybrid")

    # Switch to eval mode
    model.eval()

    # Move to GPU if available
    if torch.cuda.is_available():
        model = model.cuda()

    return model

def process_image(img, size=(256, 256)):
    # OpenCV uses BGR color ordering, need to convert to RGB for the model
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Resize to model input size
    img_resized = cv2.resize(img_rgb, size, interpolation=cv2.INTER_LINEAR)

    # Convert to tensor and normalize
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    img_tensor = transform(Image.fromarray(img_resized)).unsqueeze(0)
    return img_tensor, img  # Return original BGR image for display

def get_depth_map(model, image_tensor):
    with torch.no_grad():
        if torch.cuda.is_available():
            image_tensor = image_tensor.cuda()

        # Forward pass
        prediction = model(image_tensor)

        # Normalize output
        output = prediction.cpu().numpy().squeeze()

        return output

def colorize_depth(depth, cmap=plt.cm.viridis):
    # Normalize depth to 0-1 range
    normalized_depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)

    # Apply colormap
    colored_depth = (cmap(normalized_depth) * 255).astype(np.uint8)[:, :, :3]
    return colored_depth

def main():
    # Load model
    try:
        print("Loading MiDaS model...")
        model = load_model()
        print("Model loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # Open webcam
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam")
        return

    print("Starting webcam depth prediction. Press 'q' to quit.")

    while True:
        # Read frame
        ret, frame = cap.read()

        if not ret:
            print("Error: Failed to capture image")
            break

        try:
            # Process frame
            start_time = time.time()
            image_tensor, original_frame = process_image(frame)

            # Get depth prediction
            depth_map = get_depth_map(model, image_tensor)

            # Colorize depth map
            colored_depth = colorize_depth(depth_map)

            # Resize colored depth to match original frame
            h, w = original_frame.shape[:2]
            colored_depth_resized = cv2.resize(colored_depth, (w, h))

            # Convert depth from RGB to BGR for display with OpenCV
            colored_depth_bgr = cv2.cvtColor(colored_depth_resized, cv2.COLOR_RGB2BGR)

            # Show fps
            fps = 1.0 / (time.time() - start_time)
            cv2.putText(original_frame, f"FPS: {fps:.2f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Display original and depth (both in BGR format for OpenCV)
            display_img = np.hstack((original_frame, colored_depth_bgr))
            cv2.imshow('MiDaS Depth Estimation (Original | Depth)', display_img)
        except Exception as e:
            print(f"Error processing frame: {e}")

        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
