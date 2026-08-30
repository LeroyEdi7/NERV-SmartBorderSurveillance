# Model Handoff Specification — TransReID & Deep-OC-SORT (Person 2 -> Person 4 & 6)

## 1. Overview
This document specifies the model interface and feature vector format produced by **Person 2 (Tracking & Cross-Camera Re-ID)** for consumption by:
- **Person 6 (Multi-Camera RTSP Workers)**: Runs feature extraction on per-camera worker nodes.
- **Person 4 (FastAPI Backend)**: Stores and queries appearance vectors in Vector DB / Redis for cross-camera gallery matching.

---

## 2. TransReID Model Specifications

| Parameter | Specification |
| :--- | :--- |
| **Model Architecture** | Vision Transformer (ViT-Base/16) with Jigsaw Patch Module (JPM) |
| **Input Image Size** | `(256, 128, 3)` (Height=256, Width=128, Channels=3, RGB) |
| **Normalization** | ImageNet standard: `mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]` |
| **Output Feature Dimension** | `768` float32 elements |
| **Normalization Output** | **L2-Normalized** ($||v||_2 = 1.0$) |
| **Export Formats** | PyTorch Checkpoint (`.pth`), ONNX (`transreid_vit_base.onnx`) |
| **Similarity Metric** | **Cosine Similarity** ($\text{sim}(a, b) = a \cdot b$) |

---

## 3. ONNX Runtime Python Integration Code Snippet

```python
import cv2
import numpy as np
import onnxruntime as ort

class TransReIDInference:
    def __init__(self, onnx_path: str = "weights/transreid_vit_base.onnx"):
        self.session = ort.InferenceSession(onnx_path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        self.input_name = self.session.get_inputs()[0].name
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)

    def extract_embedding(self, crop_bgr: np.ndarray) -> np.ndarray:
        # 1. Resize to (256, 128)
        resized = cv2.resize(crop_bgr, (128, 256))
        # 2. BGR to RGB and normalize
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        normalized = (rgb - self.mean) / self.std
        # 3. HWC to CHW -> NCHW
        tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, :].astype(np.float32)
        # 4. ONNX Inference
        outputs = self.session.run(None, {self.input_name: tensor})
        embedding = outputs[0].flatten()
        # 5. L2 Normalize
        norm = np.linalg.norm(embedding) + 1e-8
        return (embedding / norm).astype(np.float32)
```

---

## 4. Deep-OC-SORT Tracker Integration
- Deep-OC-SORT combines spatial momentum observation updates with 768-d TransReID embeddings.
- Track objects output:
  - `track_id`: Integer persistent entity track ID.
  - `bbox`: `[x1, y1, x2, y2]` bounding box coordinates.
  - `embeddings`: Rolling buffer of last 5 L2-normalized embeddings for occlusion recovery and cross-camera exit registration.
