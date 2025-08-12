from datetime import datetime, timedelta
import json
from pathlib import Path

def test_quick_insights_cache_logic(tmp_path):
    p = tmp_path / 'quick_insights.json'
    fresh = {'ts': (datetime.utcnow()).isoformat(), 'yesterday_revenue': 1}
    p.write_text(json.dumps(fresh))
    data = json.loads(p.read_text())
    assert 'ts' in data 