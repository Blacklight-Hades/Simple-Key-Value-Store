from kv.commands import Database
from kv.store import Index


def make_db(tmp_path):
    return Database(Index(), str(tmp_path / "data.db"))


def test_set_get(tmp_path):
    db = make_db(tmp_path)
    assert db.execute("SET a hello world") == "OK"
    assert db.execute("GET a") == "hello world"


def test_missing_key(tmp_path):
    db = make_db(tmp_path)
    assert db.execute("GET nope") == "NULL"


def test_persistence_after_restart(tmp_path):
    db = make_db(tmp_path)
    db.execute("SET a 1")
    db.execute("DEL a")
    db.execute("SET b 2")

    db2 = make_db(tmp_path)  # new process, same file
    db2.replay()
    assert db2.execute("GET a") == "NULL"
    assert db2.execute("GET b") == "2"


def test_mset_mget(tmp_path):
    db = make_db(tmp_path)
    db.execute("MSET a 1 b 2")
    assert db.execute("MGET a b c") == "1\n2\nNULL"

def test_ttl_survives_restart(tmp_path):
    db = make_db(tmp_path)
    db.execute("SET a 1")
    db.execute("EXPIRE a 100")
    assert 98 <= int(db.execute("TTL a")) <= 100

    db2 = make_db(tmp_path)
    db2.replay()
    assert 90 <= int(db2.execute("TTL a")) <= 100


def test_ttl_missing_and_no_expiry(tmp_path):
    db = make_db(tmp_path)
    assert db.execute("TTL nope") == "-2"
    db.execute("SET a 1")
    assert db.execute("TTL a") == "-1"