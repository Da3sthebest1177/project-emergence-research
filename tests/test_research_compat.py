import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from emergence.research import CRITIC, _ask

class GroqCompatTests(unittest.TestCase):
    def test_groq_400_strict_retries_json_object(self):
        answer = json.dumps({"critique":"limited results", "conclusion":"no gain", "next_question":"test harder"})
        bodies = []
        def fake_urlopen(req, timeout):
            body = json.loads(req.data)
            bodies.append(body)
            if len(bodies) == 1:
                raise HTTPError('https://api.groq.com/openai/v1/chat/completions', 400, 'schema error', {}, io.BytesIO(b'not exposed'))
            return io.BytesIO(json.dumps({"choices":[{"finish_reason":"stop", "message":{"content":answer}}]}).encode())
        env = {"EMERGENCE_API_KEY":"SENSITIVE_TEST", "EMERGENCE_API_BASE":"https://api.groq.com/openai/v1", "EMERGENCE_MODEL":"openai/gpt-oss-20b"}
        with patch.dict('os.environ', env), patch('emergence.research.request.urlopen', side_effect=fake_urlopen):
            result = _ask(CRITIC, "test")
        self.assertEqual(result["conclusion"], "no gain")
        self.assertEqual(bodies[0]["response_format"]["type"], "json_schema")
        self.assertEqual(bodies[1]["response_format"], {"type":"json_object"})
        self.assertNotIn("reasoning_effort", bodies[1])

    def test_429_not_retried_as_json_error(self):
        calls = []
        def fake_urlopen(req, timeout):
            calls.append(req)
            raise HTTPError('https://api.groq.com/openai/v1/chat/completions', 429, 'rate', {}, io.BytesIO(b'private body'))
        env={"EMERGENCE_API_KEY":"SECRET", "EMERGENCE_API_BASE":"https://api.groq.com/openai/v1", "EMERGENCE_MODEL":"openai/gpt-oss-20b"}
        with patch.dict('os.environ', env), patch('emergence.research.request.urlopen', side_effect=fake_urlopen):
            with self.assertRaises(HTTPError) as raised:
                _ask(CRITIC, "test")
        self.assertEqual(raised.exception.code, 429)
        self.assertEqual(len(calls), 1)

if __name__ == '__main__': unittest.main()
