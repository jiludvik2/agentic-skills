from __future__ import annotations

import contextlib
import socket
import threading
from collections.abc import Generator
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Schemathesis test target")


class UserResponse(BaseModel):
    user_name: str


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int) -> Any:
    # Deliberate spec drift: spec declares user_name but handler returns username.
    return {"username": str(user_id)}


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
