from __future__ import annotations

import contextlib
import socket
import threading
from collections.abc import Generator
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Schemathesis test target")


class UserResponse(BaseModel):
    user_name: str


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int) -> Any:
    # Deliberate spec drift on a 2xx response: response_model keeps `user_name` in the OpenAPI
    # schema, but returning a raw JSONResponse bypasses FastAPI's response_model validation, so the
    # handler serves `username` at HTTP 200. This is a response_schema_conformance violation
    # (NOT a 500) — exactly what Schemathesis must flag as response_schema_violation.
    return JSONResponse({"username": str(user_id)})


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def running_server() -> Generator[str, None, None]:
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        import time
        for _ in range(30):
            time.sleep(0.1)
            if server.started:
                break
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)
