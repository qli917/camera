import json
import os
import uuid
import re
import shutil
import tempfile
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI, File, Form, UploadFile

app = FastAPI(title="ZIP Timestamp Search API")

TEXT_EXTENSIONS = {
    ".txt", ".log", ".csv", ".json", ".xml", ".yaml", ".yml", ".md"
}
TS_RE = re.compile(r"\d{2}:\d{2}:\d{2}")

ZIP_CACHE_ROOT = Path(tempfile.gettempdir()) / "zipsearch_cache"
ZIP_CACHE_ROOT.mkdir(parents=True, exist_ok=True)


def _prepare_zip(zip_file: UploadFile) -> tuple[str, Path, int]:
    zip_id = str(uuid.uuid4())
    work_dir = ZIP_CACHE_ROOT / zip_id
    work_dir.mkdir(parents=True, exist_ok=True)

    zip_path = work_dir / (zip_file.filename or "input.zip")
    with open(zip_path, "wb") as f:
        f.write(zip_file.file.read())

    extracted = work_dir / "unzipped"
    extracted.mkdir(parents=True, exist_ok=True)
    _safe_extract(zip_path, extracted)
    files = _iter_files(extracted)
    return zip_id, extracted, len(files)


def _safe_extract(zip_path: Path, out_dir: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target = out_dir / member.filename
            resolved = target.resolve()
            if not str(resolved).startswith(str(out_dir.resolve())):
                raise ValueError(f"Blocked unsafe zip path: {member.filename}")
            if member.is_dir():
                resolved.mkdir(parents=True, exist_ok=True)
                continue
            resolved.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as src, open(resolved, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)


def _iter_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()]


def _scan_one_file(file_path: Path, timestamps: list[str]) -> list[dict]:
    if file_path.suffix.lower() not in TEXT_EXTENSIONS:
        return []

    hits = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore", buffering=1024 * 1024) as f:
            for i, line in enumerate(f, start=1):
                for ts in timestamps:
                    if ts in line:
                        hits.append({
                            "file": str(file_path),
                            "line_no": i,
                            "line": line.rstrip("\n"),
                            "matched_ts": ts,
                        })
    except OSError:
        return []
    return hits


def _normalize_timestamps(raw: Iterable[str]) -> list[str]:
    out = []
    for item in raw:
        out.extend(m.group(0) for m in TS_RE.finditer(item))
    return sorted(set(out))


@app.post("/search/in-zip")
async def search_in_zip(
    zip_file: UploadFile = File(...),
    timestamps_json: str = Form(...),
    workers: int = Form(4),
):
    """
    timestamps_json: JSON array string, e.g. ["12:00:01","12:00:02"]
    """
    try:
        raw_timestamps = json.loads(timestamps_json)
        if not isinstance(raw_timestamps, list):
            return {"error": "timestamps_json must be JSON list"}
    except json.JSONDecodeError:
        return {"error": "invalid timestamps_json"}

    timestamps = _normalize_timestamps([str(x) for x in raw_timestamps])
    if not timestamps:
        return {"timestamp_count": 0, "file_count": 0, "hits": []}

    with tempfile.TemporaryDirectory(prefix="zipsearch_") as tmp_dir:
        tmp = Path(tmp_dir)
        zip_path = tmp / (zip_file.filename or "input.zip")
        with open(zip_path, "wb") as f:
            f.write(await zip_file.read())

        extracted = tmp / "unzipped"
        extracted.mkdir(parents=True, exist_ok=True)
        _safe_extract(zip_path, extracted)

        files = _iter_files(extracted)
        with ProcessPoolExecutor(max_workers=max(1, workers)) as ex:
            chunks = ex.map(_scan_one_file, files, [timestamps] * len(files))
            hits = [h for one in chunks for h in one]

    return {
        "timestamp_count": len(timestamps),
        "file_count": len(files),
        "hits": hits,
    }


@app.post("/zip/preload")
async def preload_zip(zip_file: UploadFile = File(...)):
    zip_id, _extracted, file_count = _prepare_zip(zip_file)
    return {"zip_id": zip_id, "file_count": file_count}


@app.post("/search/in-zip-by-id")
async def search_in_zip_by_id(
    zip_id: str = Form(...),
    timestamps_json: str = Form(...),
    workers: int = Form(4),
):
    try:
        raw_timestamps = json.loads(timestamps_json)
        if not isinstance(raw_timestamps, list):
            return {"error": "timestamps_json must be JSON list"}
    except json.JSONDecodeError:
        return {"error": "invalid timestamps_json"}

    timestamps = _normalize_timestamps([str(x) for x in raw_timestamps])
    extracted = ZIP_CACHE_ROOT / zip_id / "unzipped"
    if not extracted.exists():
        return {"error": "zip_id not found"}

    files = _iter_files(extracted)
    with ProcessPoolExecutor(max_workers=max(1, workers)) as ex:
        chunks = ex.map(_scan_one_file, files, [timestamps] * len(files))
        hits = [h for one in chunks for h in one]

    return {"timestamp_count": len(timestamps), "file_count": len(files), "hits": hits}
