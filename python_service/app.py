import os
import re
import tempfile
from typing import List

import cv2
import easyocr
from fastapi import FastAPI, File, UploadFile

app = FastAPI(title="Video Timestamp OCR")
reader = easyocr.Reader(['en'], gpu=False)

TS_PATTERN = re.compile(r"(?:\d{4}-\d{2}-\d{2}\s+)?\d{2}:\d{2}:\d{2}")


def extract_timestamps(video_path: str, step_sec: int = 2) -> List[str]:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    step_frames = max(int(fps * step_sec), 1)
    frame_no = 0
    found = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_no % step_frames == 0:
            results = reader.readtext(frame, detail=0)
            for txt in results:
                for m in TS_PATTERN.findall(txt):
                    found.add(m)

        frame_no += 1

    cap.release()
    return sorted(found)


@app.post("/ocr/timestamps")
async def ocr_timestamps(video: UploadFile = File(...)):
    suffix = os.path.splitext(video.filename or "video.mp4")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await video.read())
        path = tmp.name

    try:
        timestamps = extract_timestamps(path)
        return {"timestamps": timestamps, "count": len(timestamps)}
    finally:
        os.remove(path)
