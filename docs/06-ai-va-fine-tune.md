# 06 — AI: mô hình gợi ý và cách tích hợp

## Nên chọn gì?

Ưu tiên **SegFormer-B0** cho bài toán bề mặt như đường, vỉa hè, mặt nước: đây là semantic segmentation, gán nhãn từng vùng/pixel. Mô hình nhỏ hơn các biến thể B1–B5, phù hợp bắt đầu trên laptop/server, không chạy mạng này trực tiếp trên ESP32.

Checkpoint thử nhanh: `nvidia/segformer-b0-finetuned-ade-512-512`. Nó có nhãn road, sidewalk, water, sea, river, lake, stairs trong ADE20K. Đây là baseline để thử pipeline, **không phải mô hình đã kiểm chứng cho camera đeo ngực tại Việt Nam**. [Tài liệu SegFormer](https://huggingface.co/docs/transformers/model_doc/segformer), [cấu hình nhãn checkpoint](https://huggingface.co/nvidia/segformer-b0-finetuned-ade-512-512/blob/main/config.json).

Nếu nhóm quen Ultralytics, có thể dùng **YOLO11n-seg** để học segmentation bằng polygon, nhưng pretrained COCO không có lớp đường/mặt nước; phải thêm dữ liệu và huấn luyện đầu ra phù hợp. YOLO11 không được gọi là bản mới nhất. Kiểm tra giấy phép model/thư viện khi vượt ngoài đồ án. [Tài liệu segmentation Ultralytics](https://docs.ultralytics.com/tasks/segment/).

Không cần fine-tune mô hình ngôn ngữ lớn để làm bước đầu. Nhận diện đường và nước bằng ảnh cũng không xác định được độ sâu nước, khoảng cách đến mép, dòng xe có nguy hiểm hay có được sang đường.

## Mặc định an toàn về tính trung thực

`AI_PROVIDER` và `AI_MODEL_DIR` đều trống (hoặc `AI_PROVIDER=none`): adapter trả (Gemini xem [tài liệu hợp nhất](11-hop-nhat.md)):

```json
{"status":"not_configured","risk":"unknown","summary":"Chưa cài mô hình AI.","model":null,"regions":[]}
```

Đây không phải kết quả nhận diện. Không có model giả trả “an toàn”. Khi có lỗi phân tích, web hiện lỗi/không xác định; SOS và ảnh vẫn được lưu.

## Thử pretrained baseline trước khi thu thập dữ liệu

Tạo môi trường Python 3.11/3.12 cho AI, hoặc cài thêm vào môi trường máy chủ đúng phiên bản Python hỗ trợ:

```powershell
.\.venv\Scripts\python.exe -m pip install -r ai/requirements-ai.txt
```

Tải model về thư mục riêng bằng Hugging Face/Transformers theo model card, ví dụ chạy Python:

```python
from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
name = "nvidia/segformer-b0-finetuned-ade-512-512"
AutoImageProcessor.from_pretrained(name).save_pretrained("ai/model-baseline")
AutoModelForSemanticSegmentation.from_pretrained(name, use_safetensors=True).save_pretrained(
    "ai/model-baseline", safe_serialization=True
)
```

Đổi `.env`: `AI_MODEL_DIR=ai/model-baseline`, khởi động máy chủ từ thư mục gốc. Dùng ảnh **mới** để chạy phân tích; các sự kiện cũ đã kết thúc với not_configured không tự phân tích lại. Runtime chỉ đọc model cục bộ, không tự tải model trong mỗi yêu cầu và không bật `trust_remote_code`.

Trong Docker mặc định, thư mục model chưa được gắn vào container. Muốn dùng AI phải cài requirements AI vào image và bind mount model read-only, đặt AI_MODEL_DIR theo đường dẫn trong container. Không kỳ vọng Dockerfile nền đã có Torch.

## Fine-tune theo bối cảnh của nhóm

Mã mẫu `ai/train_segformer.py` thực hiện vòng train/eval và lưu checkpoint tốt nhất theo mIoU validation. Đây là mã huấn luyện để nhóm dùng sau khi chuẩn bị dữ liệu, chưa chạy huấn luyện trong gói này.

Nhãn đề xuất đã thống nhất với script:

- 0: `background_unknown`, vùng còn lại; không mang nghĩa an toàn.
- 1: `sidewalk`, vỉa hè/lối đi.
- 2: `roadway`, lòng đường.
- 3: `water_hazard`, vùng nước cần người hỗ trợ kiểm tra.
- 4: `stairs`, bậc/cầu thang.
- 5: `obstacle`, vật cản thuộc phạm vi gán nhãn của nhóm.
- 255: vùng bỏ qua, không tính loss/metric.

Ảnh RGB, mask PNG **một kênh/chỉ số palette**, pixel chứa ID nhãn; không dùng ảnh tô màu RGB làm mask đầu vào. Ảnh và mask phải cùng kích thước. Lưu như:

```text
dataset/
  images/route_a_001.jpg
  masks/route_a_001.png
  train.jsonl
  val.jsonl
  test.jsonl
```

Mỗi dòng manifest:

```json
{"image":"images/route_a_001.jpg","mask":"masks/route_a_001.png"}
```

Chỉ phân bổ một ảnh vào một split. **Tách theo tuyến đường, vị trí và buổi quay**, không chia ngẫu nhiên các frame sát nhau; nếu không kết quả validation sẽ bị cao giả do giống ảnh train. Có thể bắt đầu bằng vài trăm ảnh đa dạng để thử quy trình rồi tăng dữ liệu theo các lỗi gặp; đây không phải số lượng đủ để đảm bảo an toàn. Đa dạng ngày/đêm, ánh sáng gắt, mặt đường ướt, phản chiếu, nước đứng, bóng cây, camera rung, góc đeo và loại camera thật. Không đứng gần mép ao/đường xe chạy để thu dữ liệu nguy hiểm.

Chỉ dùng hình có quyền sử dụng/đồng ý phù hợp; tránh lưu mặt người, địa chỉ và biển số không cần thiết. Quyết định cùng nhóm về thời hạn lưu và ai được xem dữ liệu. Ảnh người khiếm thị dùng dịch vụ không nên mặc định đưa vào tập train.

Lệnh train:

```powershell
.\.venv\Scripts\python.exe ai/train_segformer.py --data dataset --output ai/model --epochs 15 --batch 2
```

CPU chạy được nhưng có thể chậm; GPU giúp nhanh hơn. Nếu thiếu VRAM giảm batch về 1. Script đổi head về sáu lớp, `do_reduce_labels=False` vì lớp 0 là lớp thật; mask255 bỏ qua. Có lật ngang đồng thời ảnh/mask, không thay kích thước mask bằng nội suy làm lẫn nhãn. Xem công thức/chế độ tiền xử lý của [hướng dẫn semantic segmentation chính thức](https://huggingface.co/docs/transformers/tasks/semantic_segmentation).

Đánh giá cuối trên tập test tách riêng, không dùng để chọn checkpoint:

```powershell
.\.venv\Scripts\python.exe ai/train_segformer.py --data dataset --output ai/model --eval-only --eval-split test
```

Script xuất mIoU, IoU/recall từng lớp và confusion matrix. Báo cáo thêm tỷ lệ bỏ sót nước, báo nhầm đường/nước, lỗi theo điều kiện ánh sáng, độ trễ chụp → nhận → phân tích → hiển thị. Pixel recall cao không tự chứng minh phát hiện mọi tình huống nguy hiểm; cần bộ tình huống cấp sự kiện riêng và đánh giá với người hướng dẫn.

## Cắm model vào web

Sau train, thư mục `ai/model` cần có config, preprocessor config và trọng số safetensors. Đặt `AI_MODEL_DIR=ai/model`, khởi động lại backend; không sửa firmware/web. `server/ai_adapter.py` trả JSON có `status`, `risk`, `summary`, `model`, `regions`.

Adapter mẫu xét **nửa dưới, 60% giữa ảnh**; vùng nước ≥2% và điểm trung bình ≥0,55 thì `possible_water`; vùng đường ≥15% và điểm ≥0,55 thì `possible_road`; còn lại `unknown`. Đây là ngưỡng heuristic **chưa được hiệu chỉnh**, không phải chuẩn khoa học/an toàn. Điểm softmax không phải xác suất ngoài thực tế. Không quy đổi diện tích pixel thành khoảng cách mét.

Nếu dùng model khác, thay duy nhất hàm `analyze(path)` để trả cùng schema; thêm thư viện tương ứng trong môi trường server. Có thể trả thêm bounding boxes sau, nhưng giao diện hiện tại hiển thị nhãn/tỷ lệ vùng/điểm, chưa vẽ mask hoặc box trên ảnh. Không cần tạo kết quả giả để giao diện chạy.
