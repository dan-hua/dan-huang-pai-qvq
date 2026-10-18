from __future__ import annotations

import argparse
import html
import json
import os
import re
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
UPSTREAM_URL = "https://remotive.com/api/remote-jobs"
CACHE_SECONDS = 12 * 60 * 60
MAX_UPSTREAM_BYTES = 12 * 1024 * 1024
MAX_TRANSLATION_BODY_BYTES = 64 * 1024
MAX_TRANSLATION_FIELD_CHARS = 12000
MAX_TRANSLATION_TOTAL_CHARS = 14000
MAX_TRANSLATION_CHUNK_BYTES = 450
MAX_TRANSLATION_CHUNKS = 100
TRANSLATION_URL = "https://api.mymemory.translated.net/get"
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/site_config.js": ("site_config.js", "text/javascript; charset=utf-8"),
    "/job_finder.js": ("job_finder.js", "text/javascript; charset=utf-8"),
}


def fetch_remote_jobs() -> dict[str, Any]:
    request = Request(
        UPSTREAM_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "ShituJobSearch/1.0 (public job feed)",
        },
    )
    try:
        with urlopen(request, timeout=15, context=ssl.create_default_context()) as response:
            if response.status != 200:
                raise RuntimeError(f"岗位来源返回 HTTP {response.status}")
            content = response.read(MAX_UPSTREAM_BYTES + 1)
    except (URLError, TimeoutError) as error:
        raise RuntimeError("岗位来源暂不可用") from error

    if len(content) > MAX_UPSTREAM_BYTES:
        raise RuntimeError("岗位来源响应超过大小限制")
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("岗位来源返回的数据格式无法识别") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise RuntimeError("岗位来源返回的数据格式无法识别")
    return payload


