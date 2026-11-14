import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
from utils.polling_health import PollingHealthRequest
class PollingHealthTests(unittest.IsolatedAsyncioTestCase):
 async def test_only_successful_polls_refresh_health_and_errors_do_not_break_polling(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'bot-health.json'
   request=PollingHealthRequest(path)
   with patch('telegram.request.HTTPXRequest.do_request',new_callable=AsyncMock) as base:
    base.return_value=(500,b'{"ok":false}')
    await request.do_request(url='unused',method='POST');self.assertFalse(path.exists())
    base.return_value=(200,b'{"ok":true,"result":[]}')
    await request.do_request(url='unused',method='POST')
    value=json.loads(path.read_text());self.assertGreater(value['lastSuccessAt'],0)
    path.unlink();request.health_path=Path(directory)/'missing'/'bot-health.json';request.last_written=0
    self.assertEqual((await request.do_request(url='unused',method='POST'))[0],200)
   await request.shutdown()
