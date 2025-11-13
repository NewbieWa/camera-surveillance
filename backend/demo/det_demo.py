from ultralytics import YOLO
import cv2
import torch

conf_threshold = 0.8
image_path = 'images/example.png'
model_path = 'models/det_20250924.pt'
output_path = 'images/output.png'
# 根据系统自动判断用mps还是gpu还是cpu
if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

# 加载模型并预测
model = YOLO(model_path)
results = model(image_path, conf=conf_threshold, device=device)

# 检查是否检测到物体
if len(results[0].boxes) > 0:
    detected_classes = []
    for box in results[0].boxes:
        class_id = int(box.cls)
        class_name = model.names[class_id]
        detected_classes.append(class_name)
    print(f"检测到的物体类别: {detected_classes}")
    # 保存一下结果图片
    output_img = results[0].plot()
    cv2.imwrite(output_path, output_img)
else:
    print("未检测到物体")

