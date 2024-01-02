import pdb
import json
from datetime import datetime
from position import EVMInterface, PositionCollection, Token

# HASTA LA LINEA 672 DE CAPTURED2 INCLUIDA CONTANDO HEADERS

def getPairInfo(tokenInSymbol, tokenOutSymbol, transaccionHash):
    print(f"\tGetting Swap Logs...", end="")
    swapLogs = [log for log in EVMInterface.etherscanClient.get_proxy_transaction_receipt(transaccionHash)["logs"] if len(log["data"]) == 258]
    print(f"Got {len(swapLogs)} logs!")
    for log in swapLogs:
        uniswapPair = EVMInterface.getPairContract(address=log['address'])
        token0 = EVMInterface.getTokenContract(address=uniswapPair.functions.token0().call())
        token1 = EVMInterface.getTokenContract(address=uniswapPair.functions.token1().call())  # token1 casi siempre es WETH                    
        if token1.functions.symbol().call() == "WETH" and token0.functions.symbol().call() == tokenInSymbol:
            return uniswapPair.functions.token0().call(), uniswapPair.functions.token1().call(), log['address']
        elif token1.functions.symbol().call() == "WETH" and token0.functions.symbol().call() == tokenOutSymbol:
            return uniswapPair.functions.token1().call(), uniswapPair.functions.token0().call(), log['address']
    raise Exception("Error, none was WETH or pair is dissordered!")

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

def calculatePositionsAndGas():
    continueProcessing = True
    processedTransactions = []
    lastTimestampProcessed = ""
    serializedPositions = ""
    totalGasSpent = 0
    if continueProcessing:
        with open("processedTransactions.txt") as f:
            processedTransactions = json.loads(f.read())
        with open("saveProgress.txt") as f:
            _data = f.read().split(',')
            lastTimestampProcessed = _data[0]
            totalGasSpent = float(_data[1])
        with open("positions.txt") as f:
            serializedPositions = f.read()
    positions = PositionCollection(serializedPositions)
    with open("capturedTransactionHashes.txt") as file:
        file.readline()
        try:
            while line := file.readline(): #TODO check this syntax!!!
                successfulOperation = True
                line = line.split(",")
                uniswapPair = EVMInterface.getPairContract(address=line[7])
                if continueProcessing and datetime.strptime(lastTimestampProcessed, '%Y-%m-%d %H:%M:%S.%f') >= datetime.strptime(line[0], '%Y-%m-%d %H:%M:%S.%f'):
                    continue
                if line[1] == "BUY":
                    token = Token(EVMInterface.getTokenContract(address=line[6]), uniswapPair)
                    positions.increasePosition(token, float(line[9])/float(line[8]), float(line[8]))
                elif line[1] == "SELL":
                    token = Token(EVMInterface.getTokenContract(address=line[5]), uniswapPair)
                    print(f"SELL {line[3]}: ", end="")
                    successfulOperation = positions.reducePosition(token, float(line[9])/float(line[8]), float(line[8]))
                    print(successfulOperation)

                if line[2] not in processedTransactions and successfulOperation:
                    processedTransactions.append(line[2])
                    totalGasSpent += (int(line[10]) * int(line[11])) / 1e18
                lastTimestampProcessed = line[0]
        finally:
            with open("saveProgress.txt", "w") as f:
                f.write(f"{lastTimestampProcessed},{totalGasSpent}")
            with open("processedTransactions.txt", "w") as f:
                f.write(json.dumps(processedTransactions))
            with open("positions.txt", "w") as f:
                f.write(positions.serialize())
    print("ENTERING INTERACTIVE CONSOLE...")
    pdb.set_trace()

calculatePositionsAndGas()