def split_translation_chunks(text: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    sentences = re.split(r"(?<=[.!?。！？])\s*", text.strip())
    for sentence in sentences:
        if not sentence:
            continue
        if len(sentence.encode("utf-8")) <= MAX_TRANSLATION_CHUNK_BYTES:
            if current and len((current + " " + sentence).encode("utf-8")) > MAX_TRANSLATION_CHUNK_BYTES:
                chunks.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
            continue

        if current:
            chunks.append(current)
            current = ""
        words = re.findall(r"\S+\s*|\s+", sentence)
        for word in words:
            if len(word.encode("utf-8")) > MAX_TRANSLATION_CHUNK_BYTES:
                if current:
                    chunks.append(current)
                    current = ""
                fragment = ""
                for character in word:
                    if len((fragment + character).encode("utf-8")) > MAX_TRANSLATION_CHUNK_BYTES:
                        chunks.append(fragment)
                        fragment = character
                    else:
                        fragment += character
                current = fragment
            elif current and len((current + word).encode("utf-8")) > MAX_TRANSLATION_CHUNK_BYTES:
                chunks.append(current)
                current = word
            else:
                current += word
    if current:
        chunks.append(current)
    return chunks


def translate_text(text: str, target_language: str) -> str:
    if target_language not in {"zh-CN", "en"}:
        raise ValueError("Unsupported target language")
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TRANSLATION_FIELD_CHARS:
        raise ValueError("Translation text is empty or too long")

    source_language = "zh-CN" if re.search(r"[\u3400-\u9fff]", text) else "en"
    if source_language == target_language:
        return text

    chunks = split_translation_chunks(text)
    if not chunks or len(chunks) > MAX_TRANSLATION_CHUNKS:
        raise ValueError("Translation text contains too many segments")

    translated_chunks: list[str] = []
    for chunk in chunks:
        query = urlencode({"q": chunk, "langpair": f"{source_language}|{target_language}"})
        request = Request(
            f"{TRANSLATION_URL}?{query}",
            headers={"Accept": "application/json", "User-Agent": "ShituJobSearch/1.0 (on-demand translation)"},
        )
        try:
            with urlopen(request, timeout=15, context=ssl.create_default_context()) as response:
                if response.status != 200:
                    raise RuntimeError(f"翻译服务返回 HTTP {response.status}")
                payload = json.loads(response.read(256 * 1024 + 1))
        except HTTPError as error:
            if error.code == 429:
                raise RuntimeError("翻译服务已达到请求额度，请稍后再试。") from error
            raise RuntimeError(f"翻译服务暂不可用（HTTP {error.code}）。") from error
        except (URLError, TimeoutError) as error:
            raise RuntimeError("翻译服务暂不可用，请检查网络后重试。") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("翻译服务返回的数据无法识别。") from error

        if not isinstance(payload, dict) or payload.get("responseStatus") != 200:
            raise RuntimeError("翻译服务无法翻译这段岗位描述。")
        response_data = payload.get("responseData")
        translated = response_data.get("translatedText") if isinstance(response_data, dict) else None
        if not isinstance(translated, str) or not translated.strip():
            raise RuntimeError("翻译服务没有返回有效译文。")
        translated_chunks.append(html.unescape(translated).strip())
    return " ".join(translated_chunks)


def validate_job_fields(fields: Any, target_language: Any) -> int:
    if not isinstance(target_language, str) or target_language not in {"zh-CN", "en"}:
        raise ValueError("Unsupported target language")
    if not isinstance(fields, dict) or set(fields) != {"title", "description", "location", "category", "job_type", "tags"}:
        raise ValueError("Invalid job fields")
    if not isinstance(fields["title"], str) or len(fields["title"]) > 300:
        raise ValueError("Job title is invalid")
    for key in ("description", "location", "category", "job_type"):
        if not isinstance(fields[key], str) or len(fields[key]) > MAX_TRANSLATION_FIELD_CHARS:
            raise ValueError("Job details are invalid or too long")
    if not isinstance(fields["tags"], list) or len(fields["tags"]) > 12:
        raise ValueError("Job tags are invalid")
    if any(not isinstance(tag, str) or len(tag) > 100 for tag in fields["tags"]):
        raise ValueError("Job tags are invalid")
    total_chars = sum(
        len(value) if isinstance(value, str) else sum(len(tag) for tag in value)
        for value in fields.values()
    )
    if total_chars > MAX_TRANSLATION_TOTAL_CHARS:
        raise ValueError("Job details exceed the translation character limit")

    return total_chars


def translate_job_fields(fields: Any, target_language: Any) -> dict[str, Any]:
    total_chars = validate_job_fields(fields, target_language)
    translated_fields: dict[str, Any] = {}
    for key, value in fields.items():
        if isinstance(value, list):
            translated_fields[key] = [translate_text(tag, target_language) if tag.strip() else tag for tag in value]
        else:
            translated_fields[key] = translate_text(value, target_language) if value.strip() else value
    return {"fields": translated_fields, "characters_used": total_chars}


class PublicJobsCache:
    def __init__(
        self,
        loader: Callable[[], dict[str, Any]] = fetch_remote_jobs,
        ttl_seconds: int = CACHE_SECONDS,
    ) -> None:
        self._loader = loader
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._payload: dict[str, Any] | None = None
        self._expires_at = 0.0
        self._fetched_at = 0

    def get(self, now: float | None = None) -> tuple[dict[str, Any], bool, int]:
        current = time.monotonic() if now is None else now
        with self._lock:
            if self._payload is not None and current < self._expires_at:
                return self._payload, True, self._fetched_at
            payload = self._loader()
            if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
                raise RuntimeError("岗位来源返回的数据格式无法识别")
            self._payload = payload
            self._expires_at = current + self._ttl_seconds
            self._fetched_at = int(time.time() * 1000)
            return payload, False, self._fetched_at


feed_cache = PublicJobsCache()


class AppRequestHandler(BaseHTTPRequestHandler):
    server_version = "Shitu"
    sys_version = ""

    def _expected_host(self) -> str:
        configured_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
        external_url = os.environ.get("RENDER_EXTERNAL_URL")
        if configured_host:
            return configured_host
        if external_url:
            return urlsplit(external_url).netloc
        return f"127.0.0.1:{self.server.server_port}"

    def _allowed_origins(self) -> set[str]:
        local_origin = f"http://127.0.0.1:{self.server.server_port}"
        configured = os.environ.get("ALLOWED_ORIGINS", "")
        return {local_origin, *(origin.strip() for origin in configured.split(",") if origin.strip())}

    def _valid_host(self) -> bool:
        return self.headers.get("Host") == self._expected_host()

    def _validate_origin(self, *, required: bool = False) -> bool:
        origin = self.headers.get("Origin")
        if origin is None and not required:
            return True
        if origin in self._allowed_origins():
            return True
        self._send_json(403, {"error": "Invalid Origin"})
        return False

    def _security_headers(self) -> None:
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; "
            "object-src 'none'; frame-ancestors 'none'",
        )
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self._security_headers()
        origin = self.headers.get("Origin")
        if origin in self._allowed_origins():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body)

    def do_GET(self) -> None:
        if not self._valid_host():
            self._send_json(403, {"error": "Invalid Host"})
            return
        request_path = urlsplit(self.path)
        if request_path.path == "/api/jobs":
            if not self._validate_origin():
                return
            if request_path.query:
                self._send_json(400, {"error": "搜索参数不被接受；岗位仅在浏览器本地匹配。"})
                return
            try:
                payload, cached, fetched_at = feed_cache.get()
            except RuntimeError as error:
                self._send_json(503, {"error": str(error)})
                return
            self._send_json(200, {**payload, "fetched_at": fetched_at, "cached": cached})
            return

        asset = ASSETS.get(request_path.path)
        if asset is None or request_path.query:
            self._send(404, "text/plain; charset=utf-8", b"Not found")
            return
        filename, content_type = asset
        try:
            body = (ROOT / filename).read_bytes()
        except OSError:
            self._send(500, "text/plain; charset=utf-8", b"Unable to read application asset")
            return
        self._send(200, content_type, body)

    def do_POST(self) -> None:
        if not self._valid_host():
            self._send_json(403, {"error": "Invalid Host"})
            return
        if urlsplit(self.path).path == "/api/jobs":
            self._send_json(405, {"error": "POST is not supported"})
            return
        if urlsplit(self.path).path != "/api/translate" or urlsplit(self.path).query:
            self._send_json(404, {"error": "Not found"})
            return
        if not self._validate_origin(required=True):
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._send_json(415, {"error": "Content-Type must be application/json"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if content_length <= 0 or content_length > MAX_TRANSLATION_BODY_BYTES:
            self._send_json(413, {"error": "Translation request is too large"})
            return
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Invalid JSON"})
            return
        if not isinstance(payload, dict) or set(payload) != {"fields", "target_language"}:
            self._send_json(400, {"error": "Invalid translation request"})
            return
        try:
            validate_job_fields(payload["fields"], payload["target_language"])
            translated = translate_job_fields(payload["fields"], payload["target_language"])
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return
        except RuntimeError as error:
            self._send_json(502, {"error": str(error)})
            return
        self._send_json(200, {**translated, "provider": "MyMemory"})

    def do_OPTIONS(self) -> None:
        if not self._valid_host():
            self._send_json(403, {"error": "Invalid Host"})
            return
        if urlsplit(self.path).path != "/api/translate" or urlsplit(self.path).query:
            self._send_json(404, {"error": "Not found"})
            return
        if not self._validate_origin(required=True):
            return
        if self.headers.get("Access-Control-Request-Method") != "POST":
            self._send_json(405, {"error": "Method is not allowed"})
            return
        requested_headers = {
            header.strip().lower()
            for header in self.headers.get("Access-Control-Request-Headers", "").split(",")
            if header.strip()
        }
        if not requested_headers.issubset({"content-type", "accept"}):
            self._send_json(403, {"error": "Request headers are not allowed"})
            return
        self.send_response(204)
        self._security_headers()
        self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.command} {urlsplit(self.path).path} - {args[1] if len(args) > 1 else 'request'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Shitu job-search app on this computer only.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (keep 127.0.0.1 for local use)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")), help="Web port (default: 8765)")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AppRequestHandler)
    server.daemon_threads = True
    print(f"拾途已启动，仅本机可访问：http://127.0.0.1:{args.port}/")
    print("按 Ctrl+C 停止。浏览器条件不会发送到岗位 API。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止拾途。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
