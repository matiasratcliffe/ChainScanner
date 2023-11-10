import pdb
import time
import datetime
import etherscan
from web3 import Web3


# TODO not always WETH is token1
# TODO sometimes their transaction fails, we need to check if that affects us
# TODO look where the main RPC is located and run script in azure in same physical location

class PendingTX:
    def __init__(self, tx_hash, to, capturedTimestamp) -> None:
        self.tx_hash = tx_hash
        self.to = to
        self.capturedTimestamp = capturedTimestamp

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PendingTX) and self.tx_hash == other.tx_hash

    def __hash__(self) -> int:
        return hash(self.tx_hash)

def scanPendingTransactions():
    global pendingBlockNumber, pendingMatchingTransactions, contractAddress
    if w3.is_connected():
        with open("pendingTransactionHashes.txt", "a") as pending:
            printDev("Getting pending transactions...", end="")
            pending_txns = w3.eth.get_block("pending", full_transactions=True)
            if ("transactions" in pending_txns):
                printDev(f"{len(pending_txns['transactions'])} transactions pending [Block {pending_txns['transactions'][0]['blockNumber']}]")
                if pending_txns["transactions"][0]["blockNumber"] != pendingBlockNumber:  # si hay cambio de bloque
                    printDev(f"\tBlockChanged! {len(pendingMatchingTransactions)} matching pending transactions are being processed")
                    limitTime = time.time()
                    pendingBlockNumber = pending_txns["transactions"][0]["blockNumber"]
                    for tx in pendingMatchingTransactions:  # proceso las buffereadas
                        pending.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')},{tx.tx_hash},{tx.to},{tx.capturedTimestamp},{limitTime-tx.capturedTimestamp}\n")
                        printDev("\t########### PENDING FILE WRITTEN ###########")
                    pendingMatchingTransactions = set({})  # lo vacio al final
                
                for tx in pending_txns["transactions"]:  # y aca lo voy llenando con lo del siguiente bloque
                    if (tx.to and tx.to.lower() == contractAddress):
                        pendingMatchingTransactions.add(PendingTX(tx["hash"].hex(), tx.to.lower(), time.time()))
            else:
                printDev("No transactions found!")
    else:
        printDev("Error connecting to Web3 client!")

def captureBlockTransactions():
    global capturedLastBlockNumber, contractAddress
    with open("capturedTransactionHashes.txt", "a") as captured:
        if (capturedLastBlockNumber != w3.eth.block_number):
            capturedLastBlockNumber = w3.eth.block_number  # This is for buffering purposes
            printDev("Capturing last block of transactions...", end="")
            capturedTransactions = w3.eth.get_block(capturedLastBlockNumber, full_transactions=True).transactions #[tx for tx in w3.eth.get_block(capturedLastBlockNumber, full_transactions=True).transactions if tx.to and tx.to.lower() == contractAddress]
            if (len(capturedTransactions) > 0):
                printDev(f"Captured {len(capturedTransactions)} transactions [Block {capturedLastBlockNumber}]")
                for tx in capturedTransactions:
                    if (tx.to and tx.to.lower() != contractAddress.lower()):
                        continue
                    if (tx.input[0:4].hex() == "0x7a4e5cd2"):
                        functionName = "BUY"
                    elif (tx.input[0:4].hex() == "0x23f4e1ee"):
                        functionName = "SELL"
                    else:
                        functionName = tx.input[0:4].hex()
                        #captured.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')},{functionName},{tx.hash.hex()},{tx['from']},{tx['to']}\n")
                        #printDev("\t########### CAPTURED FILE WRITTEN ###########")
                        continue
                        
                    swapLogs = [log for log in client.get_proxy_transaction_receipt(tx.hash.hex())["logs"] if len(log["data"]) == 258]
                    if (len(swapLogs) > 0):
                        printDev(f"\tTransaction {tx.hash.hex()} {len(swapLogs)} swaps were made")
                        for log in swapLogs:
                            #pdb.set_trace()
                            uniswapPair = w3.eth.contract(address=w3.to_checksum_address(log['address']), abi=pairABI)
                            token0 = w3.eth.contract(address=w3.to_checksum_address(uniswapPair.functions.token0().call()), abi=tokenABI)
                            token1 = w3.eth.contract(address=w3.to_checksum_address(uniswapPair.functions.token1().call()), abi=tokenABI)  # token1 es WETH
                            reserves_after = uniswapPair.functions.getReserves().call()
                            if (functionName == "BUY"):
                                processBuyTransactionSwap(captured, tx.hash.hex(), log, tokenOut=token0, tokenIn=token1, reserves=reserves_after)
                            else:
                                processSellTransactionSwap(captured, tx.hash.hex(), log, tokenOut=token1, tokenIn=token0, reserves=reserves_after)
            else:
                printDev(f"No transactions where captured [Block {capturedLastBlockNumber}]")

