"""Transparent HTTP token interceptor proxy for tracking agent LLM consumption."""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import urljoin

import httpx

from scripts.schemas import TokenUsage

logger = logging.getLogger(__name__)


class TokenAccumulator:
    """Thread-safe accumulator for intercepted token counts."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.usage = TokenUsage()

    def record(self, input_tokens: int = 0, output_tokens: int = 0, total_tokens: int = 0) -> None:
        with self._lock:
            calc_total = total_tokens if total_tokens > 0 else (input_tokens + output_tokens)
            self.usage.input_tokens += input_tokens
            self.usage.output_tokens += output_tokens
            self.usage.total_tokens += calc_total

    def get_usage(self) -> TokenUsage:
        with self._lock:
            return TokenUsage(
                input_tokens=self.usage.input_tokens,
                output_tokens=self.usage.output_tokens,
                total_tokens=self.usage.total_tokens,
            )

    def reset(self) -> None:
        with self._lock:
            self.usage = TokenUsage()


def parse_token_payload(raw_text: str, accumulator: TokenAccumulator) -> None:
    """Parse text/event-stream or JSON response bodies to extract token usage."""
    if not raw_text:
        return

    # Check for Server-Sent Events (SSE) format
    if "data:" in raw_text:
        for line in raw_text.splitlines():
            line = line.strip()
            if line.startswith("data:") and not line.startswith("data: [DONE]"):
                payload_str = line[5:].strip()
                if payload_str:
                    try:
                        data = json.loads(payload_str)
                        extract_usage_from_dict(data, accumulator)
                    except json.JSONDecodeError:
                        continue
    else:
        # Standard JSON body
        try:
            data = json.loads(raw_text)
            extract_usage_from_dict(data, accumulator)
        except json.JSONDecodeError:
            pass


def extract_usage_from_dict(data: dict, accumulator: TokenAccumulator) -> None:
    """Extract usage metrics according to OpenAI, Anthropic, or standard schemas."""
    if not isinstance(data, dict):
        return

    # 1. Standard OpenAI usage block: {"usage": {"prompt_tokens": ..., "completion_tokens": ...}}
    if "usage" in data and isinstance(data["usage"], dict):
        u = data["usage"]
        in_tok = u.get("prompt_tokens", u.get("input_tokens", 0)) or 0
        out_tok = u.get("completion_tokens", u.get("output_tokens", 0)) or 0
        tot_tok = u.get("total_tokens", 0) or (in_tok + out_tok)
        accumulator.record(input_tokens=in_tok, output_tokens=out_tok, total_tokens=tot_tok)
        return

    # 2. Anthropic message_start event: {"type": "message_start", "message": {"usage": {"input_tokens": ...}}}
    if data.get("type") == "message_start" and isinstance(data.get("message"), dict):
        msg_usage = data["message"].get("usage", {})
        in_tok = msg_usage.get("input_tokens", 0) or 0
        accumulator.record(input_tokens=in_tok)
        return

    # 3. Anthropic message_delta event: {"type": "message_delta", "usage": {"output_tokens": ...}}
    if data.get("type") == "message_delta" and isinstance(data.get("usage"), dict):
        delta_usage = data["usage"]
        out_tok = delta_usage.get("output_tokens", 0) or 0
        accumulator.record(output_tokens=out_tok)
        return


class InterceptorHandler(BaseHTTPRequestHandler):
    """HTTP request handler that forwards requests to upstream and extracts token counts."""

    accumulator: TokenAccumulator
    upstream_url: str
    client: httpx.Client

    def do_HEAD(self) -> None:
        self._proxy_request("HEAD")

    def do_GET(self) -> None:
        self._proxy_request("GET")

    def do_POST(self) -> None:
        self._proxy_request("POST")

    def do_PUT(self) -> None:
        self._proxy_request("PUT")

    def do_DELETE(self) -> None:
        self._proxy_request("DELETE")

    def _proxy_request(self, method: str) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Build target upstream URL
        target_url = urljoin(self.upstream_url.rstrip("/") + "/", self.path.lstrip("/"))

        # Copy incoming headers, omitting host
        forward_headers = {k: v for k, v in self.headers.items() if k.lower() != "host"}

        try:
            request = self.client.build_request(
                method=method,
                url=target_url,
                headers=forward_headers,
                content=body,
                timeout=120.0,
            )
            response = self.client.send(request, stream=True)

            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() not in ("transfer-encoding", "content-length"):
                    self.send_header(key, value)

            # Collect response bytes while forwarding to client
            collected_chunks = []
            try:
                for chunk in response.iter_bytes():
                    collected_chunks.append(chunk)
                    self.wfile.write(chunk)
                self.wfile.flush()
            finally:
                response.close()

            # Parse captured content for token usage
            full_body = b"".join(collected_chunks).decode("utf-8", errors="replace")
            parse_token_payload(full_body, self.accumulator)

        except Exception as exc:
            logger.error("Proxy error forwarding to %s: %s", target_url, exc)
            self.send_error(502, f"Bad Gateway: {exc}")

    def log_message(self, format: str, *args) -> None:
        # Suppress noisy standard HTTP access logs
        pass


class TokenInterceptorProxy:
    """Manages lifecycle of the local token interceptor proxy server."""

    def __init__(self, upstream_url: str = "https://api.openai.com") -> None:
        self.upstream_url = upstream_url
        self.accumulator = TokenAccumulator()
        self.http_client = httpx.Client()
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.host: str = "127.0.0.1"
        self.port: int = 0

    def start(self) -> None:
        handler_cls = type(
            "BoundInterceptorHandler",
            (InterceptorHandler,),
            {
                "accumulator": self.accumulator,
                "upstream_url": self.upstream_url,
                "client": self.http_client,
            },
        )
        # Bind to 127.0.0.1 with port 0 to let OS assign an available port
        self._server = ThreadingHTTPServer((self.host, 0), handler_cls)
        self.port = self._server.server_port

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def get_usage(self) -> TokenUsage:
        return self.accumulator.get_usage()

    def reset_usage(self) -> None:
        self.accumulator.reset()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        self.http_client.close()

    def __enter__(self) -> "TokenInterceptorProxy":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
