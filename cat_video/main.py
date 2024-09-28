import torch

model = torch.hub.load("/code/yolov5", "custom", "models/yolov5n-face.pt", source='local', force_reload=True)

img = "https://ultralytics.com/images/zidane.jpg"  # or file, Path, PIL, OpenCV, numpy, list

# Inference
results = model(img)

# Results
results.print()  # or .show(), .save(), .crop(), .pandas(), etc.