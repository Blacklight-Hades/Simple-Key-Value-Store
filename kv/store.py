class Record:
    """One entry in the store."""

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.expires_at = None  # used later for EXPIRE/TTL


class Index:
    """A simple list of records, scanned linearly."""

    def __init__(self):
        self._records = []

    def find(self, key):
        """Return the Record for key, or None."""
        for record in self._records:
            if record.key == key:
                return record
        return None

    def put(self, key, value):
        """Insert or overwrite. Last write wins."""
        record = self.find(key)
        if record is not None:
            record.value = value
            record.expires_at = None
        else:
            self._records.append(Record(key, value))

    def remove(self, key):
        """Delete key. Return True if it existed."""
        for i, record in enumerate(self._records):
            if record.key == key:
                del self._records[i]
                return True
        return False

    def keys(self):
        return [r.key for r in self._records]

    def clear(self):
        self._records = []

