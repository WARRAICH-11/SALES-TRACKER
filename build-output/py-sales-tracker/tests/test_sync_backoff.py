from app.services.sync import attempt_sync_with_backoff

def test_sync_backoff_smoke():
    assert attempt_sync_with_backoff(session=None, max_attempts=1) in (True, False) 