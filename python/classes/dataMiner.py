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

#1108
def simplifyCaptures():
    processedTransactions = []
    with open("captured3.txt") as readFile:
        with open("captured1.txt", "w") as writeFile:
            readFile.readline()
            writeFile.write("function,tx_hash\n")
        while line := readFile.readline().strip():
            line = line.split(",")
            if line[2] not in processedTransactions:
                processedTransactions.append(line[2])
                with open("captured1.txt", "a") as writeFile:
                    writeFile.write(f"{line[1]},{line[2]}\n")

def calculatePositions():
    lineNumber = 2
    readFiles = True
    continueProcessing = False
    lastTimestampProcessed = datetime.strptime("2000", "%Y")
    serializedPositions = ""
    writeFiles = False
    processedTransactions = []
    failedTransactions = []
    if readFiles:
        with open("saveProgress.txt") as f:
            _data = f.read().split(',')
            lastTimestampProcessed = datetime.strptime(_data[0], '%Y-%m-%d %H:%M:%S.%f')
        with open("positions.txt") as f:
            serializedPositions = f.read()
    positions = PositionCollection(serializedPositions)
    if continueProcessing:
        try:    
            with open("captured3.txt") as file:
                file.readline()
                if writeFiles:
                    with open("gasUsage.txt", "w") as f:
                        f.write("tx_hash,gas_used,gas_price,gas_cost_in_eth\n")
                while line := file.readline():
                    line = line.strip().split(",")
                    successfulOperation = True
                    uniswapPair = EVMInterface.getPairContract(address=line[7])
                    if continueProcessing and lastTimestampProcessed >= datetime.strptime(line[0], '%Y-%m-%d %H:%M:%S.%f'):
                        continue
                    if line[1] == "BUY":
                        token = Token(EVMInterface.getTokenContract(address=line[6]), uniswapPair)
                        #print(f"BUY {line[4]}: {float(line[12])}")
                        positions.increasePosition(token, float(line[12]), float(line[10]))
                    elif line[1] == "SELL":
                        token = Token(EVMInterface.getTokenContract(address=line[5]), uniswapPair)
                        #print(f"SELL {line[3]}: {float(line[12])} ", end="")
                        successfulOperation = positions.reducePosition(token, float(line[12]), float(line[10]))
                        if not successfulOperation:
                            failedTransactions.append((line[0], line[2]))
                        #print(successfulOperation)
                    lastTimestampProcessed = datetime.strptime(line[0], '%Y-%m-%d %H:%M:%S.%f')
                    if line[2] not in processedTransactions and successfulOperation and writeFiles:
                        processedTransactions.append(line[2])
                        with open("gasUsage.txt", "a") as f:
                            tx_hash = line[2]
                            tx_receipt = EVMInterface.w3.eth.wait_for_transaction_receipt(tx_hash)
                            gas_cost = tx_receipt.gasUsed * tx_receipt.effectiveGasPrice / 1e18
                            f.write(f"{tx_hash},{tx_receipt.gasUsed},{tx_receipt.effectiveGasPrice},{gas_cost}\n")
                    print(lineNumber)
                    lineNumber += 1
        finally:
            if writeFiles:
                with open("saveProgress.txt", "w") as f:
                    f.write(f"{lastTimestampProcessed}")
                with open("positions.txt", "w") as f:
                    f.write(positions.serialize())
    print("ENTERING INTERACTIVE CONSOLE...")
    pdb.set_trace()

def refactorCapturedTransactions():
    with open("captured1.txt") as readFile:
        with open("captured2.txt", "w") as writeFile:
            line = readFile.readline().split()
            newLine = [*line[:8], "amount_in", "amount_out", "execution_price", "eth_amount", "token_amount", "sync_reserves_after"]
            writeFile.write(f"{(',').join(newLine)}\n")
        counter = 0
        while line := readFile.readline().split(","):
            tx_hash = line[1].strip()
            print(counter)
            counter += 1
            logs = EVMInterface.etherscanClient.get_proxy_transaction_receipt(tx_hash)["logs"]
            flag = False
            for index, log in enumerate(logs):
                if len(log["data"]) == 258:
                    assert index > 0, "A swap log cannot be the first event"
                    assert len(logs[index - 1]["data"]) == 130, "Swap logs must follow a Sync log"
                    uniswapPair = EVMInterface.getPairContract(log['address'])
                    token0 = EVMInterface.getTokenContract(uniswapPair.functions.token0().call())
                    token1 = EVMInterface.getTokenContract(uniswapPair.functions.token1().call()) 
                    if line[0] == "BUY":
                        tokenInAddress = token1.address
                        tokenOutAddress = token0.address
                        tokenInSymbol = token1.functions.symbol().call()
                        tokenOutSymbol = token0.functions.symbol().call()
                        amount_out = int(log["data"][130:130+64], 16)
                        amount_in = int(log["data"][66:130], 16)
                        eth_amount = amount_in / 1e18
                        token_amount = amount_out / (10**token0.functions.decimals().call())
                    elif line[0] == "SELL":
                        tokenInAddress = token0.address
                        tokenOutAddress = token1.address
                        tokenInSymbol = token0.functions.symbol().call()
                        tokenOutSymbol = token1.functions.symbol().call()
                        amount_out = int(log["data"][194:], 16)
                        amount_in = int(log["data"][2:66], 16)
                        eth_amount = amount_out / 1e18
                        token_amount = amount_in / (10**token0.functions.decimals().call())
                    else:
                        raise Exception("Unknown transaction function processed")
                    price = eth_amount / token_amount
                    deterministicReservesAfter = [int(logs[index - 1]["data"][2:66], 16), int(logs[index - 1]["data"][66:130], 16)]
                    newLine = [line[0], tx_hash, tokenInSymbol, tokenOutSymbol, tokenInAddress, tokenOutAddress, uniswapPair.address, str(amount_in), str(amount_out), str(price), str(eth_amount), str(token_amount), str(deterministicReservesAfter)]
                    with open("captured2.txt", "a") as writeFile:
                        writeFile.write(f"{(',').join(newLine)}\n")
                    flag = True
            if not flag:
                raise Exception("Attempted to process a transaction without any swap logs")

def compareReserves():
    with open("captured3.txt") as f:
        f.readline()
        count = 0
        lineNumber = 2
        while line := f.readline().strip():
            line = line.split(',')
            syncReserves = (',').join(line[13:15])
            capturedReserves = (',').join(line[15:17])
            if syncReserves != capturedReserves:
                count += 1
                print(f"{lineNumber} {syncReserves} <==> {capturedReserves}")
            lineNumber += 1
        print(count)

def calculateGas():
    with open("gasUsage.txt") as readFile:
        cummulativeCost = 0
        readFile.readline()
        while line := readFile.readline().strip():
            line = line.split(",")
            cummulativeCost += float(line[3])
    print(cummulativeCost)
    return cummulativeCost
            

#TODO remove gas and analyze it later trying to get percentage of gas used, ALSO TODO, do the gas used check in the sacnner, as it is currently logging the gas limit LAST TODO, add all the additional fields to the scanner

calculatePositions()
#compareReserves()
#calculateGas()
#pdb.set_trace()

#49.44349383700043 value today
#50.98830630985579 true value
#42.50275401937556 eth gotten out
#41.822331653041296 eth put in
#15.241479024445457 gas