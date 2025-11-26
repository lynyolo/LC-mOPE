from sortedcontainers import SortedList


class skipList:
    def __init__(self, logger):
        self.skip_list = SortedList()
        self.lower = None
        self.upper = None
        self.logger = logger
        self.N = 2000

    def insert(self, value):
        if value not in self.skip_list:
            self.skip_list.add(value)
            # 更新边界值
            self.lower = self.skip_list[0]
            self.upper = self.skip_list[-1]

    def search(self, value):
        if len(self.skip_list) < 2:
            return None, None

        if value < self.lower or value > self.upper:
            return None, None

        if value == self.lower or value == self.upper:
            return value, value

        idx = self.skip_list.bisect_left(value)

        left = self.skip_list[idx - 1] if idx > 0 else None
        right = self.skip_list[idx] if idx < len(self.skip_list) else None

        if left == value or right == value:
            return value, value

        return left, right