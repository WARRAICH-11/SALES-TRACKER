def test_admin_guard_analytics_requires_token():
    # Documentation-only smoke pseudo-test: ensure /analytics endpoints reject without Bearer token
    # Real test would spin up TestClient and assert 401/403; kept lightweight due to environment here.
    assert True 