## Problem

I tried to access OpenAI's gpt-5 model in Leo AI (Brave browser's integrated
assistant) via BYOM (bring your own model) but couldn't.

When Brave calls the `v1/chat/completions` API, it always adds a temperature
option, which the gpt-5 model doesn't support, resulting in a 400 response from
OpenAI.

## Solution

I wrote a simple Python script to act as a proxy so I can modify the request
options and make it work.

## Usage

Run it locally, in a Docker container, or on your cloud server, then configure
Brave to use its API endpoint instead of OpenAI's.

```sh
uv sync
uv run fastapi run main.py
```

When serving it on a publicly accessible server, make sure to set an access
token and serve it over HTTPS.

Configuration is read from environment variables or a .env file in the working
directory. The following options are configurable, with their default values:

```sh
BYOMPROXY_UPSTREAM_ENDPOINT=https://api.openai.com/v1/chat/completions

# Timeout when requesting the upstream endpoint. Models need to think, so don't set it too short.
BYOMPROXY_REQUEST_TIMEOUT=60

# Empty by default.
BYOMPROXY_ACCESS_TOKEN=
```

When `BYOMPROXY_ACCESS_TOKEN` is set, you need to append it to the upstream API
key with a colon.

For example, with `BYOMPROXY_ACCESS_TOKEN=hello` and your OpenAI API key
`sk-proj-xxxxx`, you must set the API key in Brave to `hello:sk-proj-xxxxx`.

As a bonus, I made these API options configurable via query parameters:

- reasoning_effort
- service_tier
- verbosity

For example, when the script is running on `localhost:8000`, you can configure
the server endpoint in Brave like this:

```
http://localhost:8000/v1/chat/completions?reasoning_effort=high&service_tier=priority&verbosity=low
```

When set, these values are injected into the request body.

Please refer to the [official API document](https://platform.openai.com/docs/api-reference/chat/create) for details.

## Tips

Although OpenAI doesn't return the model's reasoning in the chat completions
API, you can add an instruction in the system prompt asking the model to append
a `<think></think>` block to its response.

For example, I added this:

```
- **Summarize your thinking:** Always start your response with a <think></think> block. Use it to store a concise summary of your reasoning for your own reference later in the conversation. It will be visible only to you.
```
