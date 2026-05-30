"""Minimal FastAPI app whose 200 response violates its advertised schema.

The OpenAPI doc advertises the `User` model (id + user_name required), but the
handler returns a raw JSONResponse missing `user_name`, bypassing FastAPI's
response validation. Schemathesis' response_schema_conformance check should flag
a JsonSchemaError -> ruleId schemathesis.response_schema_violation.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()


class User(BaseModel):
    id: int
    user_name: str


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int) -> JSONResponse:
    # BUG: omits the required `user_name` field.
    return JSONResponse({"id": user_id})
