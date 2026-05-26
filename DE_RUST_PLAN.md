# 去 Rust 化状态

## 当前状态
- ✅ 已完成 Rust 移除。
- ✅ `rust_core/` 目录已删除。
- ✅ 检索能力由 `python_service/zip_search_api.py` 提供。

## 当前架构
- Flutter 前端（`flutter_app`）
- Python OCR（`python_service/app.py`）
- Python ZIP 检索（`python_service/zip_search_api.py`）

## 后续建议
1. 已合并为一个 FastAPI 进程（单端口 8001）。
2. 增加 SQLite 索引提高重复查询性能。
3. 给 Flutter 增加真正拖拽支持（目前主要是文件选择）。
