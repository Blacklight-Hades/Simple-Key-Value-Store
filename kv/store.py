class Record:
    """One entry in the store."""

    def __init__(self, key, value, kind="string"):
        self.key = key
        self.value = value
        self.kind = kind
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
            record.kind = "string"
            record.expires_at = None
        else:
            self._records.append(Record(key, value))

    def get_or_create(self, key, kind):
        """Return the record for key, creating an empty one of this kind.
        Returns None if the key exists with a different kind.
        """
        record = self.find(key)
        if record is None:
            empty = [] if kind in ("hash", "list") else ""
            record = Record(key, empty, kind)
            self._records.append(record)
            return record
        if record.kind != kind:
            return None
        return record

    def remove(self, key):
        """Delete key. Return True if it existed."""
        for i, record in enumerate(self._records):
            if record.key == key:
                del self._records[i]
                return True
        return False

    def keys(self):
        return [r.key for r in self._records]

    def range_keys(self, start, end):
        """Return keys with start <= key <= end, sorted lexicographically."""
        matches = [k for k in self.keys() if start <= k <= end]
        # Insertion sort, so we don't depend on a library structure.
        for i in range(1, len(matches)):
            current = matches[i]
            j = i - 1
            while j >= 0 and matches[j] > current:
                matches[j + 1] = matches[j]
                j -= 1
            matches[j + 1] = current
        return matches

    def clear(self):
        self._records = []

    def snapshot(self):
        """Return a deep copy of all records."""
        copies = []
        for r in self._records:
            if r.kind == "hash":
                value = [[pair[0], pair[1]] for pair in r.value]
            elif r.kind == "list":
                value = list(r.value)
            else:
                value = r.value
            c = Record(r.key, value, r.kind)
            c.expires_at = r.expires_at
            copies.append(c)
        return copies

    def restore(self, records):
        """Replace the current records with a previous snapshot."""
        self._records = records

