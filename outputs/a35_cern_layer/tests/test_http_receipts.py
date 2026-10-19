"""Network-boundary doubles; real HTTPError handling and diagnostic preservation."""
import base64
from email.message import Message
import hashlib
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from sl_constraints.collider.sources import acquire_public


class HttpReceiptTests(unittest.TestCase):
    def test_forbidden_response_retained_not_empty_success(self):
        body = b'<html>Forbidden - request blocked</html>'
        headers = Message(); headers['Content-Type'] = 'text/html'; headers['Server'] = 'edge'
        error = HTTPError('https://www.hepdata.net/record/123?format=json', 403, 'Forbidden', headers, io.BytesIO(body))
        with patch('urllib.request.OpenerDirector.open', side_effect=error):
            raw, receipt = acquire_public(error.url)
        self.assertIsNone(raw)
        self.assertEqual(receipt['status'], 'SOURCE_UNAVAILABLE')
        self.assertEqual(receipt.get('http_status'), 403)
        self.assertEqual(receipt['error_message'], 'Forbidden')
        self.assertEqual(base64.b64decode(receipt['error_response_base64']), body)
        self.assertEqual(receipt['error_response_sha256'], hashlib.sha256(body).hexdigest())
        self.assertFalse(receipt['error_response_truncated'])

    def test_rate_limit_retry_after_preserved(self):
        headers = Message(); headers['Retry-After'] = '60'
        error = HTTPError('https://www.hepdata.net/record/123', 429, 'Too Many Requests', headers, io.BytesIO(b'Rate limited'))
        with patch('urllib.request.OpenerDirector.open', side_effect=error):
            _, receipt = acquire_public(error.url)
        self.assertEqual(receipt.get('http_status'), 429)
        self.assertEqual(receipt['response_headers']['retry-after'], '60')

    def test_timeout_is_distinct_from_http_error(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=TimeoutError('synthetic timeout')):
            raw, receipt = acquire_public('https://www.hepdata.net/record/123')
        self.assertIsNone(raw)
        self.assertEqual(receipt['error_class'], 'TimeoutError')
        self.assertIn('http_status', receipt)
        self.assertIsNone(receipt['http_status'])


if __name__ == '__main__':
    unittest.main()
