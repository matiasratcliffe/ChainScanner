import json
import etherscan
from web3 import Web3


class EVMInterface:
    lastCheckedBlockNumber = 18894135
    botContractAddress = "0x50B8f49f4B2E80e09cE8015C4e7A9c277738Fd3d"
    w3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/eth"))  # "https://ethereum.publicnode.com"
    uniswapRouter = w3.eth.contract(address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", abi=[
        {"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"reserveIn","type":"uint256"},{"internalType":"uint256","name":"reserveOut","type":"uint256"}],"name":"getAmountIn","outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"}],"stateMutability":"pure","type":"function"},
        {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"reserveIn","type":"uint256"},{"internalType":"uint256","name":"reserveOut","type":"uint256"}],"name":"getAmountOut","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"pure","type":"function"}
    ])
    etherscanClient = etherscan.Etherscan(api_key="397DG3PDX5BUT6XYMVIQE518NTZQT66BZ8")
    tokenABI = [{"constant": True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable": False,"stateMutability":"view","type":"function"},
            {"constant": True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable": False,"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
    pairABI = [{"constant": True, "inputs": [], "name": "token0", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
            {"constant": True, "inputs": [], "name": "token1", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
            {"constant": True,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable": False,"stateMutability":"view","type":"function"}]

    def getTokenContract(address):
        return EVMInterface.w3.eth.contract(address=EVMInterface.w3.to_checksum_address(address), abi=EVMInterface.tokenABI)
    
    def getPairContract(address):
        return EVMInterface.w3.eth.contract(address=EVMInterface.w3.to_checksum_address(address), abi=EVMInterface.pairABI)
    
    def setRPC(rpcAddress):
        EVMInterface.w3 = Web3(Web3(Web3.HTTPProvider(rpcAddress)))

class Token:
    def __init__(self, token, uniswapPair, decimals=None):
        self.token = token
        self.address = token.address
        self.uniswapPair = uniswapPair
        self.decimals = self.token.functions.decimals().call() if decimals == None else int(decimals)

    def getReserves(self) -> (int, int):
        _output = self.uniswapPair.functions.getReserves().call(block_identifier=EVMInterface.lastCheckedBlockNumber)
        return (_output[0], _output[1])

    def getAvailableAmount(self) -> int:
        return self.getReserves()[0]

    def get_amount_out(self, amount_in) -> int:
        amount_in = int(amount_in * (10**self.decimals))
        (reserve_in, reserve_out) = self.getReserves()
        assert amount_in > 0, 'INSUFFICIENT_INPUT_AMOUNT'
        assert reserve_in > 0 and reserve_out > 0, 'INSUFFICIENT_LIQUIDITY'
        
        amount_in_with_fee = amount_in * 997
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 1000) + amount_in_with_fee
        
        amount_out = numerator // denominator
        return amount_out / 1e18

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
        if self.amount == 0:
            return False
        if amount > self.amount:
            amount = self.amount
        self.ethGottenOut += amount * price  # TODO watch out for the decimals!!!
        self.amount -= amount
        return True
    
    def getBalance(self, considerResidue: bool) -> (float, float): #TODO o (float, int) ???
        residualValue = 0
        residualAmount = self.getAmount()
        if residualAmount > 0 and considerResidue:
            try:
                residualValue = self.token.get_amount_out(residualAmount)
                residualAmount = 0
            except Exception as e:
                print(f"Exception {e}")
                availableAmount = self.token.getAvailableAmount()
                residualValue = self.token.get_amount_out(availableAmount)
                residualAmount -= availableAmount
        return ((self.ethGottenOut + residualValue) - self.ethPutIn, residualAmount)
    
    def getValue(self, considerResidue: bool) -> (float, float): #TODO o (float, int) ???
        residualValue = 0
        residualAmount = self.getAmount()
        if residualAmount > 0 and considerResidue:
            try:
                residualValue = self.token.get_amount_out(residualAmount)
                residualAmount = 0
            except Exception as e:
                print(f"Exception {e}")
                availableAmount = self.token.getAvailableAmount()
                residualValue = self.token.get_amount_out(availableAmount)
                residualAmount -= availableAmount
        return ((self.ethGottenOut + residualValue), residualAmount)
    
    def getAmount(self) -> float:
        self.amount = int(self.amount * (10**self.token.decimals)) / (10**self.token.decimals)
        return self.amount

class PositionCollection:
    def __init__(self, serializedPositions: str = ""):
        self.positions = {}
        if len(serializedPositions) > 0:
            index = 0
            _positions = json.loads(serializedPositions)
            print(f"Initiating {len(_positions)} positions")
            for k, v in _positions.items():
                print(f"Processing position {index}")
                token = Token(token=EVMInterface.getTokenContract(v["token"]["address"]), uniswapPair=EVMInterface.getPairContract(v["token"]["uniswapPair"]), decimals=v["token"]["decimals"])
                self.positions[k] = Position(token, v["amount"], v["ethPutIn"], v["ethGottenOut"])
                index += 1
    
    def increasePosition(self, token, amount, price):
        if token in self.positions:
            self.positions[token.address].increasePosition(amount, price)
        else:
            self.positions[token.address] = Position(token)
            self.positions[token.address].increasePosition(amount, price)
    
    def reducePosition(self, token, amount, price) -> bool:
        if token.address in self.positions:
            return self.positions[token.address].reducePosition(amount, price)
        else:
            return False
    
    def getValue(self, considerResidues: bool) -> (float, list):
        value = 0
        collection = []
        print(f"Calculating the value of {len(self.positions)} positions")
        with open("positionValue.txt", "a") as f:
            f.write(f"-----------------------------------------------\n")
        for index, position in enumerate(self.positions.values()):
            positionValue = position.getValue(considerResidues)[0]
            print(f"Calculating the value of position {index}: {positionValue}")
            value += positionValue
            collection.append((index, positionValue))
            with open("positionValue.txt", "a") as f:
                f.write(f"{positionValue}\n")
        with open("positionValue.txt", "a") as f:
            f.write(f"-----------------------------------------------\n")
        return value, collection
    
    def getEarnings(self, considerResidues: bool) -> (float, list):
        earnings = 0
        collection = []
        print(f"Calculating the earnings of {len(self.positions)} positions")
        with open("positionEarnings.txt", "a") as f:
            f.write(f"-----------------------------------------------\n")
        for index, position in enumerate(self.positions.values()):
            positionEarnings = position.getBalance(considerResidues)[0]
            print(f"Calculating the earnings of position {index}: {positionEarnings}")
            earnings += positionEarnings
            collection.append((index, positionEarnings))
            with open("positionEarnings.txt", "a") as f:
                f.write(f"{positionEarnings}\n")
        with open("positionEarnings.txt", "a") as f:
            f.write(f"-----------------------------------------------\n")
        return earnings, collection
    
    def getInvestment(self) -> float:
        investment = 0
        for _, position in self.positions.items():
            investment += position.ethPutIn
        return investment
    
    def serialize(self) -> str:
        result = {}
        for k, v in self.positions.items():
            result[k] = {
                "token": {
                    "address": v.token.address,
                    "uniswapPair": v.token.uniswapPair.address,
                    "decimals": v.token.decimals
                },
                "amount": v.amount,
                "ethPutIn": v.ethPutIn,
                "ethGottenOut": v.ethGottenOut
            }
        return json.dumps(result)
    
    def __len__(self):
        return len(self.positions)
    
    def __getitem__(self, key):
        if isinstance(key, int):
            array = [v for v in self.positions.values()]
            return array[key]
        else:
            return self.positions[key]