from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

import requests
import circle.web3.developer_controlled_wallets

Wallet = circle.web3.developer_controlled_wallets.SCAWallet

class Blockchain(str, Enum):
    ETH = "ETH"
    ETH_SEPOLIA = "ETH-SEPOLIA"
    ARB = "ARB"
    ARB_SEPOLIA = "ARB-SEPOLIA"
    MATIC = "MATIC"
    MATIC_AMOY = "MATIC-AMOY"

class User(BaseModel):
    telegram_id: int = Field(..., description="The user's telegram ID")
    username: str = Field(..., description="The user's telegram username")
    wallet: Wallet = Field(..., description="The user's wallet")

class Wallets(BaseModel):
    wallets: List[Wallet] = Field(..., description="The list of wallets")

