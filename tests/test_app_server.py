import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app_server


class FakeTranslationResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return json.dumps({
            "responseStatus": 200,
            "responseData": {"translatedText": "译文"},
        }).encode("utf-8")


class PublicJobsCacheTests(unittest.TestCase):
    def test_cache_reuses_upstream_payload_until_expiry(self):
        calls = []
        payload = {"jobs": [{"id": 1}]}
        cache = app_server.PublicJobsCache(loader=lambda: calls.append(True) or payload, ttl_seconds=60)

        first, first_cached, first_fetched_at = cache.get(now=100)
        second, second_cached, second_fetched_at = cache.get(now=159)
        third, third_cached, third_fetched_at = cache.get(now=160)

        self.assertIs(first, payload)
        self.assertIs(second, payload)
        self.assertIs(third, payload)
        self.assertEqual((first_cached, second_cached, third_cached), (False, True, False))
        self.assertGreater(first_fetched_at, 0)
        self.assertEqual(first_fetched_at, second_fetched_at)
        self.assertGreater(third_fetched_at, 0)
        self.assertEqual(len(calls), 2)

    def test_cache_rejects_unexpected_payload(self):
        cache = app_server.PublicJobsCache(loader=lambda: {"unexpected": []})
        with self.assertRaisesRegex(RuntimeError, "数据格式无法识别"):
            cache.get(now=10)

    def test_translation_splits_requests_within_provider_byte_limit(self):
        text = ("This is a complete English sentence for translation. " * 20).strip()
        chunks = app_server.split_translation_chunks(text)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk.encode("utf-8")) <= app_server.MAX_TRANSLATION_CHUNK_BYTES for chunk in chunks))

        with patch("app_server.urlopen", return_value=FakeTranslationResponse()) as mocked_urlopen:
            translated = app_server.translate_text(text, "zh-CN")

        self.assertEqual(translated, " ".join(["译文"] * len(chunks)))
        self.assertEqual(mocked_urlopen.call_count, len(chunks))
        first_request = mocked_urlopen.call_args_list[0].args[0]
        self.assertTrue(first_request.full_url.startswith(app_server.TRANSLATION_URL + "?"))
        self.assertIn("langpair=en%7Czh-CN", first_request.full_url)

    def test_translation_skips_provider_when_text_already_matches_language(self):
        with patch("app_server.urlopen") as mocked_urlopen:
            self.assertEqual(app_server.translate_text("你好", "zh-CN"), "你好")
        mocked_urlopen.assert_not_called()

    def test_translation_validates_language_and_input_length(self):
        with self.assertRaises(ValueError):
            app_server.translate_text("Hello", "fr")
        with self.assertRaises(ValueError):
            app_server.translate_text("x" * (app_server.MAX_TRANSLATION_FIELD_CHARS + 1), "zh-CN")

    def test_translation_validates_full_job_fields(self):
        fields = {
            "title": "Designer",
            "description": "Build accessible products.",
            "location": "Worldwide",
            "category": "Design",
            "job_type": "Full-time",
            "tags": ["Figma", "Research"],
        }
        expected_chars = sum(
            len(value) if isinstance(value, str) else sum(map(len, value))
            for value in fields.values()
        )
        self.assertEqual(app_server.validate_job_fields(fields, "zh-CN"), expected_chars)
        with self.assertRaises(ValueError):
            app_server.validate_job_fields({"title": "Designer"}, "zh-CN")
        with self.assertRaises(ValueError):
            app_server.validate_job_fields(fields, ["zh-CN"])
        with self.assertRaises(ValueError):
            app_server.validate_job_fields(
                {**fields, "description": "x" * (app_server.MAX_TRANSLATION_FIELD_CHARS + 1)},
                "zh-CN",
            )
        long_fields = {**fields, "description": "x" * 8000}
        self.assertEqual(app_server.validate_job_fields(long_fields, "zh-CN"), 8000 + sum(
            len(value) if isinstance(value, str) else sum(map(len, value))
            for key, value in long_fields.items()
            if key != "description"
        ))

