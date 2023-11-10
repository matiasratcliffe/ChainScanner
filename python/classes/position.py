from datetime import datetime


class Token:
    def __init__(self):
        pass

class Position:
    def __init__(self):
        self.token = Token()
        self.buyTime = datetime.now()
        self.buyPrice = 0