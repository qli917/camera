from fastapi import FastAPI

from app import app as ocr_app
from zip_search_api import app as zip_app

app = FastAPI(title="Video OCR + ZIP Search API")

# Reuse existing endpoints under one port.
for route in ocr_app.routes:
    app.router.routes.append(route)

for route in zip_app.routes:
    # avoid duplicate docs/openapi routes from sub apps
    if getattr(route, "path", "") in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}:
        continue
    app.router.routes.append(route)
