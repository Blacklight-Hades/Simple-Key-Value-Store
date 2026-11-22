from kv.store import Index


def test_put_and_find():
    idx = Index()
    idx.put("a", "1")
    assert idx.find("a").value == "1"


def test_overwrite_last_write_wins():
    idx = Index()
    idx.put("a", "1")
    idx.put("a", "2")
    assert idx.find("a").value == "2"
    assert len(idx.keys()) == 1


def test_remove():
    idx = Index()
    idx.put("a", "1")
    assert idx.remove("a") is True
    assert idx.find("a") is None
    assert idx.remove("a") is False