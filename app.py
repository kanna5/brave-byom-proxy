from typing import Literal

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from config import config

app = FastAPI()
_client = httpx.AsyncClient()

ReasoningEffort = Literal["minimal", "low", "medium", "high"]
ServiceTier = Literal["auto", "default", "flex", "priority"]
Verbosity = Literal["low", "medium", "high"]


def split_token(req_token: str) -> tuple[str | None, str | None]:
    parts = req_token.split(":")
    if len(parts) == 1:
        return None, parts[0]
    elif len(parts) == 2:
        return parts[0], parts[1]
    return None, None


@app.post("/v1/chat/completions")
async def completions(
    request: Request,
    reasoning_effort: ReasoningEffort | None = None,
    service_tier: ServiceTier | None = None,
    verbosity: Verbosity | None = None,
):
    proxy_token, upstream_token = split_token(
        request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    )
    if proxy_token != config.access_token:
        return JSONResponse({"error": "Unauthorized"}, 401)
    if not upstream_token:
        return JSONResponse({"error": "Missing upstream token"}, 401)

    try:
        body = await request.json()
    except Exception as e:
        return JSONResponse(
            {"error": f"Error while parsing request: {type(e).__name__}: {str(e)}"}, 400
        )

    if "temperature" in body:
        del body["temperature"]

    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    if service_tier:
        body["service_tier"] = service_tier
    if verbosity:
        body["verbosity"] = verbosity

    req = _client.build_request(
        "post",
        config.upstream_endpoint,
        json=body,
        headers={"authorization": f"Bearer {upstream_token}"},
        timeout=config.request_timeout,
    )
    r = await _client.send(req, stream=True)
    r.raise_for_status()

    return StreamingResponse(
        r.aiter_text(),
        headers={"content-type": r.headers.get("content-type")},
        background=BackgroundTask(r.aclose),
    )
