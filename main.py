import sys

from kv import log
from kv.commands import Database
from kv.store import Index


def main():
    log.ensure_log()
    db = Database(Index())
    db.replay()

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        if line.upper() == "EXIT":
            break
        result = db.execute(line)
        if result is not None:
            print(result, flush=True)


if __name__ == "__main__":
    main()