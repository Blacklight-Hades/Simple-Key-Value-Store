"""Parse and execute commands."""

import time

from kv import log

WRONGTYPE = "ERR wrong type"


class Database:
    def __init__(self, index, log_path=log.LOG_FILE):
        self.index = index
        self.log_path = log_path
        self._tx_buffer = None  # None means no transaction is active
        self._tx_snapshot = None

    def replay(self):
        """Rebuild the index from data.db. Nothing is re-written to the log."""
        for line in log.read_all(self.log_path):
            self.execute(line, persist=False)

    def execute(self, line, persist=True):
        """Run one command line and return the output string (or None)."""
        line = line.strip()
        parts = line.split(" ")
        cmd = parts[0].upper()

        if cmd == "SET":
            # Split on the first two spaces only, so values can contain spaces.
            pieces = line.split(" ", 2)
            if len(pieces) != 3:
                return "ERR wrong number of arguments"
            self.index.put(pieces[1], pieces[2])
            self._persist(line, persist)
            return "OK"

        if cmd == "GET":
            if len(parts) != 2:
                return "ERR wrong number of arguments"
            record = self._live_record(parts[1])
            if record is None:
                return "NULL"
            if record.kind != "string":
                return WRONGTYPE
            return record.value

        if cmd == "DEL":
            if len(parts) != 2:
                return "ERR wrong number of arguments"
            removed = self.index.remove(parts[1])
            if removed:
                self._persist(line, persist)
            return "1" if removed else "0"

        if cmd == "EXISTS":
            if len(parts) != 2:
                return "ERR wrong number of arguments"
            return "1" if self._live_record(parts[1]) else "0"

        if cmd == "MSET":
            pairs = parts[1:]
            if len(pairs) == 0 or len(pairs) % 2 != 0:
                return "ERR wrong number of arguments"
            for i in range(0, len(pairs), 2):
                self.index.put(pairs[i], pairs[i + 1])
            self._persist(line, persist)
            return "OK"

        if cmd == "MGET":
            if len(parts) < 2:
                return "ERR wrong number of arguments"
            results = []
            for key in parts[1:]:
                record = self._live_record(key)
                results.append(record.value if record else "NULL")
            return "\n".join(results)

        if cmd == "EXPIRE":
            if len(parts) != 3:
                return "ERR wrong number of arguments"
            try:
                seconds = float(parts[2])
            except ValueError:
                return "ERR invalid seconds"
            record = self._live_record(parts[1])
            if record is None:
                return "0"
            deadline = time.time() + seconds
            record.expires_at = deadline
            # Log the absolute deadline so replay doesn't restart the clock.
            self._persist("PEXPIREAT %s %s" % (parts[1], deadline), persist)
            return "1"

        if cmd == "PEXPIREAT":
            # Internal command written by EXPIRE; used during replay.
            record = self.index.find(parts[1])
            if record is not None:
                record.expires_at = float(parts[2])
            return "1"

        if cmd == "TTL":
            if len(parts) != 2:
                return "ERR wrong number of arguments"
            record = self._live_record(parts[1])
            if record is None:
                return "-2"
            if record.expires_at is None:
                return "-1"
            return str(int(record.expires_at - time.time()))

        if cmd == "RANGE":
            if len(parts) != 3:
                return "ERR wrong number of arguments"
            live = []
            for key in self.index.range_keys(parts[1], parts[2]):
                if self._live_record(key) is not None:
                    live.append(key)
            return "\n".join(live)

        if cmd == "BEGIN":
            if self._tx_buffer is not None:
                return "ERR transaction already active"
            self._tx_buffer = []
            self._tx_snapshot = self.index.snapshot()
            return "OK"

        if cmd == "COMMIT":
            if self._tx_buffer is None:
                return "ERR no transaction"
            for buffered in self._tx_buffer:
                log.append(buffered, self.log_path)
            self._tx_buffer = None
            self._tx_snapshot = None
            return "OK"

        if cmd == "ABORT":
            if self._tx_buffer is None:
                return "ERR no transaction"
            self.index.restore(self._tx_snapshot)
            self._tx_buffer = None
            self._tx_snapshot = None
            return "OK"

        if cmd == "HSET":
            pieces = line.split(" ", 3)
            if len(pieces) != 4:
                return "ERR wrong number of arguments"
            record = self.index.get_or_create(pieces[1], "hash")
            if record is None:
                return WRONGTYPE
            for pair in record.value:
                if pair[0] == pieces[2]:
                    pair[1] = pieces[3]
                    break
            else:
                record.value.append([pieces[2], pieces[3]])
            self._persist(line, persist)
            return "OK"

        if cmd == "HGET":
            if len(parts) != 3:
                return "ERR wrong number of arguments"
            record = self._live_record(parts[1])
            if record is None:
                return "NULL"
            if record.kind != "hash":
                return WRONGTYPE
            for pair in record.value:
                if pair[0] == parts[2]:
                    return pair[1]
            return "NULL"

        if cmd == "HGETALL":
            if len(parts) != 2:
                return "ERR wrong number of arguments"
            record = self._live_record(parts[1])
            if record is None:
                return ""
            if record.kind != "hash":
                return WRONGTYPE
            lines = []
            for pair in record.value:
                lines.append(pair[0])
                lines.append(pair[1])
            return "\n".join(lines)

        if cmd in ("LPUSH", "RPUSH"):
            pieces = line.split(" ", 2)
            if len(pieces) != 3:
                return "ERR wrong number of arguments"
            record = self.index.get_or_create(pieces[1], "list")
            if record is None:
                return WRONGTYPE
            if cmd == "LPUSH":
                record.value.insert(0, pieces[2])
            else:
                record.value.append(pieces[2])
            self._persist(line, persist)
            return str(len(record.value))

        if cmd == "LRANGE":
            if len(parts) != 4:
                return "ERR wrong number of arguments"
            try:
                start = int(parts[2])
                stop = int(parts[3])
            except ValueError:
                return "ERR value is not an integer"
            record = self._live_record(parts[1])
            if record is None:
                return ""
            if record.kind != "list":
                return WRONGTYPE
            size = len(record.value)
            # Negative indexes count from the end (-1 is the last element).
            if start < 0:
                start = max(size + start, 0)
            if stop < 0:
                stop = size + stop
            stop = min(stop, size - 1)
            if start > stop:
                return ""
            return "\n".join(record.value[start:stop + 1])

        return "ERR unknown command"

    def _persist(self, line, persist):
        """Append a write to data.db, or buffer it inside a transaction."""
        if not persist:
            return
        if self._tx_buffer is not None:
            self._tx_buffer.append(line)
        else:
            log.append(line, self.log_path)

    def _live_record(self, key):
        """Return the record for key, deleting it first if it has expired."""
        record = self.index.find(key)
        if record is None:
            return None
        if record.expires_at is not None and time.time() >= record.expires_at:
            self.index.remove(key)
            return None
        return record