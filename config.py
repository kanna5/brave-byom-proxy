import os
from dataclasses import dataclass


@dataclass
class Config:
    upstream_endpoint: str = "https://api.openai.com/v1/chat/completions"
    request_timeout: int = 60
    access_token: str | None = None

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


config = Config()
