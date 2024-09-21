import json
from typing import List, Optional, Type, TypeVar
from pydantic import BaseModel, Field
from enum import Enum

import requests
import pathlib
import circle.web3.developer_controlled_wallets

Wallet = circle.web3.developer_controlled_wallets.SCAWallet

T = TypeVar('T', bound=BaseModel)

def load_json_as_model(path: str, model: Type[T]) -> T:
    with open(path, 'r') as file:
        data = json.load(file)
    return model.parse_obj(data)

def store_json_as_model(path: str, model: BaseModel):
    with open(path, 'w') as file:
        file.write(model.json())

class Blockchain(str, Enum):
    ETH = "ETH"
    ETH_SEPOLIA = "ETH-SEPOLIA"
    ARB = "ARB"
    ARB_SEPOLIA = "ARB-SEPOLIA"
    MATIC = "MATIC"
    MATIC_AMOY = "MATIC-AMOY"

class CommandType(str, Enum):
    TRANSFER_MONEY = "transfer_money"
    SHOW_BALANCE = "show_balance"
    SHOW_ADDRESS = "show_address"
    HELP = "help"
    UNKNOWN_COMMAND = "unknown_command"
    ERROR = "error"

class RecipientType(str, Enum):
    USERNAME = "username"
    ADDRESS = "address"
    ENS = "ens"

class CurrencyType(str, Enum):
    TOKEN = "token"
    FIAT = "fiat"

class Network(str, Enum):
    DEFAULT = "default"
    MAINNET = "mainnet"
    TESTNET = "testnet"

class Transaction(BaseModel):
    amount: float = Field(description="The amount of currency or equivalent_currency to be transferred")
    currency: str = Field(description="The type of currency being transferred")
    recipient: str = Field(description="The recipient of the transaction, can be a username, address, or ENS name")
    recipient_type: RecipientType = Field(description="The type of recipient")
    network: str = Field(description="The network on which the transaction is to be executed")
    currency_type: CurrencyType = Field(description="The type of currency, such as token or fiat")
    equivalent_currency: Optional[str] = Field(description="The currency in which the amount is denominated if different from the currency being transferred")
    
    def get_amount_usd(self, exchange_rates: dict[str, float]) -> float:
        if self.currency_type is CurrencyType.FIAT:
            return self.amount / exchange_rates[self.currency]
        return self.amount
    
    def get_recipient_address(self):
        if self.recipient_type is RecipientType.USERNAME:
            return self.recipient
        elif self.recipient_type is RecipientType.ADDRESS:
            return self.recipient
        elif self.recipient_type is RecipientType.ENS: # TODO add for non .eth ens names
            return requests.get(f'https://api.ensdata.net/{self.recipient}').json().get('address')

class BotCommand(BaseModel):
    type: CommandType = Field(..., description="The type of bot command")
    transactions: Optional[List[Transaction]] = Field(None, description="List of transactions (only for transfer_money type)")

class StoreableBaseModel(BaseModel):
    def save(self, path: str):
        store_json_as_model(path, self)
    
    @classmethod
    def load(cls, path: str):
        return load_json_as_model(path, cls)

class User(StoreableBaseModel):
    telegram_id: int = Field(..., description="The user's telegram ID")
    username: str = Field(..., description="The user's telegram username")
    wallet: Wallet = Field(..., description="The user's wallet")
    
    @classmethod
    def load_by_id(cls, telegram_id: int) -> 'User | None':
        try:
            return cls.load(f'data/users/{telegram_id}.json')
        except FileNotFoundError:
            return None
    
    @classmethod
    def load_by_username(cls, username: str) -> 'User | None':
        if username.startswith('@'):
            username = username[1:]
        # TODO improve this to not load all files
        for path in pathlib.Path('data/users').glob('*.json'):
            user = cls.load(str(path))
            if user.username == username:
                return user
        return None

    def pretty_print_blockchain(self):
        if self.wallet.blockchain.value == 'ETH':
            return 'Ethereum'
        elif self.wallet.blockchain.value == 'ETH-SEPOLIA':
            return 'Ethereum Sepolia'
        elif self.wallet.blockchain.value == 'ARB':
            return 'Arbitrum'
        elif self.wallet.blockchain.value == 'ARB-SEPOLIA':
            return 'Arbitrum Sepolia'
        elif self.wallet.blockchain.value == 'MATIC':
            return 'Polygon'
        elif self.wallet.blockchain.value == 'MATIC-AMOY':
            return 'Polygon Amoy'
        elif self.wallet.blockchain.value == 'SOL':
            return 'Solana'
        elif self.wallet.blockchain.value == 'SOL-DEVNET':
            return 'Solana Devnet'
        else:
            return self.wallet.blockchain.value

class Wallets(StoreableBaseModel):
    wallets: List[Wallet] = Field(..., description="The list of wallets")

