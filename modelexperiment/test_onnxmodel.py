import cv2
import numpy as np
import onnxruntime as ort

# Load ONNX model
session = ort.InferenceSession("best_packages.onnx")  # Use "best_fp16.onnx" if needed

# Get model input details
input_name = session.get_inputs()[0].name
print("Model input name:", input_name)

# Hardcoded image size (match your training setting)
img_height, img_width = 320, 320

# Open webcam
cap = cv2.VideoCapture(0)
def sigmoid(x):
    return 1 / (1 + np.exp(-x))


while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Resize frame to model input size
    img = cv2.resize(frame, (img_width, img_height))

    # Preprocess frame
    img = img.astype(np.float32) / 255.0       # Use float16 if model requires
    img = img.transpose(2, 0, 1)               # HWC -> CHW
    img = np.expand_dims(img, axis=0)         # Add batch dimension

    # Run inference
    outputs = session.run(None, {input_name: img})

    # Post-processing
    pred = outputs[0].squeeze().T  # (2100, 15)

    boxes_xywh = pred[:, :4]
    objectness = sigmoid(pred[:, 4])
    class_scores = sigmoid(pred[:, 5:])

    scores = objectness * class_scores.max(axis=1)
    class_ids = class_scores.argmax(axis=1)

    # Now try thresholding
    conf_thresh = 0.1
    keep = scores > conf_thresh

    boxes_xywh = boxes_xywh[keep]
    scores = scores[keep]
    class_ids = class_ids[keep]
    print("Objectness * max class score:", scores[:10])  # Show top 10
    print("Number of boxes above threshold:", np.sum(scores > 0.1))

    # Convert boxes to pixel coordinates
    boxes_xywh *= np.array([img_width, img_height, img_width, img_height])
    boxes = np.zeros_like(boxes_xywh)
    boxes[:, 0] = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2  # x1
    boxes[:, 1] = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2  # y1
    boxes[:, 2] = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2  # x2
    boxes[:, 3] = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2  # y2

    # Draw results on original frame (not resized one)
    scale_x = frame.shape[1] / img_width
    scale_y = frame.shape[0] / img_height

    for box, score, class_id in zip(boxes, scores, class_ids):
        x1 = int(box[0] * scale_x)
        y1 = int(box[1] * scale_y)
        x2 = int(box[2] * scale_x)
        y2 = int(box[3] * scale_y)

        label = f"Class {class_id}: {score:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Display result
    cv2.imshow("ONNX YOLOv8 Detection", frame)

    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
