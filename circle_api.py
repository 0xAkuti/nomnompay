import uuid
import enum
import dotenv
import os
import requests

import definitions as defs
from constants import *

from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
import base64
import web3
from eth_abi import decode

dotenv.load_dotenv()

CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
ENTITY_SECRET = os.getenv("ENTITY_SECRET", "")
WALLET_SET_ID = os.getenv("WALLET_SET_ID")
with open("data/setup/key.pub", "r") as f:
    PUBLIC_KEY = f.read()

def generate_entity_secret_ciphertext():
    entity_secret = bytes.fromhex(ENTITY_SECRET)
    if len(entity_secret) != 32:
        raise Exception("invalid entity secret")

    # encrypt data by the public key
    public_key = RSA.importKey(PUBLIC_KEY)
    cipher_rsa = PKCS1_OAEP.new(key=public_key, hashAlgo=SHA256)
    encrypted_data = cipher_rsa.encrypt(entity_secret)

    # encode to base64
    ciphertext = base64.b64encode(encrypted_data)

    return ciphertext.decode()

def create_wallet(nr_wallets: int, blockchain: defs.Blockchain = defs.Blockchain.MATIC_AMOY) -> defs.Wallets:
    if nr_wallets > 200:
        raise ValueError("Cannot create more than 200 wallets at a time")
    
    url = "https://api.circle.com/v1/w3s/developer/wallets"


    payload = {
        "idempotencyKey": str(uuid.uuid4()),
        "accountType": "SCA",
        "blockchains": [blockchain.value],
        "count": nr_wallets,
        "entitySecretCiphertext": generate_entity_secret_ciphertext(),
        "walletSetId": WALLET_SET_ID
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {CIRCLE_API_KEY}"
    }

    response = requests.post(url, json=payload, headers=headers)
    return defs.Wallets.parse_obj(response.json()['data'])

def update_wallet(wallet_id: str, wallet_name: str, wallet_ref_id: str):
    url = f"https://api.circle.com/v1/w3s/wallets/{wallet_id}"

    payload = {
        "name": wallet_name,
        "refId": wallet_ref_id
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {CIRCLE_API_KEY}"
    }

    response = requests.put(url, json=payload, headers=headers)
    return response.json()

def get_wallet_balance(wallet_id: str):
    url = f"https://api.circle.com/v1/w3s/wallets/{wallet_id}/balances"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {CIRCLE_API_KEY}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def get_user_usdc_balance(user: defs.User) -> float:
    balances = get_wallet_balance(user.wallet.id)['data']
    for token in balances['tokenBalances']:
        if token['token']['symbol'] == 'USDC':
            return float(token['amount'])
    return 0.0

def send_transfer(wallet_id: str, recipient: str, tokenId: str, amount: float, ref_id: str):
    url = "https://api.circle.com/v1/w3s/developer/transactions/transfer"

    payload = {
        "walletId": wallet_id,
        "destinationAddress": recipient,
        "tokenId": tokenId,
        "amounts": [str(amount)],
        "idempotencyKey": str(uuid.uuid4()), # TODO create a uuid from the user request so that it can only be sent once
        "entitySecretCiphertext": generate_entity_secret_ciphertext(),
        "feeLevel": "MEDIUM",
        "refId": ref_id
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
        "entitySecretCiphertext": generate_entity_secret_ciphertext(),
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

def encode_address(address: str) -> str:
    address = address.lower().removeprefix('0x')
    if len(address) != 40:
        raise ValueError("Invalid Ethereum address length")
    address_bytes = bytes.fromhex(address)
    return '0x' + (b'\x00' * 12 + address_bytes).hex()

def cttp_burn(user: defs.User, destination_chain: defs.Blockchain, destination_address: str, amount: float):
    amount_str = str(round(amount * 1e6))
    chain = user.wallet.blockchain.value
    print(chain)
    response1 = execute_smart_contract(user.wallet.id, USDC_TOKEN_ADDRESSES[chain], "approve(address,uint256)", [CTTP_TOKEN_MESSENGER[chain], amount_str])
    
    abi_function_signature = "depositForBurn(uint256,uint32,bytes32,address)"
    encoded_destination_address = encode_address(destination_address)    
    abi_parameters = [amount_str, CCTP_DOMAINS[destination_chain.value], encoded_destination_address, USDC_TOKEN_ADDRESSES[chain]]    
    response2 = execute_smart_contract(user.wallet.id, CTTP_TOKEN_MESSENGER[chain], abi_function_signature, abi_parameters)
    
    return response1, response2

def get_message_bytes_and_hash(blockchain: defs.Blockchain, tx_hash: str) -> tuple[str, str]:
    provider = web3.Web3(web3.HTTPProvider(INFURA_ENPOINTS[blockchain.value]))
    # Get the transaction receipt
    transaction_receipt = provider.eth.get_transaction_receipt(tx_hash)

    # Create the event topic
    event_topic = web3.Web3.keccak(text='MessageSent(bytes)').hex()

    # Find the log with the matching topic
    log = next((l for l in transaction_receipt['logs'] if l['topics'][0].hex() == event_topic), None)

    if log is None:
        raise ValueError("MessageSent event not found in transaction logs")

    # Decode the log data
    message_bytes = decode(['bytes'], log['data'])[0]

    # Calculate the message hash
    message_hash = web3.Web3.keccak(message_bytes).hex()

    return f'0x{message_bytes.hex()}', f'0x{message_hash}'

def get_atttestation(message_hash: str) -> str | None:
    url = f"https://iris-api-sandbox.circle.com/v1/attestations/{message_hash}"

    headers = {"accept": "application/json"}

    response = requests.get(url, headers=headers).json()
    if response['status'] != 'complete':
        return None
    return response['attestation']

def cttp_mint(source_chain: defs.Blockchain, destination_walled_id: str, destination_chain: defs.Blockchain, tx_hash: str):
    contract_address = CTTP_MESSAGE_TRANSMITTER[destination_chain.value]
    message_bytes, message_hash = get_message_bytes_and_hash(source_chain, tx_hash)
    attestation = get_atttestation(message_hash)
    abi_function_signature = "receiveMessage(bytes,bytes)"
    abi_parameters = [message_bytes, attestation]
    return execute_smart_contract(destination_walled_id, contract_address, abi_function_signature, abi_parameters)