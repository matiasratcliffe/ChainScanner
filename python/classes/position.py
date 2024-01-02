import json
import etherscan
from web3 import Web3


class EVMInterface:
    w3 = Web3(Web3.HTTPProvider("https://ethereum.publicnode.com"))
    uniswapRouter = w3.eth.contract(address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", abi=[{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsIn","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}])
    etherscanClient = etherscan.Etherscan(api_key="397DG3PDX5BUT6XYMVIQE518NTZQT66BZ8")
    tokenABI = [{"constant": True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable": False,"stateMutability":"view","type":"function"},
            {"constant": True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable": False,"stateMutability":"view","type":"function"}]
    pairABI = [{"constant": True, "inputs": [], "name": "token0", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
            {"constant": True, "inputs": [], "name": "token1", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
            {"constant": True,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable": False,"stateMutability":"view","type":"function"}]

    def getTokenContract(address):
        return EVMInterface.w3.eth.contract(address=EVMInterface.w3.to_checksum_address(address), abi=EVMInterface.tokenABI)
    
    def getPairContract(address):
        return EVMInterface.w3.eth.contract(address=EVMInterface.w3.to_checksum_address(address), abi=EVMInterface.pairABI)

class Token:
    def __init__(self, token, uniswapPair):
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

    def get_amount_in(self, amount_out, reserve_in, reserve_out):
        assert amount_out > 0, 'INSUFFICIENT_OUTPUT_AMOUNT'
        assert reserve_in > 0 and reserve_out > 0, 'INSUFFICIENT_LIQUIDITY'

        numerator = reserve_in * amount_out * 1000
        denominator = (reserve_out - amount_out) * 997

        amount_in = (numerator // denominator) + 1
        return amount_in

    def __hash__(self) -> int:
        return hash(int(self.token.address, 16))

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, Token) and self.__hash__() == __value.__hash__()

class Position:
    def __init__(self, token, amount=0, ethPutIn=0, ethGottenOut=0):
        self.token = token
        self.amount = amount
        self.ethPutIn = ethPutIn
        self.ethGottenOut = ethGottenOut

    def increasePosition(self, amount, price):
        self.ethPutIn += amount * price  # TODO watch out for the decimals!!!
        self.amount += amount

    def reducePosition(self, amount, price):
        self.ethGottenOut += amount * price  # TODO watch out for the decimals!!!
        self.amount -= amount
    
    def getPositionValue(self, considerResidue: bool) -> (float, float): #TODO o (float, int) ???
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
    
    def getPositionBalance(self, considerResidue: bool) -> (float, float): #TODO o (float, int) ???
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
        return ((self.ethGottenOut + residualValue), residualAmount)

class PositionCollection:
    def __init__(self, serializedPositions: str = ""):
        self.positions = {}
        if len(serializedPositions) > 0:
            _positions = json.loads(serializedPositions)
            for k, v in _positions.items():
                token = Token(token=EVMInterface.getTokenContract(v["token"]["address"]), uniswapPair=EVMInterface.getPairContract(v["token"]["uniswapPair"]))
                self.positions[k] = Position(token, v["amount"], v["ethPutIn"], v["ethGottenOut"])
    
    def increasePosition(self, token, amount, price):
        if token in self.positions:
            self.positions[token.address].increasePosition(amount, price)
        else:
            self.positions[token.address] = Position(token)
            self.positions[token.address].increasePosition(amount, price)
    
    def reducePosition(self, token, amount, price) -> bool:
        if token.address in self.positions:
            self.positions[token.address].reducePosition(amount, price)
            return True
        else:
            return False
    
    def getEarnings(self, considerResidues: bool) -> float:
        earnings = 0
        for _, position in self.positions.items():
            earnings += position.getPositionValue(considerResidues)[0]
        return earnings
    
    def getBalance(self, considerResidues: bool) -> float:
        balance = 0
        for _, position in self.positions.items():
            balance += position.getPositionBalance(considerResidues)[0]
        return balance
    
    def serialize(self) -> str:
        result = {}
        for k, v in self.positions.items():
            result[k] = {
                "token": {
                    "address": v.token.address,
                    "uniswapPair": v.token.uniswapPair.address
                },
                "amount": v.amount,
                "ethPutIn": v.ethPutIn,
                "ethGottenOut": v.ethGottenOut
            }
        return json.dumps(result)