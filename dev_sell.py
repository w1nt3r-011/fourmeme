import json
import time
from web3 import Web3
import threading
from datetime import datetime
from fourmeme_buy_sell import sell, fetch_holdings
import yaml
import requests




def log(message):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')} {message}")


CONTRACT_ADDRESS = "0x5c952063c7fc8610FFDB798152D69F0B9550762b"
dev_sell_dict = {}
known_cas = set()


try:
    with open("dev_sell_config.yaml", "r") as config_file:
        config_data = yaml.safe_load(config_file)
        RPC_HTTP = config_data["RPC_HTTP"]
        PAYER_PK = config_data["PAYER_PK"]
        SELL_GWEI = config_data["SELL_GWEI"]

    web3_client = Web3(Web3.HTTPProvider(RPC_HTTP))
    if web3_client.is_connected():
        log(f"[STARTUP] connected to RPC {RPC_HTTP}")
    else:
        log(f"[STARTUP] error connecting to RPC {RPC_HTTP}")
        time.sleep(5)
        raise SystemExit

    with open("fourmeme_abi.json", "r") as abi_file:
        contract_abi = json.load(abi_file)

except Exception as e:
    log(f"[STARTUP] error {str(e)}")
    time.sleep(5)
    raise SystemExit


def handle_trade(trade_data):
    try:
        token_address = trade_data.get("args", {}).get("token", "")
        if token_address in dev_sell_dict:
            dev_wallet = dev_sell_dict[token_address]
            seller = trade_data.get("args", {}).get("account", "")
            if str(seller).lower() == str(dev_wallet).lower():
                log(f"[TRADE] Developer just sold coin {token_address}")
                holdings_resp = fetch_holdings(web3_client, contract_abi, token_address, PAYER_PK)
                if holdings_resp:
                    log(f"[TRADE] Fetched holdings worth {holdings_resp["token_value"]} BNB")
                    min_bnb_out = 0
                    sell(web3_client, contract_abi, PAYER_PK, token_address, holdings_resp["token_balance"], min_bnb_out, SELL_GWEI, 250_000)
    except Exception as e:
        log(f"[TRADE] error handling trade {str(e)}")


def handle_cas():
    while True:
        try:
            with open("dev_sell_cas.txt", "r") as f:
                lines = [line.strip() for line in f if line.strip()]
            for ca in lines:
                if ca not in known_cas:
                    attempts = 0
                    while attempts < 10:
                        try:
                            r = requests.get(f"https://four.meme/meme-api/v1/private/token/get/v2?address={ca}")
                            if r.status_code == 200:
                                req_data = r.json()
                                dev_wallet = req_data["data"]["userAddress"]
                                dev_sell_dict[ca] = dev_wallet
                                known_cas.add(ca)
                                log(f"[FILE HANDLER] Added new token")
                                log(f"[FILE HANDLER] CA: {ca}")
                                log(f"[FILE HANDLER] DEV: {dev_wallet}")
                                break
                            else:
                                time.sleep(5)
                        except Exception as e:
                            log(f"[FILE HANDLER] error {str(e)}")
                            time.sleep(5)
                        attempts += 1

                    if attempts == 10:
                        log(f"[FILE HANDLER] Could not add contract address: {ca}")
        except Exception as e:
            log(f"[FILE HANDLER] error {str(e)}")
        time.sleep(0.5)


def main():
    threading.Thread(target=handle_cas, daemon=True).start()

    contract = web3_client.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

    while True:
        try:
            sale_filter = contract.events.TokenSale.create_filter(from_block="latest")
            log(f"[MONITOR] subscribed to events")
        except ValueError as e:
            log(f"[MONITOR] error creating event filter {str(e)}")
            time.sleep(5)
            continue

        while True:
            try:
                new_sales = sale_filter.get_new_entries()
                for event in new_sales:
                    threading.Thread(target=handle_trade, args=(event,), daemon=True).start()
                time.sleep(0.1)
            except Exception as e:
                log(f"[MONITOR] error polling events {str(e)}")
                time.sleep(5)
                break

main()
