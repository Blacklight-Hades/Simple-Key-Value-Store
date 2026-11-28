# Simple Key-Value Store

A persistent key-value store written in Python. It reads commands from
STDIN, writes results to STDOUT, and saves every write to an append-only
log (`data.db`) that is replayed on startup.

## Run

    python3 main.py

## Commands

SET, GET, DEL, EXISTS, MSET, MGET, EXPIRE, TTL, RANGE, BEGIN, COMMIT,
ABORT, HSET, HGET, HGETALL, LPUSH, RPUSH, LPOP, RPOP, LRANGE, INCR,
DECR, FLUSHDB, EXIT

## Test

    pip install -r requirements-dev.txt
    python -m pytest
    ruff check .

The in-memory index is a plain list of records scanned linearly, with no
built-in dict or map types.
