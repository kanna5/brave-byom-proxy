import asyncio
import json
import logging
import re
from typing import Awaitable, Literal

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from config import config

app = FastAPI(openapi_url=None)
app.add_middleware(GZipMiddleware)

_client = httpx.AsyncClient()
_logger = logging.getLogger(__name__)

ReasoningEffort = Literal["minimal", "low", "medium", "high"]
ServiceTier = Literal["auto", "default", "flex", "priority"]
Verbosity = Literal["low", "medium", "high"]

reasoning_models = [
    re.compile(r"^o\d"),
    re.compile(r"^gpt-5(-(mini|nano|codex))?(-[\d-]+)?$"),
]


def split_token(req_token: str) -> tuple[str | None, str | None]:
    parts = req_token.split(":")
    if len(parts) == 1:
        return None, parts[0]
    elif len(parts) == 2:
        return parts[0], parts[1]
    return None, None


def forge_msg(msg: str | None):
    if msg is None:
        return (
            """data: {"object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n"""
            """data: [DONE]\n\n"""
        )
    msg_encoded = json.dumps(msg)
    return (
        """data: {"object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"""
        f"{msg_encoded}"
        """},"finish_reason":null}]}\n\n"""
    )


async def proxy_result(resp: Awaitable[httpx.Response]):
    keepalive_str = ": keep-alive\n\n"
    yield keepalive_str

    while True:
        try:
            real_resp = await asyncio.wait_for(asyncio.shield(resp), 10)
            real_resp.raise_for_status()
            try:
                async for text in real_resp.aiter_text():
                    yield text
                break
            finally:
                await real_resp.aclose()

        except TimeoutError:
            yield keepalive_str
            continue

        except Exception as exc:
            yield forge_msg(
                "Error occurred while requesting model response. Check server logs for details.\n"
            )
            yield forge_msg(None)
            raise exc


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

    if config.log_request:
        _logger.info(
            "Request: %s",
            json.dumps(
                {"headers": dict(request.headers), "body": body},
                separators=(",", ":"),
            ),
        )

    if "stream" not in body or body["stream"] is not True:
        return JSONResponse({"error": "Non-streaming requests are not supported"}, 400)

    if "temperature" in body and "model" in body:
        model: str = body["model"]
        for pattern in reasoning_models:
            if pattern.match(model):
                del body["temperature"]
                break

    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    if service_tier:
        body["service_tier"] = service_tier
    if verbosity:
        body["verbosity"] = verbosity

    upstream_req = _client.build_request(
        "post",
        config.upstream_endpoint,
        json=body,
        headers={"authorization": f"Bearer {upstream_token}"},
        timeout=config.request_timeout,
    )

    resp = asyncio.create_task(_client.send(upstream_req, stream=True))
    return StreamingResponse(
        proxy_result(resp),
        headers={"content-type": "text/event-stream"},
    )
