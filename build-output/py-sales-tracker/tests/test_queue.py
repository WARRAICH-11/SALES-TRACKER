from app.services.sync import _read_queue, _write_queue, enqueue


def test_queue_roundtrip(tmp_path, monkeypatch):
    qp = tmp_path / 'offline_queue.json'
    monkeypatch.setenv('PYTHONHASHSEED', '0')
    from app.services import sync as s
    s.QUEUE_PATH = qp
    _write_queue([])
    assert _read_queue() == []
    enqueue('sale_created', {'sale_id': 1})
    q = _read_queue()
    assert q and q[0]['event_type'] == 'sale_created' 