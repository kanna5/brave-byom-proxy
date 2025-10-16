## Problem

Brave Leo’s BYOM (Bring Your Own Model) adds a temperature parameter when
calling the `/v1/chat/completions` endpoint. The gpt-5 model doesn’t support
it, resulting in an HTTP 400 from OpenAI.

## Solution

A small Python proxy that rewrites requests (e.g., strips unsupported
parameters) before forwarding to OpenAI.

## Usage

Run it locally, then point Brave to this proxy instead of OpenAI.

```sh
# Download dependencies
uv sync

# Run locally
uv run fastapi run main.py

# -- Or --

# Build docker image
docker build --pull -t brave-byom-proxy .

# Run the docker image
docker run --rm --network host brave-byom-proxy
# Run on specific host and port
docker run --rm --network host brave-byom-proxy --host 192.168.1.123 --port 8001
```

When exposing it publicly, make sure to set an access token and serve it over
HTTPS.

Configuration is read from environment variables or a .env file in the working
directory. The following settings are configurable, with their default values:

```sh
BYOMPROXY_UPSTREAM_ENDPOINT=https://api.openai.com/v1/chat/completions

# Timeout when requesting the upstream endpoint. Reasoning models can take
# longer to response, so don't set it too short.
BYOMPROXY_REQUEST_TIMEOUT=300

# Empty by default.
BYOMPROXY_ACCESS_TOKEN=
```

When `BYOMPROXY_ACCESS_TOKEN` is set, prepend it to the upstream API key with a
colon in Brave's settings.

For example, with `BYOMPROXY_ACCESS_TOKEN=hello` and your OpenAI API key
`sk-proj-xxxxx`, the API key set in Brave has to be `hello:sk-proj-xxxxx`.

In addition, these API parameters are configurable via query parameters:

- reasoning_effort
- service_tier
- verbosity

For example, when the script is running on `localhost:8000`, you can configure
the server endpoint in Brave like this:

```
http://localhost:8000/v1/chat/completions?reasoning_effort=high&service_tier=priority&verbosity=low
```

When provided, these values are injected into the request body.

Please refer to the [official API document](https://platform.openai.com/docs/api-reference/chat/create) for details.

## Tips

Although OpenAI doesn't return the model's reasoning in the chat completions
API, you can add an instruction in the system prompt asking the model to
prepend a `<think></think>` block to its response.

For example:

```
- **Summarize your thinking:** Always start your response with a <think></think> block. Use it to store a concise summary of your reasoning for your own reference later in the conversation. It will be visible only to you.
```
