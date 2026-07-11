import os
from dataclasses import dataclass


@dataclass
class Config:
    upstream_endpoint: str = "https://api.openai.com/v1/chat/completions"
    request_timeout: int = 300
    access_token: str | None = None
    log_request: bool = False

    disable_title_gen: bool = False
    """Return 400 for conversation title generation requests if set to True."""

    title_gen_model: str | None = "gpt-5.6-luna"
    """If set, this model will be used for generating conversation titles."""

    def load_from_env(self, prefix: str = "BYOMPROXY_"):
        upstream_endpoint = os.getenv(f"{prefix}UPSTREAM_ENDPOINT")
        if upstream_endpoint:
            self.upstream_endpoint = upstream_endpoint

        request_timeout = os.getenv(f"{prefix}REQUEST_TIMEOUT")
        if request_timeout:
            try:
                self.request_timeout = int(request_timeout)
            except ValueError as e:
                raise ValueError(
                    f"Invalid {prefix}REQUEST_TIMEOUT value: {request_timeout}"
                ) from e
            if self.request_timeout <= 0:
                raise ValueError(f"{prefix}REQUEST_TIMEOUT must be a positive integer")

        access_token = os.getenv(f"{prefix}ACCESS_TOKEN")
        if access_token:
            self.access_token = access_token

        log_request = os.getenv(f"{prefix}LOG_REQUEST") or ""
        if log_request.lower() in ["yes", "1", "true"]:
            self.log_request = True

        disable_title_gen = os.getenv(f"{prefix}DISABLE_TITLE_GEN") or ""
        if disable_title_gen.lower() in ["yes", "1", "true"]:
            self.disable_title_gen = True

        title_gen_model = os.getenv(f"{prefix}TITLE_GEN_MODEL")
        if title_gen_model:
            self.title_gen_model = title_gen_model


config = Config()
