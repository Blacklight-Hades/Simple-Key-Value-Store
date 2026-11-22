
import time
from kv import log

class Database:
    def __init__(self, index, log_path=log.LOG_FILE):
        self.index = index
        self.log_path = log_path

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
            return record.value if record else "NULL"

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

        return "ERR unknown command"

    def _persist(self, line, persist):
        """Append a successful write to data.db, unless we are replaying."""
        if persist:
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