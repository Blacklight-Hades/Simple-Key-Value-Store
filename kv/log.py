import os

LOG_FILE = "data.db"


def ensure_log(path=LOG_FILE):
    """Create the log file if it doesn't exist."""
    if not os.path.exists(path):
        open(path, "a").close()


def append(line, path=LOG_FILE):
    """Append one command line and force it onto disk immediately."""
    with open(path, "a") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_all(path=LOG_FILE):
    """Return every logged line, for replay on startup."""
    ensure_log(path)
    with open(path, "r") as f:
        return [line.rstrip("\n") for line in f if line.strip()]