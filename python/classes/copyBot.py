from brownie import accounts, interface, Contract


UniswapV2Router02 = w3.eth.contract(address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", abi=[{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsIn","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}])

def swap():
    # Connect to an Ethereum network
    network = "mainnet"  # You can use a testnet like "ropsten" for testing
    account = accounts.load("your_wallet_name")  # Load your wallet using a Brownie account

    # Load the Uniswap Router contract
    router_address = "0xYourUniswapRouterAddress"  # Replace with the actual Uniswap Router address
    router = interface.IUniswapV2Router02(router_address)

    # Define token addresses and swap parameters
    token_in_address = "0xTokenInAddress"  # Address of the token you want to swap
    token_out_address = "0xTokenOutAddress"  # Address of the token you want to receive
    amount_in = 1000000000000000000  # Amount of tokenIn you want to swap (in Wei)
    amount_out_min = 900000000000000000  # Minimum amount of tokenOut you want to receive (in Wei)
    deadline = 1634960400  # Deadline in UNIX timestamp (replace with your desired deadline)
    gas_price = "30 gwei"  # Set an appropriate gas price

    # Approve the Router contract to spend your tokens (if needed)
    token_in = Contract.from_explorer(token_in_address)
    token_in.approve(router_address, amount_in, {"from": account})

    # Perform the swap
    tx = router.swapExactTokensForTokens(
        amount_in,
        amount_out_min,
        [token_in_address, token_out_address],
        account,
        deadline,
        {"from": account, "gas_price": gas_price},
    )

    # Wait for the transaction to be mined
    tx.wait()

    print(f"Swap complete. Transaction hash: {tx.txid}")
