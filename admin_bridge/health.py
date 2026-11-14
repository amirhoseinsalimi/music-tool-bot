"""Core-owned, bounded resource observations from the bridge container."""
import json
import os
import shutil
import time
from pathlib import Path


def observation():
    """Read storage and successful-poll timestamps without inspecting user files."""
    path = Path(os.getenv('DATA_DIR', '/data'))
    try:
        usage = shutil.disk_usage(path)
        storage = {'totalBytes': usage.total, 'usedBytes': usage.used, 'freeBytes': usage.free}
    except OSError:
        storage = None
    heartbeat = None
    try:
        value = json.loads((path/'bot-health.json').read_text())
        timestamp = value['lastSuccessAt']
        if type(timestamp) in (int, float) and 0 <= time.time()-timestamp < 7*86400:
            age = time.time() - timestamp
            heartbeat = {
                'lastSuccessAt': timestamp, 'ageSeconds': round(age),
                'status': 'healthy' if age < 90 else 'stale',
            }
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {
        'botHeartbeat': heartbeat, 'checkedAt': time.time(), 'database': 'reachable',
        'storage': storage,
        'storageScope': 'Filesystem backing bot data; not retained-file byte totals',
        'botProcess': 'not_monitored', 'hostResources': 'not_monitored',
    }
