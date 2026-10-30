"""Điểm thay mô hình. Không tải model tự động; mặc định luôn unknown.

AI_PROVIDER: none | segformer | gemini. Để trống thì dùng segformer khi có AI_MODEL_DIR, ngược lại none.
Mọi nhà cung cấp trả cùng một dạng: status, risk, summary, model, regions (+ trường riêng của provider).
"""
import os
from pathlib import Path
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
_model = None
_processor = None
_gemini = None
DARK_MEAN = 15  # độ sáng trung bình 0..255; ảnh tối hơn không đủ căn cứ để phân tích


def provider() -> str:
    value = os.getenv('AI_PROVIDER', '').strip().lower()
    if not value:
        return 'segformer' if os.getenv('AI_MODEL_DIR', '').strip() else 'none'
    if value not in ('none', 'segformer', 'gemini'):
        raise RuntimeError('AI_PROVIDER phải là none, segformer hoặc gemini')
    return value


def not_configured(summary='Chưa cài mô hình AI.'):
    return {'status': 'not_configured', 'risk': 'unknown', 'summary': summary, 'model': None, 'regions': []}


def too_dark(path: Path) -> bool:
    with Image.open(path) as im:
        return ImageStat.Stat(im.convert('L')).mean[0] < DARK_MEAN


def analyze(path: Path) -> dict:
    name = provider()
    if name == 'none':
        return not_configured()
    if name == 'gemini':
        global _gemini
        if _gemini is None:
            from server.gemini import GeminiAnalyzer
            _gemini = GeminiAnalyzer(os.getenv('GEMINI_API_KEY', ''), os.getenv('GEMINI_MODEL', ''))
        return _gemini.analyze(path)
    return _segformer(path)


def model_dir() -> Path | None:
    """AI_MODEL_DIR tương đối được tính từ thư mục gốc dự án, không phụ thuộc thư mục đang đứng."""
    folder = os.getenv('AI_MODEL_DIR', '').strip()
    if not folder: return None
    path = Path(folder).expanduser()
    return path if path.is_absolute() else ROOT / path

def _segformer(path: Path) -> dict:
    global _model, _processor
    folder = model_dir()
    if folder is None:
        return not_configured('AI_PROVIDER=segformer nhưng AI_MODEL_DIR đang trống.')
    if not (folder / 'config.json').is_file():
        return not_configured(f'Không thấy model trong {folder.name}; kiểm tra AI_MODEL_DIR.')
    if too_dark(path):
        return {'status': 'ready', 'risk': 'unknown', 'summary': 'Ảnh quá tối để phân tích đáng tin cậy.', 'model': Path(folder).name, 'regions': [], 'provider': 'segformer'}
    try:
        import torch
        from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
    except ImportError:
        return not_configured('Chưa cài thư viện AI: pip install -r ai/requirements-ai.txt')
    if _model is None:
        _processor = AutoImageProcessor.from_pretrained(str(folder), local_files_only=True, trust_remote_code=False)
        _model = AutoModelForSemanticSegmentation.from_pretrained(str(folder), local_files_only=True, trust_remote_code=False, use_safetensors=True).eval()
    with Image.open(path) as im:
        rgb = im.convert('RGB')
        inputs = _processor(images=rgb, return_tensors='pt')
        with torch.inference_mode():
            logits = _model(**inputs).logits
            scores = torch.nn.functional.interpolate(logits, size=(rgb.height, rgb.width), mode='bilinear', align_corners=False).softmax(dim=1)[0]
            confidence, mask = scores.max(dim=0)
        # Nửa dưới, 60% giữa ảnh chỉ là ROI thử nghiệm, KHÔNG phải khoảng cách.
        h, w = mask.shape
        roi = mask[h//2:, w//5:4*w//5]
        roi_conf = confidence[h//2:, w//5:4*w//5]
        regions = []
        for value in roi.unique().tolist():
            selected = roi == value
            area = float(selected.float().mean())
            if area < .01:
                continue
            label = str(_model.config.id2label.get(value, value))
            regions.append({'label': label, 'fraction': round(area, 4), 'confidence': round(float(roi_conf[selected].mean()), 3)})
        regions.sort(key=lambda item: item['fraction'], reverse=True)
        water_labels = {'water', 'sea', 'river', 'lake', 'water_hazard'}
        road_labels = {'road', 'roadway'}
        water = any(r['label'].strip().lower() in water_labels and r['fraction'] >= .02 and r['confidence'] >= .55 for r in regions)
        road = any(r['label'].strip().lower() in road_labels and r['fraction'] >= .15 and r['confidence'] >= .55 for r in regions)
        risk = 'possible_water' if water else 'possible_road' if road else 'unknown'
        summary = {'possible_water': 'Có vùng giống mặt nước; cần người hỗ trợ kiểm tra.', 'possible_road': 'Có vùng giống lòng đường; chưa xác định được việc sang đường.', 'unknown': 'Chưa đủ căn cứ xác định nguy cơ.'}[risk]
        return {'status': 'ready', 'risk': risk, 'summary': summary, 'model': Path(folder).name, 'regions': regions, 'method': 'semantic_segmentation_roi_heuristic_v1', 'provider': 'segformer'}
