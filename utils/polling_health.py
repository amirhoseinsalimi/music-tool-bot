"""Successful Telegram getUpdates observations; optional, no new polling loop."""
import json
import time
from pathlib import Path
from telegram.request import HTTPXRequest


class PollingHealthRequest(HTTPXRequest):
    def __init__(self,path,**kwargs):
        super().__init__(**kwargs)
        self.health_path=Path(path)
        self.started=time.time()
        self.last_written=0

    async def do_request(self,*args,**kwargs):
        result=await super().do_request(*args,**kwargs)
        now=time.time()
        if result[0]==200 and now-self.last_written>=15:
            try:
                if json.loads(result[1]).get('ok') is True:
                    temporary=self.health_path.with_suffix('.tmp')
                    temporary.write_text(json.dumps(dict(startedAt=self.started,lastSuccessAt=now)))
                    temporary.replace(self.health_path)
                    self.last_written=now
            except (OSError,ValueError,AttributeError):
                pass  # Observability must never interrupt Telegram updates.
        return result
