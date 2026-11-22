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
            record = self.index.find(parts[1])
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
            return "1" if self.index.find(parts[1]) else "0"

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
                record = self.index.find(key)
                results.append(record.value if record else "NULL")
            return "\n".join(results)

        return "ERR unknown command"

    def _persist(self, line, persist):
        """Append a successful write to data.db, unless we are replaying."""
        if persist:
            log.append(line, self.log_path)