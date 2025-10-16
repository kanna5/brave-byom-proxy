# Brave-BYOM-Proxy

A small proxy script that addresses issues when using Leo (Brave’s built-in AI
assistant) with Bring Your Own Model (BYOM):

- Unable to use OpenAI’s reasoning models like gpt-5, o3, etc.  
  Brave adds a `temperature` parameter that these models don’t support. The
  proxy removes it before sending the request to OpenAI’s endpoint.
- Timeout.  
  Brave waits for approximately one minute, which is sometimes too short for
  reasoning models. The proxy sends a keep-alive message every 10 seconds so the
  browser keeps waiting.

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

### Reasoning Summary

Although OpenAI doesn't return the model's reasoning in the chat completions
API, you can add an instruction in the system prompt asking the model to
prepend a `<think></think>` block to its response.

For example:

```
- **Summarize your thinking:** Always start your response with a <think></think> block. Use it to store a concise summary of your reasoning for your own reference later in the conversation. It will be visible only to you.
```

### Alternatives

Try [OpenRouter](https://openrouter.ai/) if an additional third party is
acceptable.

With OpenRouter, adding the `:online` suffix to any model name enables research
capabilities (access to tools like web search, calculator, and more), and it's
compatible with the `v1/chat/completions` API.
