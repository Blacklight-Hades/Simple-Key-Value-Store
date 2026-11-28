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
def test_range(tmp_path):
    db = make_db(tmp_path)
    db.execute("MSET a 1 c 3 b 2 z 26")
    assert db.execute("RANGE a c") == "a\nb\nc"


def test_transaction_commit(tmp_path):
    db = make_db(tmp_path)
    db.execute("BEGIN")
    db.execute("SET a 1")
    assert db.execute("GET a") == "1"
    db.execute("COMMIT")

    db2 = make_db(tmp_path)
    db2.replay()
    assert db2.execute("GET a") == "1"


def test_transaction_abort(tmp_path):
    db = make_db(tmp_path)
    db.execute("SET a 1")
    db.execute("BEGIN")
    db.execute("SET a 2")
    db.execute("DEL a")
    db.execute("ABORT")
    assert db.execute("GET a") == "1"

    db2 = make_db(tmp_path)
    db2.replay()
    assert db2.execute("GET a") == "1"

def test_hash_commands(tmp_path):
    db = make_db(tmp_path)
    db.execute("HSET user name Hades")
    db.execute("HSET user school UNT")
    db.execute("HSET user name Hades Z")
    assert db.execute("HGET user name") == "Hades Z"
    assert db.execute("HGET user nope") == "NULL"
    assert db.execute("HGETALL user") == "name\nHades Z\nschool\nUNT"

    db2 = make_db(tmp_path)
    db2.replay()
    assert db2.execute("HGET user school") == "UNT"


def test_list_commands(tmp_path):
    db = make_db(tmp_path)
    db.execute("RPUSH l b")
    db.execute("RPUSH l c")
    db.execute("LPUSH l a")
    assert db.execute("LRANGE l 0 -1") == "a\nb\nc"
    assert db.execute("LRANGE l 1 1") == "b"

    db2 = make_db(tmp_path)
    db2.replay()
    assert db2.execute("LRANGE l 0 -1") == "a\nb\nc"


def test_wrong_type(tmp_path):
    db = make_db(tmp_path)
    db.execute("HSET h f v")
    assert db.execute("GET h") == "ERR wrong type"
    db.execute("RPUSH l x")
    assert db.execute("HGET l f") == "ERR wrong type"

def test_incr_decr(tmp_path):
    db = make_db(tmp_path)
    assert db.execute("INCR n") == "1"
    assert db.execute("INCR n") == "2"
    assert db.execute("DECR n") == "1"
    db.execute("SET word hello")
    assert db.execute("INCR word") == "ERR value is not an integer"

    db2 = make_db(tmp_path)
    db2.replay()
    assert db2.execute("GET n") == "1"


def test_flushdb(tmp_path):
    db = make_db(tmp_path)
    db.execute("MSET a 1 b 2")
    db.execute("HSET h f v")
    assert db.execute("FLUSHDB") == "OK"
    assert db.execute("GET a") == "NULL"

    db2 = make_db(tmp_path)
    db2.replay()
    assert db2.execute("GET a") == "NULL"
    assert db2.execute("EXISTS h") == "0"