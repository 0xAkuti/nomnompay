import os
import logging
import dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import uuid
import circle_api
import json
from typing import Type, TypeVar
from pydantic import BaseModel
import definitions as defs
import circle_api

dotenv.load_dotenv()

T = TypeVar('T', bound=BaseModel)

def load_json_as_model(path: str, model: Type[T]) -> T:
    with open(path, 'r') as file:
        data = json.load(file)
    return model.parse_obj(data)

def store_json_as_model(path: str, model: BaseModel):
    with open(path, 'w') as file:
        file.write(model.json())

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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
    wallets = load_json_as_model(fresh_wallets_path, defs.Wallets)
    for i, wallet in enumerate(wallets.wallets):
        if wallet.ref_id is None:
            wallet = wallets.wallets.pop(i)
            store_json_as_model(fresh_wallets_path, wallets)
            return wallet
    return None

# commands and handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        user = load_json_as_model(f'data/users/{user_id}.json', defs.User)
    except FileNotFoundError:
        user = None
    
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


async def query_create_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    blockchain = defs.Blockchain(query.data.split(':')[1])
    wallet = get_unregistered_wallet(blockchain)
    if wallet is None:
        await query.edit_message_text("No wallets available to create.")
        return
    
    user = defs.User(telegram_id=update.effective_user.id, username=update.effective_user.username, wallet=wallet)
    circle_api.update_wallet(wallet.id, user.username, str(user.telegram_id))
    # TODO fech wallet after update
    
    store_json_as_model(f'data/users/{user.telegram_id}.json', user)
    
    await query.edit_message_text(f"Wallet created successfully. {wallet.address}")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

if __name__ == '__main__':
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise ValueError("No BOT_TOKEN found in environment variables")

    application = ApplicationBuilder().token(bot_token).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    application.run_polling()