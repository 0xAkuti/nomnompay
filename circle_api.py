import dotenv
import os

from circle.web3 import developer_controlled_wallets
from circle.web3 import utils as circle_utils

dotenv.load_dotenv()

CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
ENTITY_SECRET = os.getenv("ENTITY_SECRET")

client = circle_utils.init_developer_controlled_wallets_client(api_key=CIRCLE_API_KEY, entity_secret=ENTITY_SECRET)

def create_wallet(nr_wallets: int, wallet_set_id: str, blockchain: str = 'MATIC-AMOY'):
    api_instance = developer_controlled_wallets.WalletsApi(client)

    if nr_wallets > 20:
        raise ValueError("Cannot create more than 20 wallets at a time")

    try:
        request = developer_controlled_wallets.CreateWalletRequest.from_dict({
            "accountType": 'SCA',
            "blockchains": [blockchain],
            "count": nr_wallets,
            "walletSetId": wallet_set_id
        })
        api_instance.create_wallet(request) # TODO does not actually return wallets as it's supposed to

        return api_instance.get_wallets(page_size=nr_wallets)

    except developer_controlled_wallets.ApiException as e:
        print(f"Exception when calling WalletsApi->create_wallet: {e}")
        return None