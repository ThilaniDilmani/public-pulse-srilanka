"""FastAPI app entrypoint. Reads pre-scored data from Postgres (batch-scored
by scripts/run_inference.py) -- routes should not trigger live model inference.
"""

from fastapi import FastAPI

app = FastAPI(title="Public Pulse API")


@app.get("/health")
def health():
    return {"status": "ok"}
