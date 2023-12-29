

class Token:
    def __init__(self, token, uniswapPair):
        self.token = token
        #self.hash = token.address??? TODO
        self.uniswapPair = uniswapPair
    
    def getPriceForSpecificAmount(self, amount) -> int:
        pass

    def getAmountForSpecificPrice(self, price) -> int: #tener en cuenta la conversion a decimales y esas weas aca TODO!
        pass

    def getAvailableAmount(self) -> int:
        pass

    def __hash__(self) -> int:
        pass

    def __eq__(self, __value: object) -> bool:
        pass

class Position:
    def __init__(self, token, amount, price):
        self.token = token
        self.amount = amount
        self.ethPutIn = amount * price  # TODO watch out for the decimals!!!
        self.ethGottenOut = 0

    def increasePosition(self, amount, price):
        self.ethPutIn += amount * price  # TODO watch out for the decimals!!!
        self.amount += amount

    def reducePosition(self, amount, price):
        self.ethGottenOut += amount * price  # TODO watch out for the decimals!!!
        self.amount -= amount
    
    def getPositionValue(self, considerResidue: bool):
        residualValue = 0
        residualAmount = self.amount
        if residualAmount > 0 and considerResidue:
            try:
                residualValue = self.token.getPriceForSpecificAmount(residualAmount) * residualAmount
                residualAmount = 0
            except:
                availableAmount = self.token.getAvailableAmount()
                residualValue = self.token.getPriceForSpecificAmount(availableAmount) * availableAmount
                residualAmount -= availableAmount
        return ((self.ethGottenOut + residualValue) - self.ethPutIn, residualAmount)

class PositionCollection:
    def __init__(self):
        self.positions = {}
    
    def increasePosition(self, token, amount, price):
        if token in self.positions:
            self.positions[token].increasePosition(amount, price)
        else:
            self.positions[token] = Position(token, amount, price)
    
    def reducePosition(self, token, amount, price) -> bool:
        if token in self.positions:
            self.positions[token].reducePosition(amount, price)
            return True
        else:
            return False
    
    def getBalance(self, considerResidues: bool):
        outputBalance = 0
        for _, position in self.positions.items():
            outputBalance += position.getPositionValue(considerResidues)

#despues sumar el gas distinguiendo por transaccion y no por swap, y tener una comparativa de los movimientos capturados a tiempo