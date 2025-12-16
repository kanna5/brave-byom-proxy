# Brave-BYOM-Proxy

A small proxy script that enables the use of OpenAI's flagship models in Brave
Browser's Assistant (Leo) via Bring Your Own Model (BYOM).

## Why

The BYOM feature in Brave is not compatible with OpenAI's flagship models
(e.g., GPT-5) because it always adds a `temperature` body parameter in API
calls, which the newer models do not support, thus causing a 400 response from
OpenAI's API and making it unusable.

The proxy script strips the unsupported parameters, extends the timeout to
allow models to reason longer, and adds a few adjustable parameters.

## Usage

Run it locally, then point Brave to this proxy instead of OpenAI.

```sh
# Run locally.
# Requires uv (astral-sh/uv). It will automatically download dependencies into the .venv directory.
uv run fastapi run main.py

# -- Or --

# Build a docker image
docker build --pull -t brave-byom-proxy .

# Run the docker image
docker run --rm --network host brave-byom-proxy
# Or run on specific host and port
docker run --rm --network host brave-byom-proxy --host 192.168.1.123 --port 8001
```

When exposing it publicly, make sure to set an access token and serve it over
HTTPS.

Configuration is read from environment variables or a .env file in the working
directory. The following settings are configurable, with their default values:

```sh
BYOMPROXY_UPSTREAM_ENDPOINT=https://api.openai.com/v1/chat/completions

# Timeout (seconds) when requesting the upstream endpoint. Reasoning models can
# take longer to respond, so don't set it too short.
BYOMPROXY_REQUEST_TIMEOUT=300

# Empty by default.
BYOMPROXY_ACCESS_TOKEN=

# Log requests for debugging (or curiosity). Set to 1 to enable.
BYOMPROXY_LOG_REQUEST=

# Set to 1 to disable the generation of conversation titles. All new conversations
# will be titled "New conversation."
BYOMPROXY_DISABLE_TITLE_GEN=

# If set, this model will be used for generating conversation titles.
# A faster model is recommended.
BYOMPROXY_TITLE_GEN_MODEL=gpt-4o-mini
```

When `BYOMPROXY_ACCESS_TOKEN` is set, prepend it to the upstream API key with a
colon in Brave's settings.

For example, with `BYOMPROXY_ACCESS_TOKEN=hello` and your OpenAI API key
`sk-proj-xxxxx`, the API key set in Brave has to be `hello:sk-proj-xxxxx`.

In addition, these API parameters are configurable via query parameters:

- [reasoning_effort](https://platform.openai.com/docs/api-reference/chat/create#chat_create-reasoning_effort)
- [service_tier](https://platform.openai.com/docs/api-reference/chat/create#chat_create-service_tier)
- [verbosity](https://platform.openai.com/docs/api-reference/chat/create#chat_create-verbosity)

For example, when the script is running on `localhost:8000`, you can configure
the server endpoint in Brave like this:

```
http://localhost:8000/v1/chat/completions?reasoning_effort=high&service_tier=priority&verbosity=low
```

When provided, these values are injected into the request body.

Please refer to the [official API document](https://platform.openai.com/docs/api-reference/chat/create) for details.

## Tips

### Reasoning Summary

Although OpenAI doesn't return the model's reasoning in the chat completions
API, you can add an instruction in the system prompt asking the model to
prepend a `<think></think>` block to its response.

For example:

```
- **Summarize your thinking:** Always start your response with a <think></think> block. Use it to store a concise summary of your reasoning (e.g., path to conclusion) for your own reference later in the conversation. It will be visible only to you.
```

### Alternatives

Try [OpenRouter](https://openrouter.ai/) if an additional third party is
acceptable.

With OpenRouter, adding the `:online` suffix to any model name enables research
capabilities (access to tools like web search, calculator, and more), and it's
compatible with the `v1/chat/completions` API.
