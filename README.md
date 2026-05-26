# Video+ZIP Timestamp Search (Flutter + Python)

这个工程现在是 **纯 Python 后端 + Flutter 前端**：

1. **Flutter 前端**：上传视频和 ZIP，触发 OCR 与 ZIP 检索。
2. **Python OCR 服务**：识别视频中的时间戳。
3. **Python ZIP 检索服务**：解压 ZIP 并检索包含时间戳的文件行。

## 目录结构

- `flutter_app/` Flutter Web/桌面界面
- `python_service/` FastAPI（OCR + ZIP 检索）
- `DE_RUST_PLAN.md` 去 Rust 化改造说明

## 运行步骤

### 1) 启动统一 Python 服务（8001）

```bash
cd python_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001
```

### 2) 启动 Flutter 前端

```bash
cd flutter_app
flutter pub get
flutter run -d chrome
```

## API 流程

1. Flutter 上传视频到 Python OCR：`POST /ocr/timestamps`（8001）
2. Python 返回时间戳列表
3. Flutter 上传 ZIP + 时间戳到 Python ZIP 检索：`POST /search/in-zip`（8001）
4. Python 返回匹配行列表

## 说明

- 已移除 Rust 服务（`rust_core`）。
- `zip_search_api.py` 使用安全解压（防 zip slip）和多进程并发逐行扫描。


## 新流程
- 选择 ZIP 后，前端会立刻调用 `POST /zip/preload` 完成解压并拿到 `zip_id`。
- 点击“开始处理”后才会上传视频到 OCR，然后调用 `/search/in-zip-by-id` 用 `zip_id` 做检索。
