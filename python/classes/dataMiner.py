import pdb
import etherscan
from web3 import Web3
from position import PositionCollection, Token

# HASTA LA LINEA 672 DE CAPTURED2 INCLUIDA CONTANDO HEADERS

def getPairInfo(tokenInSymbol, tokenOutSymbol, transaccionHash):
    print(f"\tGetting Swap Logs...", end="")
    swapLogs = [log for log in client.get_proxy_transaction_receipt(transaccionHash)["logs"] if len(log["data"]) == 258]
    print(f"Got {len(swapLogs)} logs!")
    for log in swapLogs:
        uniswapPair = w3.eth.contract(address=w3.to_checksum_address(log['address']), abi=pairABI)
        token0 = w3.eth.contract(address=w3.to_checksum_address(uniswapPair.functions.token0().call()), abi=tokenABI)
        token1 = w3.eth.contract(address=w3.to_checksum_address(uniswapPair.functions.token1().call()), abi=tokenABI)  # token1 casi siempre es WETH                    
        if token1.functions.symbol().call() == "WETH" and token0.functions.symbol().call() == tokenInSymbol:
            return uniswapPair.functions.token0().call(), uniswapPair.functions.token1().call(), log['address']
        elif token1.functions.symbol().call() == "WETH" and token0.functions.symbol().call() == tokenOutSymbol:
            return uniswapPair.functions.token1().call(), uniswapPair.functions.token0().call(), log['address']
    raise Exception("Error, none was WETH or pair is dissordered!")

print("Initiating Web3 client...")
rpc_url = "https://ethereum.publicnode.com"
w3 = Web3(Web3.HTTPProvider(rpc_url))

print("Initiating etherscan client...")
api_key = "397DG3PDX5BUT6XYMVIQE518NTZQT66BZ8"
client = etherscan.Etherscan(api_key=api_key)

print("Initiating UniswapV2Router02...")
UniswapV2Router02 = w3.eth.contract(address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", abi=[{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsIn","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}])

tokenABI = [{"constant": True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable": False,"stateMutability":"view","type":"function"},
            {"constant": True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable": False,"stateMutability":"view","type":"function"}]
pairABI = [{"constant": True, "inputs": [], "name": "token0", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
            {"constant": True, "inputs": [], "name": "token1", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
            {"constant": True,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable": False,"stateMutability":"view","type":"function"}]

def expandCSV():
    with open("capturedTransactionHashes.txt") as file:
        try:
            i = 1
            while line := file.readline():
                print(f"Processing {line[:-1]}")
                line = line.split(",")
                tokenInAddress, tokenOutAddress, uniswapPairAddress = getPairInfo(tokenInSymbol=line[3], tokenOutSymbol=line[4], transaccionHash=line[2])
                line.insert(5, tokenInAddress)
                line.insert(6, tokenOutAddress)
                line.insert(7, uniswapPairAddress)
                print("\tWritting to file...", end="")
                with open("capturedTransactionHashes2.txt", "a") as file2:
                    file2.write(f"{(',').join(line)}")
                print("Done!")
                i += 1
        except BaseException as e:
            print(f"Exception: {e}")
            pdb.set_trace()

def calculatePositions():
    positions = PositionCollection()
    with open("capturedTransactionHashes2.txt") as file:
        file.readline()
        processedTransactions = []
        totalGasSpent = 0
        lastTimestampProcessed = ""
        try:
            i=0
            while line := file.readline(): #TODO check this syntax!!!
                line = line.split(",")
                if line[2] in processedTransactions:
                    continue
                else:
                    processedTransactions.append(line[2])
                uniswapPair = w3.eth.contract(address=w3.to_checksum_address(line[7]), abi=pairABI)
                if line[1] == "BUY":
                    token = Token(w3.eth.contract(address=w3.to_checksum_address(line[6]), abi=tokenABI), uniswapPair, UniswapV2Router02)
                    positions.increasePosition(token, float(line[9])/float(line[8]), float(line[8]))
                    totalGasSpent += (int(line[10]) * int(line[11])) / 1e18
                elif line[1] == "SELL":
                    token = Token(w3.eth.contract(address=w3.to_checksum_address(line[5]), abi=tokenABI), uniswapPair, UniswapV2Router02)
                    success = positions.reducePosition(token, float(line[9])/float(line[8]), float(line[8]))
                    if success:
                        totalGasSpent += (int(line[10]) * int(line[11])) / 1e18
                lastTimestampProcessed = line[0]
                i+=1
                if i > 10:
                    break
        finally:
            with open("saveProgress.txt", "a") as f:
                f.write(f"{lastTimestampProcessed} {totalGasSpent}\n")
                #save lastTimestampProcessed and totalGasSpent and serialize positionCollection TODO
    pdb.set_trace()

calculatePositions()