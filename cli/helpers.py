class SetQueue(dict):
    def __init__(self, capacity=10):
        super().__init__()
        self.capacity = capacity
        self.size = 0

    def add(self, item):
        # delete first to make sure it ends in last
        try:
            self.remove(item)
        except KeyError:
            pass
        self[item] = None
        self.size += 1
        self.truncate()

    def truncate(self, capacity=None):
        capacity = capacity or self.capacity
        while self.size > capacity:
            _f = next(iter(self.keys()))
            self.remove(_f)

    def remove(self, item):
        del self[item]
        self.size -= 1
