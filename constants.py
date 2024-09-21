import dotenv
import os

dotenv.load_dotenv()

INFURA_API_KEY = os.getenv("INFURA_API_KEY")

USDC_TOKEN_ADDRESSES = {
    # https://developers.circle.com/stablecoins/docs/usdc-on-test-networks
    "ETH-SEPOLIA": '0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238',
    "ARB-SEPOLIA": '0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d',
    "MATIC-AMOY": '0x41e94eb019c0762f9bfcf9fb1e58725bfb0e7582',
    # https://developers.circle.com/stablecoins/docs/usdc-on-main-networks
    "ETH": '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
    "ARB": '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
    "MATIC": '0x3c499c542cef5e3811e1192ce70d8cc03d5c3359',
}

USDC_TOKEN_IDS = {
    "ETH-SEPOLIA": '',
    "ARB-SEPOLIA": '4b8daacc-5f47-5909-a3ba-30d171ebad98',
    "MATIC-AMOY": '36b6931a-873a-56a8-8a27-b706b17104ee',
    "ETH": '',
    "ARB": '',
    "MATIC": '',
}

CHAIN_IDS = {
    "ETH-SEPOLIA": 11155111,
    "ARB-SEPOLIA": 421614,
    "MATIC-AMOY": 80002,
    "ETH": 1,
    "ARB": 42161,
    "MATIC": 137,
}

CCTP_DOMAINS = {
    "ETH": "0",
    "ETH-SEPOLIA": "0",
    "ARB": "3",
    "ARB-SEPOLIA": "3",
    "MATIC": "7",
    "MATIC-AMOY": "7"
}

CTTP_TOKEN_MESSENGER = {
    "ETH": "0xbd3fa81b58ba92a82136038b25adec7066af3155",
    "ETH-SEPOLIA": "0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5",
    "ARB": "0x19330d10D9Cc8751218eaf51E8885D058642E08A",
    "ARB-SEPOLIA": "0xaCF1ceeF35caAc005e15888dDb8A3515C41B4872",
    "MATIC": "0x9daF8c91AEFAE50b9c0E69629D3F6Ca40cA3B3FE",
    "MATIC-AMOY": "0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5"
}

CTTP_MESSAGE_TRANSMITTER = {
    "ETH": "0x0a992d191deec32afe36203ad87d7d289a738f81",
    "ETH-SEPOLIA": "0x7865fAfC2db2093669d92c0F33AeEF291086BEFD",
    "ARB": "0xC30362313FBBA5cf9163F0bb16a0e01f01A896ca",
    "ARB-SEPOLIA": "0xaCF1ceeF35caAc005e15888dDb8A3515C41B4872",
    "MATIC": "0xF3be9355363857F3e001be68856A2f96b4C39Ba9",
    "MATIC-AMOY": "0x7865fAfC2db2093669d92c0F33AeEF291086BEFD"
}

USDC_TOKEN_ADDRESSES = { # TODO duplicate with bot.py, move into constants file
    # https://developers.circle.com/stablecoins/docs/usdc-on-test-networks
    "ETH-SEPOLIA": '0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238',
    "ARB-SEPOLIA": '0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d',
    "MATIC-AMOY": '0x41e94eb019c0762f9bfcf9fb1e58725bfb0e7582',
    # https://developers.circle.com/stablecoins/docs/usdc-on-main-networks
    "ETH": '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
    "ARB": '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
    "MATIC": '0x3c499c542cef5e3811e1192ce70d8cc03d5c3359',
}

INFURA_ENPOINTS = {
    "ETH": f"https://mainnet.infura.io/v3/{INFURA_API_KEY}",
    "ETH-SEPOLIA": f"https://sepolia.infura.io/v3/{INFURA_API_KEY}",
    "ARB": f"https://arbitrum-mainnet.infura.io/v3/{INFURA_API_KEY}",
    "ARB-SEPOLIA": f"https://arbitrum-sepolia.infura.io/v3/{INFURA_API_KEY}",
    "MATIC": f"https://polygon-mainnet.infura.io/v3/{INFURA_API_KEY}",
    "MATIC-AMOY": f"https://polygon-amoy.infura.io/v3/{INFURA_API_KEY}",
}