class AppServerSecurityTests(unittest.TestCase):
    def setUp(self):
        self.original_cache = app_server.feed_cache
        app_server.feed_cache = app_server.PublicJobsCache(
            loader=lambda: {"jobs": [{"id": 1, "title": "Example"}]}
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app_server.AppRequestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        app_server.feed_cache = self.original_cache

    def test_same_origin_api_and_security_headers(self):
        with urlopen(f"{self.base_url}/api/jobs") as response:
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
            self.assertIn("connect-src 'self'", response.headers["Content-Security-Policy"])
            self.assertEqual(payload["jobs"][0]["title"], "Example")
            self.assertFalse(payload["cached"])
            self.assertGreater(payload["fetched_at"], 0)

    def test_pages_origin_cors_and_translation_preflight(self):
        pages_origin = "https://dan-hua.github.io"
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": pages_origin}):
            request = Request(f"{self.base_url}/api/jobs", headers={"Origin": pages_origin})
            with urlopen(request) as response:
                self.assertEqual(response.headers["Access-Control-Allow-Origin"], pages_origin)

            preflight = Request(
                f"{self.base_url}/api/translate",
                method="OPTIONS",
                headers={
                    "Origin": pages_origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type, accept",
                },
            )
            with urlopen(preflight) as response:
                self.assertEqual(response.status, 204)
                self.assertEqual(response.headers["Access-Control-Allow-Origin"], pages_origin)
                self.assertEqual(response.headers["Access-Control-Allow-Methods"], "POST, OPTIONS")

        bad_origin = Request(
            f"{self.base_url}/api/jobs",
            headers={"Origin": "https://untrusted.example"},
        )
        with self.assertRaises(HTTPError) as rejected:
            urlopen(bad_origin)
        self.assertEqual(rejected.exception.code, 403)

    def test_hosted_api_accepts_configured_render_hostname(self):
        origin = "https://dan-hua.github.io"
        with patch.dict(
            os.environ,
            {
                "ALLOWED_ORIGINS": origin,
                "RENDER_EXTERNAL_URL": "https://shitu-api.onrender.com",
            },
        ):
            request = Request(
                f"{self.base_url}/api/jobs",
                headers={"Host": "shitu-api.onrender.com", "Origin": origin},
            )
            with urlopen(request) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)

    def test_server_rejects_search_queries_and_unlisted_files(self):
        invalid_host = Request(f"{self.base_url}/", headers={"Host": "untrusted.example"})
        with self.assertRaises(HTTPError) as rejected_host:
            urlopen(invalid_host)
        self.assertEqual(rejected_host.exception.code, 403)

        with self.assertRaises(HTTPError) as bad_query:
            urlopen(f"{self.base_url}/api/jobs?search=designer")
        self.assertEqual(bad_query.exception.code, 400)

        with self.assertRaises(HTTPError) as private_file:
            urlopen(f"{self.base_url}/README.md")
        self.assertEqual(private_file.exception.code, 404)

        request = Request(f"{self.base_url}/api/jobs", method="POST", data=b"{}")
        with self.assertRaises(HTTPError) as disallowed_method:
            urlopen(request)
        self.assertEqual(disallowed_method.exception.code, 405)

    def test_translation_requires_a_same_origin_explicit_post(self):
        payload = {
            "fields": {
                "title": "Product designer",
                "description": "Design useful products.",
                "location": "Worldwide",
                "category": "Design",
                "job_type": "Full-time",
                "tags": ["Research"],
            },
            "target_language": "zh-CN",
        }
        characters_used = app_server.validate_job_fields(payload["fields"], payload["target_language"])
        body = json.dumps(payload).encode("utf-8")
        bad_origin = Request(
            f"{self.base_url}/api/translate",
            data=body,
            headers={"Content-Type": "application/json", "Origin": "https://untrusted.example"},
        )
        with self.assertRaises(HTTPError) as rejected_origin:
            urlopen(bad_origin)
        self.assertEqual(rejected_origin.exception.code, 403)

        request = Request(
            f"{self.base_url}/api/translate",
            data=body,
            headers={"Content-Type": "application/json", "Origin": self.base_url},
        )
        with patch(
            "app_server.translate_job_fields",
            return_value={
                "fields": {
                    **payload["fields"],
                    "title": "产品设计师",
                    "description": "设计有用的产品。",
                    "location": "全球",
                    "category": "设计",
                    "job_type": "全职",
                    "tags": ["用户研究"],
                },
                "characters_used": characters_used,
            },
        ) as translate_mock:
            with urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(result["provider"], "MyMemory")
        self.assertEqual(result["fields"]["description"], "设计有用的产品。")
        self.assertEqual(result["fields"]["tags"], ["用户研究"])
        self.assertEqual(result["characters_used"], characters_used)
        translate_mock.assert_called_once_with(payload["fields"], "zh-CN")

    def test_translation_has_no_local_daily_character_cap(self):
        fields = {
            "title": "Designer",
            "description": "x" * 1500,
            "location": "",
            "category": "",
            "job_type": "",
            "tags": [],
        }
        body = json.dumps({"fields": fields, "target_language": "zh-CN"}).encode("utf-8")
        request_headers = {"Content-Type": "application/json", "Origin": self.base_url}
        with patch(
            "app_server.translate_job_fields",
            return_value={"fields": fields, "characters_used": 1508},
        ):
            for _ in range(4):
                request = Request(
                    f"{self.base_url}/api/translate",
                    data=body,
                    headers=request_headers,
                )
                with urlopen(request) as response:
                    self.assertEqual(response.status, 200)


if __name__ == "__main__":
    unittest.main()