def processBuyTransactionSwap(file, tx_hash, log, tokenOut, tokenIn, reserves):
    amount_out = int(log["data"][130:130+64], 16)
    amount_in = int(log["data"][66:130], 16)
    tokenOutSymbol = tokenOut.functions.symbol().call()
    tokenInSymbol = tokenIn.functions.symbol().call()
    if (tokenOutSymbol == "WETH"):
        eth_amount = amount_out / 1e18
    elif (tokenInSymbol == "WETH"):  #deberia ser el caso
        eth_amount = amount_in / 1e18
    else:
        eth_amount = "NotFound"
    multiplier = 10**(tokenOut.functions.decimals().call() - tokenIn.functions.decimals().call())  # ver si esto no es mejor meterlo en los if porque capaz depende del orden
    file.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')},BUY,{tx_hash},{tokenInSymbol},{tokenOutSymbol},{eth_amount/(multiplier*amount_out)},{eth_amount},{reserves[:2]}\n")
    printDev("\t########### CAPTURED FILE WRITTEN ###########")

def processSellTransactionSwap(file, tx_hash, log, tokenOut, tokenIn, reserves):
    amount_out = int(log["data"][194:], 16)
    amount_in = int(log["data"][2:66], 16)
    tokenOutSymbol = tokenOut.functions.symbol().call()
    tokenInSymbol = tokenIn.functions.symbol().call()
    if (tokenOutSymbol == "WETH"):  #deberia ser el caso
        eth_amount = amount_out / 1e18
    elif (tokenInSymbol == "WETH"):
        eth_amount = amount_in / 1e18
    else:
        eth_amount = "NotFound"
    multiplier = 10**(tokenOut.functions.decimals().call() - tokenIn.functions.decimals().call())  # ver si esto no es mejor meterlo en los if porque capaz depende del orden
    file.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')},SELL,{tx_hash},{tokenInSymbol},{tokenOutSymbol},{(multiplier*eth_amount)/amount_in},{eth_amount},{reserves[:2]}\n")
    printDev("\t########### CAPTURED FILE WRITTEN ###########")

def get_amount_in(amount_out, reserve_in, reserve_out):
    assert amount_out > 0, 'INSUFFICIENT_OUTPUT_AMOUNT'
    assert reserve_in > 0 and reserve_out > 0, 'INSUFFICIENT_LIQUIDITY'

    numerator = reserve_in * amount_out * 1000
    denominator = (reserve_out - amount_out) * 997

    amount_in = (numerator // denominator) + 1
    return amount_in

def printDev(message, end="\n"):
    global DEBUG
    if DEBUG:
        print(message, end=end)


if __name__ == "__main__":
    DEBUG = True

    printDev("Initiating Web3 client...")
    rpc_url = "https://ethereum.publicnode.com"
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    printDev("Initiating etherscan client...")
    api_key = "397DG3PDX5BUT6XYMVIQE518NTZQT66BZ8"
    client = etherscan.Etherscan(api_key=api_key)

    tokenABI = [{"constant": True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable": False,"stateMutability":"view","type":"function"},
                {"constant": True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable": False,"stateMutability":"view","type":"function"}]
    pairABI = [{"constant": True, "inputs": [], "name": "token0", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
               {"constant": True, "inputs": [], "name": "token1", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
               {"constant": True,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable": False,"stateMutability":"view","type":"function"}]
    UniswapV2Router02 = w3.eth.contract(address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", abi=[{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsIn","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}])
    contractAddress = "0x50b8f49f4b2e80e09ce8015c4e7a9c277738fd3d"
    
    pendingMatchingTransactions = set({})
    pendingBlockNumber = w3.eth.block_number + 1
    capturedLastBlockNumber = 0

    printDev("Scanning has begun!")
    while True:
        scanPendingTransactions()
        captureBlockTransactions()