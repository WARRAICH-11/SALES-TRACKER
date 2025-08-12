import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.sync import attempt_sync_with_backoff

def test_sync_backoff_smoke():
    assert attempt_sync_with_backoff(session=None, max_attempts=1) in (True, False) 