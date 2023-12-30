

def get_amount_in(amount_out, reserve_in, reserve_out):
    assert amount_out > 0, 'INSUFFICIENT_OUTPUT_AMOUNT'
    assert reserve_in > 0 and reserve_out > 0, 'INSUFFICIENT_LIQUIDITY'

    numerator = reserve_in * amount_out * 1000
    denominator = (reserve_out - amount_out) * 997

    amount_in = (numerator // denominator) + 1
    return amount_in

class Token:
    def __init__(self, token, uniswapPair, uniswapRouter):
        self.uniswapRouter = uniswapRouter
        self.token = token
        self.address = token.address
        self.uniswapPair = uniswapPair
    
    def getPriceForSpecificAmount(self, amount) -> int:
        pass

    def getAmountForSpecificPrice(self, price) -> int: #tener en cuenta la conversion a decimales y esas weas aca TODO!
        pass

    def getReserves(self) -> (int, int):
        _output = self.uniswapPair.functions.getReserves().call()
        return (_output[0], _output[1])

    def __hash__(self) -> int:
        return hash(int(self.token.address, 16))

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, Token) and self.__hash__() == __value.__hash__()

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
            self.positions[token.address].increasePosition(amount, price)
        else:
            self.positions[token.address] = Position(token, amount, price)
    
    def reducePosition(self, token, amount, price) -> bool:
        if token in self.positions:
            self.positions[token.address].reducePosition(amount, price)
            return True
        else:
            return False
    
    def getBalance(self, considerResidues: bool):
        outputBalance = 0
        for _, position in self.positions.items():
            outputBalance += position.getPositionValue(considerResidues)

#despues sumar el gas distinguiendo por transaccion y no por swap, y tener una comparativa de los movimientos capturados a tiempo