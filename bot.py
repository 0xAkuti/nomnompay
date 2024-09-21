import io
import os
import logging
import pathlib
import dotenv
import qrcode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import telegram
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import uuid
import circle_api
import definitions as defs
import circle_api

dotenv.load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def get_user_usdc_balance(user: defs.User) -> float:
    balances = circle_api.get_wallet_balance(user.wallet.id)['data']
    for token in balances['tokenBalances']:
        if token['token']['symbol'] == 'USDC':
            return float(token['amount'])
    return 0.0

def format_amount(amount: float) -> str:
    amount = float(amount)
    if amount.is_integer() or (amount * 100).is_integer():
        return f'{amount:,.0f}'
    return f'{amount:,.2f}'

class CallbackDataEntry:
    def __init__(self, telegram_id:int, data:dict):
        self.telegram_id = telegram_id
        self.data = data

class CallBackData:
    def __init__(self):
        self.data: dict[str, CallbackDataEntry] = {}
    
    def set(self, entry) -> str:
        key = str(uuid.uuid4())
        self.data[key] = entry
        return key
    
    def get(self, key: str):
        return self.data.pop(key)

CALLBACK_DATA = CallBackData()

def get_unregistered_wallet(blockchain: defs.Blockchain) -> defs.Wallet | None:
    fresh_wallets_path = f'data/wallets/{blockchain.value}.json'
    wallets = defs.Wallets.load(fresh_wallets_path)
    for i, wallet in enumerate(wallets.wallets):
        if wallet.ref_id is None:
            wallet = wallets.wallets.pop(i)
            wallets.save(fresh_wallets_path)
            return wallet
    return None

# commands and handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    user = defs.User.load_by_id(user_id)
    
    if user is not None:
        await update.message.reply_text(f"Welcome back {update.effective_user.first_name}! You already have a wallet.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("Ethereum", callback_data='create_wallet:ETH-SEPOLIA'),
            InlineKeyboardButton("Arbitrum", callback_data='create_wallet:ARB-SEPOLIA'),
            InlineKeyboardButton("Polygon", callback_data='create_wallet:MATIC-AMOY')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text=f"Welcome {update.effective_user.first_name}! Select a network to initialize your wallet.", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    split_command = query.data.split(':')
    if len(split_command) != 2:
        return

    command, _ = split_command

    if command == 'create_wallet':
        await query_create_wallet(update, context)

# queries

async def query_create_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if pathlib.Path(f'data/users/{update.effective_user.id}.json').exists():
        await update.message.reply_text(f"Welcome back {update.effective_user.first_name}! You already have a wallet.")
        return

    query = update.callback_query
    
    blockchain = defs.Blockchain(query.data.split(':')[1])
    wallet = get_unregistered_wallet(blockchain)
    if wallet is None:
        await query.edit_message_text("No wallets available to create.")
        # TODO batch generate new wallets if none is available
        return
    
    user = defs.User(telegram_id=update.effective_user.id, username=update.effective_user.username, wallet=wallet)
    circle_api.update_wallet(wallet.id, user.username, str(user.telegram_id))
    # TODO fech wallet after update
    
    user.save(f'data/users/{user.telegram_id}.json')
    
    await query.edit_message_text(f"Wallet created successfully. {wallet.address}")

# commands

async def show_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    user = defs.User.load_by_id(user_id)
    
    if user is None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have a wallet yet. Please /start the bot first.")
        return

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(user.wallet.address)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)

    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=bio, caption=f"Scan this QR code or use this address to fund your wallet:\n\n{user.wallet.address}\n\nOnly send USDC to this address on {user.pretty_print_blockchain()}.")

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return
    
    user_id = update.effective_user.id
    
    user = defs.User.load_by_id(user_id)
    if user is None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have a wallet yet. Please start the bot first.")
        return
    
    usdc_balance = get_user_usdc_balance(user)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"You currently have <b>{format_amount(usdc_balance)} USDC</b> in your wallet.",
        parse_mode=telegram.constants.ParseMode.HTML
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

if __name__ == '__main__':
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise ValueError("No BOT_TOKEN found in environment variables")

    application = ApplicationBuilder().token(bot_token).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('address', show_address))
    application.add_handler(CommandHandler('balance', show_balance))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    application.run_polling()