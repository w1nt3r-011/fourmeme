from datetime import datetime
from eth_account import Account
import requests




FOURMEME_CONTRACT_ADDRESS = "0x5c952063c7fc8610FFDB798152D69F0B9550762b"
TOTAL_SUPPLY = 1_000_000_000
TOKEN_DECIMALS = 18
INFINITE_APPROVAL = 2**256 - 1

def log(message):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')} {message}")


def buy(RPC_CLIENT, contract_abi, payer_pk, token_address, bnb_in, min_tokens_out, gas_gwei, gas_limit):
    try:
        log(f"[BUY] Buying {token_address}")
        payer_addr = str(Account.from_key(payer_pk).address)
        fourmeme_contract_address = RPC_CLIENT.to_checksum_address(FOURMEME_CONTRACT_ADDRESS)
        fourmeme_contract = RPC_CLIENT.eth.contract(
            address=fourmeme_contract_address,
            abi=contract_abi
        )
        token_address = RPC_CLIENT.to_checksum_address(token_address)
        funds_in_wei = RPC_CLIENT.to_wei(bnb_in, "ether")
        nonce = RPC_CLIENT.eth.get_transaction_count(payer_addr)
        tx_builder = fourmeme_contract.functions.buyTokenAMAP(
            token_address,
            payer_addr,
            funds_in_wei,
            int(min_tokens_out)
        ).build_transaction({
            'from': payer_addr,
            'value': funds_in_wei,
            'gasPrice': RPC_CLIENT.to_wei(gas_gwei, 'gwei'),
            'gas': gas_limit,
            'nonce': nonce
        })
        signed_tx = RPC_CLIENT.eth.account.sign_transaction(tx_builder, payer_pk)
        tx_hash = RPC_CLIENT.eth.send_raw_transaction(signed_tx.raw_transaction)
        log(f"[BUY] Sent https://bscscan.com/tx/{RPC_CLIENT.to_hex(tx_hash)}")
        return True
    except Exception as e:
        log(f"[BUY] error {str(e)}")
        return False


def sell(RPC_CLIENT, contract_abi, payer_pk, token_address, tokens_in, min_bnb_out, gas_gwei, gas_limit):
    try:
        log(f"[SELL] Selling {token_address}")
        payer_addr = str(Account.from_key(payer_pk).address)
        fourmeme_contract_address = RPC_CLIENT.to_checksum_address(FOURMEME_CONTRACT_ADDRESS)
        fourmeme_contract = RPC_CLIENT.eth.contract(
            address=fourmeme_contract_address,
            abi=contract_abi
        )
        token_address = RPC_CLIENT.to_checksum_address(token_address)
        nonce = RPC_CLIENT.eth.get_transaction_count(payer_addr)
        tx_builder = fourmeme_contract.functions.sellToken(
            token_address,
            int(tokens_in),
            int(min_bnb_out)
        ).build_transaction({
            'from': payer_addr,
            'gasPrice': RPC_CLIENT.to_wei(gas_gwei, 'gwei'),
            'gas': gas_limit,
            'nonce': nonce
        })
        signed_tx = RPC_CLIENT.eth.account.sign_transaction(tx_builder, payer_pk)
        tx_hash = RPC_CLIENT.eth.send_raw_transaction(signed_tx.raw_transaction)
        log(f"[SELL] Sent https://bscscan.com/tx/{RPC_CLIENT.to_hex(tx_hash)}")
        return True
    except Exception as e:
        log(f"[SELL] error {str(e)}")
        return False


def approve_sell_unlimited(RPC_CLIENT, payer_pk, token_address, gas_gwei, gas_limit):
    try:
        erc20_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
        ]
        log(f"[APPROVE UNLIMITED] Approving unlimited tokens for {token_address}")
        payer_addr = str(Account.from_key(payer_pk).address)
        fourmeme_contract_address = RPC_CLIENT.to_checksum_address(FOURMEME_CONTRACT_ADDRESS)
        token_contract = RPC_CLIENT.eth.contract(
            address=RPC_CLIENT.to_checksum_address(token_address),
            abi=erc20_abi
        )
        unlimited_approve_amount = 2**256 - 1
        nonce = RPC_CLIENT.eth.get_transaction_count(payer_addr)
        tx_approve = token_contract.functions.approve(
            fourmeme_contract_address,
            unlimited_approve_amount
        ).build_transaction({
            'from': payer_addr,
            'gasPrice': RPC_CLIENT.to_wei(gas_gwei, 'gwei'),
            'gas': gas_limit,
            'nonce': nonce
        })
        signed_approve = RPC_CLIENT.eth.account.sign_transaction(tx_approve, payer_pk)
        log(f"[APPROVE UNLIMITED] Sent")
        return True
    except Exception as e:
        log(f"[APPROVE UNLIMITED] error {str(e)}")
        return False


