import uuid
import enum
import dotenv
import os

from circle.web3 import developer_controlled_wallets
from circle.web3 import utils as circle_utils
import requests

dotenv.load_dotenv()

CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
ENTITY_SECRET = os.getenv("ENTITY_SECRET")
WALLET_SET_ID = os.getenv("WALLET_SET_ID")

class Blockchain(str, enum.Enum):
    ETH = "ETH"
    ETH_SEPOLIA = "ETH-SEPOLIA"
    ARB = "ARB"
    ARB_SEPOLIA = "ARB-SEPOLIA"
    MATIC = "MATIC"
    MATIC_AMOY = "MATIC-AMOY"

client = circle_utils.init_developer_controlled_wallets_client(api_key=CIRCLE_API_KEY, entity_secret=ENTITY_SECRET)

def create_wallet(nr_wallets: int, blockchain: Blockchain = Blockchain.MATIC_AMOY) -> list[developer_controlled_wallets.SCAWallet]:
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

        return [wallet.actual_instance for wallet in api_instance.get_wallets(page_size=nr_wallets).data.wallets]

    except developer_controlled_wallets.ApiException as e:
        print(f"Exception when calling WalletsApi->create_wallet: {e}")
        return []

def update_wallets(wallet_id: str, wallet_name: str, wallet_ref_id: str) -> bool:
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

def send_transfer(wallet_id: str, recipient: str, token: str, amount: str):
    url = "https://api.circle.com/v1/w3s/developer/transactions/transfer"

    payload = {
        "walletId": wallet_id,
        "destinationAddress": recipient,
        "tokenAddress": token,
        "amounts": [amount],
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
    return response.json()

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
        payload["amount"] = str(amount * 1e18) # assuming 18 decimals for the token

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {CIRCLE_API_KEY}"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()