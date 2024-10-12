from datetime import datetime
import json
from typing import List, Optional, Type, TypeVar
from pydantic import BaseModel, Field, StrictStr
from enum import Enum

import requests
import pathlib


T = TypeVar('T', bound=BaseModel)
DECIMALS = 6

def load_json_as_model(path: str, model: Type[T]) -> T:
    with open(path, 'r') as file:
        return model.model_validate_json(file.read())

def store_json_as_model(path: str, model: BaseModel):
    with open(path, 'w') as file:
        file.write(model.model_dump_json())

class StoreableBaseModel(BaseModel):
    def save(self, path: str):
        store_json_as_model(path, self)
    
    @classmethod
    def load(cls, path: str):
        return load_json_as_model(path, cls)

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
    REQUEST = "request"
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
            if self.equivalent_currency is None:
                raise ValueError("equivalent_currency is required for fiat currency")
            return round(self.amount / exchange_rates[self.equivalent_currency], DECIMALS)
        return round(self.amount, DECIMALS)
    
    def get_recipient_address(self):
        if self.recipient_type is RecipientType.USERNAME:
            return self.recipient
        elif self.recipient_type is RecipientType.ADDRESS:
            return self.recipient
        elif self.recipient_type is RecipientType.ENS: # TODO add for non .eth ens names
            return requests.get(f'https://api.ensdata.net/{self.recipient}').json().get('address')

class Request(BaseModel):
    target_username: str = Field(description="The username of the user to request from")
    amount: float = Field(description="The amount of currency to request")
    currency: str = Field(description="The type of currency to request")
    equivalent_currency: Optional[str] = Field(description="The currency in which the amount is denominated if different from the currency being transferred")
    message: Optional[str] = Field(description="An optional message to include in the request")
    
    def get_amount_usd(self, exchange_rates: dict[str, float]) -> float:
        if self.equivalent_currency:
            return round(self.amount / exchange_rates[self.equivalent_currency], DECIMALS)
        return round(self.amount, DECIMALS)

class BotCommand(BaseModel):
    type: CommandType = Field(..., description="The type of bot command")
    transactions: Optional[List[Transaction]] = Field(None, description="List of transactions (only for transfer_money type)")
    request: Optional[Request] = Field(None, description="A request to be sent to the target user")

class CustodyType(str, Enum):
    DEVELOPER = 'DEVELOPER'
    ENDUSER = 'ENDUSER'

class WalletState(str, Enum):
    LIVE = 'LIVE'
    FROZEN = 'FROZEN'

class Wallet(BaseModel):
    id: StrictStr = Field(..., description="System-generated unique identifier of the resource.")
    address: StrictStr = Field(..., description="Blockchain address of the wallet.")
    blockchain: Blockchain = Field(...)
    create_date: datetime = Field(..., alias="createDate", description="Date and time the resource was created, in ISO-8601 UTC format.")
    update_date: datetime = Field(..., alias="updateDate", description="Date and time the resource was last updated, in ISO-8601 UTC format.")
    custody_type: CustodyType = Field(..., alias="custodyType")
    name: Optional[StrictStr] = Field(None, description="Optional name or description associated with the wallet.")
    ref_id: Optional[StrictStr] = Field(None, alias="refId", description="Reference or description used to identify the object.")
    state: WalletState = Field(...)
    user_id: Optional[StrictStr] = Field(None, alias="userId", description="Unique system generated identifier for the user.")
    wallet_set_id: StrictStr = Field(..., alias="walletSetId", description="System-generated unique identifier of the resource.")
    account_type: StrictStr = Field(..., alias="accountType", description="An account can be a Smart Contract Account (SCA) or an Externally Owned Account (EOA). To learn more, see the [account types guide](https://developers.circle.com/w3s/docs/programmable-wallets-account-types).  If an account type is not specified during the creation of a wallet, it defaults to `EOA` (Externally Owned Account). Note that Solana doesn't support Smart Contract Account (SCA). ")
    sca_core: StrictStr = Field(..., alias="scaCore", description="SCAs can have different versions that have different functionality. SCACore will display the version of the SCA being created. Please refer to developer docs for a list of the versions supported.")
    __properties = ["id", "address", "blockchain", "createDate", "updateDate", "custodyType", "name", "refId", "state", "userId", "walletSetId", "accountType", "scaCore"]

    class Config:
        alias_generator = lambda string: ''.join(word.capitalize() for word in string.split('_'))
        populate_by_name = True

class Wallets(StoreableBaseModel):
    wallets: List[Wallet] = Field(..., description="The list of wallets")

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
    
    @classmethod
    def load_by_wallet_id(cls, wallet_id: str) -> 'User | None':
        for path in pathlib.Path('data/users').glob('*.json'):
            user = cls.load(str(path))
            if user and user.wallet.id == wallet_id:
                return user
        return None

    @classmethod
    def load_by_wallet_address(cls, wallet_address: str) -> 'User | None':
        for path in pathlib.Path('data/users').glob('*.json'):
            user = cls.load(str(path))
            if user and user.wallet.address == wallet_address:
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

class TransferType(str, Enum):
    SINGLE_CHAIN = "SINGLE-CHAIN"
    CROSS_CHAIN = "CROSS-CHAIN"
    
class CircleTransaction(StoreableBaseModel):
    id: str = Field(..., description="The ID of the transaction")
    state: str = Field(..., description="The state of the transaction")
    user_id: int = Field(..., description="The ID of the user who initiated the transaction")
    chat_id: int = Field(..., description="The ID of the chat where the transaction was initiated")
    message_id: int = Field(..., description="The ID of the message in the user's chat where the transaction was initiated")
    transfer_type: TransferType = Field(..., description="The type of transfer")
    transaction: Transaction
