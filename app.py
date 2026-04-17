import asyncio
import json
import logging
import re
from typing import Awaitable, Literal

import fastapi
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

import misc
from config import config

app = FastAPI(openapi_url=None)
app.add_middleware(GZipMiddleware)

_client = httpx.AsyncClient()
_logger = logging.getLogger(__name__)

ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]
ServiceTier = Literal["auto", "default", "flex", "priority"]
Verbosity = Literal["low", "medium", "high"]

reasoning_models = [
    re.compile(r"^o\d"),
    re.compile(r"^gpt-5(\.\d+)?(-(mini|nano|codex))?(-[\d-]+)?$"),
    re.compile(r"^claude-[a-z]+-(4-[7-9]|[5-9])"),
]
newer_models = re.compile(r"^gpt-[5-9]")


def is_reasoning_model(name: str) -> bool:
    for pattern in reasoning_models:
        if pattern.match(name):
            return True
    return False


def is_newer_model(name: str) -> bool:
    return bool(newer_models.match(name))


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
                "🛑 Error occurred while requesting model response. Check server logs for details.\n"
            )
            yield forge_msg(None)

            if isinstance(exc, httpx.HTTPStatusError):
                # Log response headers and body
                await exc.response.aread()
                logobj = {
                    "http": exc.response.status_code,
                    "msg": str(exc),
                    "headers": exc.response.headers,
                    "body": exc.response.text,
                }
                _logger.error(logobj)
                return

            raise exc


def is_title_gen_request(body) -> bool:
    if not isinstance(body, dict):
        return False
    if "stream" in body and body["stream"] is not False:
        return False
    # look for `"stop": ["</title>"]`
    if "stop" not in body or not (
        isinstance(body["stop"], list) or isinstance(body["stop"], str)
    ):
        return False
    return "</title>" in body["stop"]


async def proxy_title_gen_request(body, upstream_token: str) -> fastapi.Response:
    if not isinstance(body, dict):
        return JSONResponse({"error": "invalid request body"}, 400)

    # Not supported by all models. Delete for better compatibility
    del_opts = [
        "reasoning_effort",
        # "stop",
        "temperature",
        "verbosity",
    ]
    for opt in del_opts:
        if opt in body:
            del body[opt]

    if config.title_gen_model is not None:
        if "claude" in body["model"]:
            body["model"] = "claude-haiku-4-5-20251001"
        else:
            body["model"] = config.title_gen_model

    if is_reasoning_model(body["model"]):
        body["reasoning_effort"] = "low"

    if is_newer_model(body["model"]):
        body["reasoning_effort"] = "minimal"
        body["verbosity"] = "low"

    upstream_req = _client.build_request(
        "post",
        misc.ANTHROPIC_API_ENDPOINT
        if "claude" in body["model"]
        else config.upstream_endpoint,
        json=body,
        headers={"authorization": f"Bearer {upstream_token}"},
        timeout=20,
    )

    upstream_resp = await _client.send(upstream_req)
    resp_headers = dict(upstream_resp.headers)

    return fastapi.Response(
        upstream_resp.read(),
        headers={"content-type": resp_headers["content-type"]},
        status_code=upstream_resp.status_code,
    )


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

    if "model" not in body:
        return JSONResponse({"error": "model is required"}, 400)

    is_claude = "claude" in body["model"]
    if "temperature" in body:
        if is_reasoning_model(body["model"]):
            del body["temperature"]

    if reasoning_effort:
        if not is_claude:  # sad
            body["reasoning_effort"] = reasoning_effort
    if service_tier:
        body["service_tier"] = service_tier
    if verbosity:
        body["verbosity"] = verbosity

    if is_title_gen_request(body):
        if config.disable_title_gen:
            return JSONResponse({"error": "Title generation is disabled"}, 400)
        return await proxy_title_gen_request(body, upstream_token)

    if "stream" not in body or body["stream"] is not True:
        return JSONResponse({"error": "Non-streaming requests are not supported"}, 400)

    upstream_req = _client.build_request(
        "post",
        misc.ANTHROPIC_API_ENDPOINT if is_claude else config.upstream_endpoint,
        json=body,
        headers={"authorization": f"Bearer {upstream_token}"},
        timeout=config.request_timeout,
    )

    resp = asyncio.create_task(_client.send(upstream_req, stream=True))
    return StreamingResponse(
        proxy_result(resp),
        headers={"content-type": "text/event-stream"},
    )
