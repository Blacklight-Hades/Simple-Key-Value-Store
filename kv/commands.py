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
        parts = line.strip().split(" ", 2)
        cmd = parts[0].upper()

        if cmd == "SET" and len(parts) == 3:
            self.index.put(parts[1], parts[2])
            if persist:
                log.append(line.strip(), self.log_path)
            return "OK"

        if cmd == "GET" and len(parts) >= 2:
            record = self.index.find(parts[1])
            return record.value if record else "NULL"

        return "ERR unknown command"