def check_approval(RPC_CLIENT, payer_pk, token_address):
    try:
        erc20_abi = [
            {
                "constant": True,
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
        log(f"[APPROVE CHECK] Checking {token_address}")
        payer_addr = str(Account.from_key(payer_pk).address)
        fourmeme_contract_address = RPC_CLIENT.to_checksum_address(FOURMEME_CONTRACT_ADDRESS)
        token_contract = RPC_CLIENT.eth.contract(
            address=RPC_CLIENT.to_checksum_address(token_address),
            abi=erc20_abi
        )
        current_allowance = token_contract.functions.allowance(
            payer_addr, 
            fourmeme_contract_address
        ).call()
        if current_allowance > 0:
            log(f"[APPROVE CHECK] Found allowance {current_allowance}")
            return True
        else:
            log("[APPROVE CHECK] No allowance")
            return False
    except Exception as e:
        log(f"[APPROVE CHECK] error {str(e)}")
        return False


def fetch_holdings(RPC_CLIENT, contract_abi, token_address, payer_pk):
    try:
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        token_address = RPC_CLIENT.to_checksum_address(token_address)
        holder_address = str(Account.from_key(payer_pk).address)
        log(f"[HOLDINGS] Checking holdings of {token_address}")
        token_contract = RPC_CLIENT.eth.contract(
            address=token_address,
            abi=erc20_abi
        )
        raw_balance = token_contract.functions.balanceOf(holder_address).call()
        balance_human = raw_balance / 10**TOKEN_DECIMALS
        fourmeme_contract = RPC_CLIENT.eth.contract(
            address=RPC_CLIENT.to_checksum_address(FOURMEME_CONTRACT_ADDRESS),
            abi=contract_abi
        )
        token_info = fourmeme_contract.functions._tokenInfos(token_address).call()
        last_price = token_info[9]
        token_price_bnb = last_price / 1e18
        holdings_bnb = balance_human * token_price_bnb
        log(f"[HOLDINGS] Holding {balance_human} tokens worth {holdings_bnb} BNB")
        return {"token_balance": raw_balance, "token_value": holdings_bnb}
    except Exception as e:
        log(f"[HOLDINGS] error {str(e)}")
        return False


def fetch_marketcap(RPC_CLIENT, contract_abi, token_address, bnb_price):
    try:
        token_address = RPC_CLIENT.to_checksum_address(token_address)
        contract = RPC_CLIENT.eth.contract(address=FOURMEME_CONTRACT_ADDRESS, abi=contract_abi)
        token_info = contract.functions._tokenInfos(token_address).call()
        last_price = token_info[9]
        token_price_bnb = last_price / 1e18
        token_price_usd = token_price_bnb * bnb_price
        market_cap = token_price_usd * TOTAL_SUPPLY
        log(f"[MARKETCAP] {token_address} ${market_cap}")
        return True
    except Exception as e:
        log(f"[MARKETCAP] error {str(e)}")
        return False


def calc_min_tokens_out(bnb_in, bnb_price, max_mcap):
    try:
        max_usd_price_per_token = max_mcap / TOTAL_SUPPLY
        max_bnb_price_per_token = max_usd_price_per_token / bnb_price
        min_tokens_human = float(bnb_in) / max_bnb_price_per_token
        log(f"[MIN TOKENS CALC] {round(min_tokens_human, 2)}")
        min_tokens_scaled = int(min_tokens_human * 10**TOKEN_DECIMALS)
        return min_tokens_scaled
    except Exception as e:
        log(f"[MIN TOKENS CALC] error {str(e)}")
        return False


def fetch_bnb_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd")
        req_data = r.json()
        bnb_price = req_data['binancecoin']['usd']
        return bnb_price
    except Exception as e:
        log(f"[BNB PRICE] error {str(e)}")
        return False
