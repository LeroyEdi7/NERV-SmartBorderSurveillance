# Model Weights Directory

This directory stores trained deep learning weights for Person Re-ID and detection models:

- `transreid_vit_base.onnx` / `transreid_vit_base.pth`: Vision Transformer TransReID weights (768-d embeddings).
- `yolov8n.pt` / custom trained YOLO weights.

To download pre-trained TransReID weights from cloud storage, run:
```bash
python scripts/download_weights.py
```
