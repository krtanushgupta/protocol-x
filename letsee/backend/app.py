"""FastAPI app, API validation, and static PWA delivery."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .pipeline.analysis import MAX_CHARS, analyze
from .pipeline.validation import EvidenceValidationError, validate_analysis_evidence
from .schemas import AnalysisRequest, AnalysisResponse

ROOT=Path(__file__).resolve().parent.parent
FRONTEND=ROOT / "frontend"
MAX_BODY_BYTES=8_100_000

class RequestBodyLimitMiddleware:
    """Reject oversized API bodies before buffering them into a request object."""
    def __init__(self, app, max_bytes: int):
        self.app=app
        self.max_bytes=max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != "/api/analyze":
            await self.app(scope, receive, send)
            return
        headers={key.lower(): value for key, value in scope.get("headers", [])}
        try:
            content_length=int(headers.get(b"content-length", b"0"))
        except ValueError:
            content_length=0
        if content_length > self.max_bytes:
            await self._too_large(send)
            return
        buffered=[]
        size=0
        while True:
            message=await receive()
            buffered.append(message)
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                await self._too_large(send)
                return
            if not message.get("more_body", False):
                break
        async def replay():
            if buffered:
                return buffered.pop(0)
            return await receive()
        await self.app(scope, replay, send)

    @staticmethod
    async def _too_large(send):
        body=json.dumps({"detail":"Request body is too large (maximum 8 MB)."}).encode()
        await send({"type":"http.response.start","status":413,"headers":[(b"content-type",b"application/json"),(b"content-length",str(len(body)).encode())]})
        await send({"type":"http.response.body","body":body})

app=FastAPI(title="UNMISSED API", version="1.0.0", description="Evidence-linked local conversation analysis.")
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=MAX_BODY_BYTES)
origins=[origin.strip() for origin in os.getenv("UNMISSED_CORS_ORIGINS", "").split(",") if origin.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Content-Type"])

@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, exc: RequestValidationError):
    errors=exc.errors()
    if any(error.get("type") == "string_too_long" for error in errors):
        return JSONResponse(status_code=413, content={"error":f"Conversation must contain 1 to {MAX_CHARS:,} non-whitespace characters."})
    return JSONResponse(status_code=400, content={"error":"Invalid request. Send JSON with a non-empty 'text' field containing the WhatsApp conversation."})

@app.get("/api/health", tags=["system"])
def health():
    return {"status":"ok"}

@app.post("/api/analyze", response_model=AnalysisResponse, tags=["analysis"])
def analyze_conversation(payload: AnalysisRequest) -> AnalysisResponse:
    """Analyze one conversation without persisting its text or source messages."""
    try:
        result=analyze(payload.text)
        validate_analysis_evidence(result, payload.text)
        return AnalysisResponse.model_validate(result)
    except EvidenceValidationError:
        return JSONResponse(status_code=500, content={"error":"Analysis failed source validation. Your conversation was not stored; please retry."})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error":str(exc)})
    except Exception:
        return JSONResponse(status_code=500, content={"error":"Analysis failed. Your conversation was not stored; please retry."})

@app.get("/", include_in_schema=False)
def app_shell():
    from fastapi.responses import FileResponse
    return FileResponse(FRONTEND / "index.html")

# Static app shell only. The service worker deliberately does not cache API requests.
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
