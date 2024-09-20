import dotenv
import os

from circle.web3 import developer_controlled_wallets
from circle.web3 import utils as circle_utils

dotenv.load_dotenv()

CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
ENTITY_SECRET = os.getenv("ENTITY_SECRET")
WALLET_SET_ID = os.getenv("WALLET_SET_ID")

client = circle_utils.init_developer_controlled_wallets_client(api_key=CIRCLE_API_KEY, entity_secret=ENTITY_SECRET)

def create_wallet(nr_wallets: int, blockchain: str = 'MATIC-AMOY') -> list[developer_controlled_wallets.SCAWallet]:
    api_instance = developer_controlled_wallets.WalletsApi(client)

    if nr_wallets > 20:
        raise ValueError("Cannot create more than 20 wallets at a time")

    try:
        request = developer_controlled_wallets.CreateWalletRequest.from_dict({
            "accountType": 'SCA',
            "blockchains": [blockchain],
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