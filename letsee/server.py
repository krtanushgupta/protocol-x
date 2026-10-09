"""Backwards-compatible development launcher for the FastAPI app."""
from backend.app import app
from backend.pipeline.analysis import analyze, MAX_CHARS
from backend.pipeline.parsing import parse_messages, is_group_event
from backend.pipeline.validation import validate_analysis_evidence

def main() -> None:
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False, access_log=True)

if __name__ == "__main__":
    main()
