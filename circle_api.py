import uuid
import enum
import dotenv
import os

from circle.web3 import developer_controlled_wallets
from circle.web3 import utils as circle_utils
import requests

import definitions as defs

dotenv.load_dotenv()

CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
ENTITY_SECRET = os.getenv("ENTITY_SECRET")
WALLET_SET_ID = os.getenv("WALLET_SET_ID")

client = circle_utils.init_developer_controlled_wallets_client(api_key=CIRCLE_API_KEY, entity_secret=ENTITY_SECRET)

def create_wallet(nr_wallets: int, blockchain: defs.Blockchain = defs.Blockchain.MATIC_AMOY) -> defs.Wallets:
    api_instance = developer_controlled_wallets.WalletsApi(client)

    if nr_wallets > 20:
        raise ValueError("Cannot create more than 20 wallets at a time")

    try:
        request = developer_controlled_wallets.CreateWalletRequest.from_dict({
            "accountType": 'SCA',
            "blockchains": [blockchain.value],
            "count": nr_wallets,
            "walletSetId": WALLET_SET_ID
        })
        api_instance.create_wallet(request) # TODO does not actually return wallets as it's supposed to

        return [wallet.actual_instance for wallet in api_instance.get_wallets(page_size=nr_wallets).data.wallets] # type: ignore

    except developer_controlled_wallets.ApiException as e:
        print(f"Exception when calling WalletsApi->create_wallet: {e}")
        return []

def update_wallet(wallet_id: str, wallet_name: str, wallet_ref_id: str) -> bool:
    api_instance = developer_controlled_wallets.WalletsApi(client)
    
    try:
        request = developer_controlled_wallets.UpdateWalletRequest(
                name=wallet_name,
                ref_id=wallet_ref_id
            )
        api_instance.update_wallet(wallet_id, request)
        print(f"Updated wallet {wallet_id} with name: {wallet_name} and ref_id: {wallet_ref_id}")
        return True
    except developer_controlled_wallets.ApiException as e:
        print(f"Exception when calling WalletsApi->update_wallet: {e}")
        return False

def get_wallet_balance(wallet_id: str):
    url = f"https://api.circle.com/v1/w3s/wallets/{wallet_id}/balances"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {CIRCLE_API_KEY}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def send_transfer(wallet_id: str, recipient: str, tokenId: str, amount: float):
    url = "https://api.circle.com/v1/w3s/developer/transactions/transfer"

    payload = {
        "walletId": wallet_id,
        "destinationAddress": recipient,
        "tokenId": tokenId,
        "amounts": [str(amount)],
        "idempotencyKey": str(uuid.uuid4()), # TODO create a uuid from the user request so that it can only be sent once
        "entitySecretCiphertext": client.generate_entity_secret_ciphertext(),
        "feeLevel": "MEDIUM"
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {CIRCLE_API_KEY}"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(response.json())
    return response.json()

def get_transaction(transaction_id: str):
    url = f"https://api.circle.com/v1/w3s/transactions/{transaction_id}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {CIRCLE_API_KEY}"
    }
    response = requests.get(url, headers=headers)
    return response.json()["data"]["transaction"]

def execute_smart_contract(wallet_id: str, contract_address: str, abi_function_signature: str, abi_parameters: list, amount: float | None = None):
    url = "https://api.circle.com/v1/w3s/developer/transactions/contractExecution"

    payload = {
        "walletId": wallet_id,
        "contractAddress": contract_address,
        "abiFunctionSignature": abi_function_signature,
        "abiParameters": abi_parameters,
        "idempotencyKey": str(uuid.uuid4()),
        "entitySecretCiphertext": client.generate_entity_secret_ciphertext(),
        "feeLevel": "MEDIUM"
    }

    if amount is not None:
        payload["amount"] = str(amount * 1e18) # 18 decimals for ETH

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {CIRCLE_API_KEY}"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()