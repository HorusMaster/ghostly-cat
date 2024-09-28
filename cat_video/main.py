import torch
from pathlib import Path

# Model
model = torch.hub.load("ultralytics/yolov5", "custom", path="models/best.pt", force_reload=True)
# Images
img = "https://ultralytics.com/images/zidane.jpg"  # or file, Path, PIL, OpenCV, numpy, list

# Inference
results = model(img)

# Results
results.print()  # or .show(), .save(), .crop(), .pandas(), etc.