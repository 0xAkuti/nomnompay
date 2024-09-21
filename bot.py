import io
import os
import logging
import pathlib
from typing import Any
import dotenv
import qrcode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import telegram
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import uuid
import circle_api
import definitions as defs
import circle_api
import requests
import txt2command
import server
import threading
from constants import *

from utils import format_amount, get_ens_address

dotenv.load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

USD_EXCHANGE_RATES = requests.get('https://open.er-api.com/v6/latest/USD').json()['rates']

def compose_transfer_money_message(transactions: list[defs.Transaction]):
    if len(transactions) == 0:
        return ""
    
    output = ['Send the following transactions:']    

    for transaction in transactions:
        message_parts = [
            f'• <b>{format_amount(transaction.get_amount_usd(USD_EXCHANGE_RATES))} USDC</b>']
        if transaction.currency_type == defs.CurrencyType.FIAT:
            message_parts.append(f'({format_amount(transaction.amount)} {transaction.equivalent_currency})')
        if transaction.recipient_type == defs.RecipientType.ENS:
            message_parts.append(f'to <b>{transaction.recipient}</b> ({get_ens_address(transaction.recipient)})')
        else:
            message_parts.append(f'to <b>{transaction.recipient}</b>')
        if transaction.network != "default":
            message_parts.append(f'on {transaction.network}')
        output.append(' '.join(message_parts))
    
    return '\n'.join(output)

def create_payment_request(user: defs.User, amount: float | None = None) -> str:
    # Create payment request according to https://eips.ethereum.org/EIPS/eip-681
    
    # Get the USDC token address for the user's blockchain
    token_address = USDC_TOKEN_ADDRESSES.get(user.wallet.blockchain.value)
    if not token_address:
        raise ValueError(f"USDC token address not found for blockchain: {user.wallet.blockchain.value}")

    chain_id = CHAIN_IDS.get(user.wallet.blockchain.value)
    if not chain_id:
        raise ValueError(f"Chain ID not found for blockchain: {user.wallet.blockchain.value}")

    # Create the EIP-681 URL
    eip681_url = f"ethereum:pay-{token_address}@{chain_id}/transfer?address={user.wallet.address}"
    
    if amount:
        # USDC has 6 decimal places
        amount = int(amount * 1e6)
        eip681_url += f"&uint256={amount}"

    print(eip681_url)
    return eip681_url

class CallbackDataEntry:
    def __init__(self, telegram_id:int, data: Any):
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
    
    def verify_user(self, key: str, telegram_id: int) -> bool:
        return key in self.data and self.data[key].telegram_id == telegram_id

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
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return
    
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
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return

    if update.callback_query is None:
        logging.error(f"Invalid update object, missing callback query: {update}")
        return

    await update.callback_query.answer()

    split_command = update.callback_query.data.split(':')
    if len(split_command) != 2:
        return

    command, callback_key = split_command
    if command == 'create_wallet':
        await query_create_wallet(update, context)
        return
        
        
    if callback_key not in CALLBACK_DATA.data:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="The button is not longer valid. Please type your command again.")
        return
    # if user not in callback data send error message
    if not CALLBACK_DATA.verify_user(callback_key, update.effective_user.id):
        if command == 'confirm_send':
            type_text = 'approve'
        elif command == 'cancel_send':
            type_text = 'cancel'
        else:
            return
        allowed_user = defs.User.load_by_id(CALLBACK_DATA.data[callback_key].telegram_id)
        if allowed_user:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"@{update.effective_user.username}, you are not allowed to {type_text} this transaction. Only @{allowed_user.username} can {type_text} this transaction.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"@{update.effective_user.username}, you are not allowed to {type_text} this transaction.")
        return

    if command == 'confirm_send':
        await internal_confirm_send(update, context)
    elif command == 'cancel_send':
        await internal_cancel_send(update, context)

# queries

async def query_create_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return
    if update.callback_query is None:
        logging.error(f"Invalid update object, missing callback query: {update}")
        return
    
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
    
    user = defs.User(telegram_id=update.effective_user.id, username=update.effective_user.username or "", wallet=wallet)
    circle_api.update_wallet(wallet.id, user.username, str(user.telegram_id))
    # TODO fech wallet after update
    
    user.save(f'data/users/{user.telegram_id}.json')
    
    await query.edit_message_text(f"Wallet created successfully. {wallet.address}")

# commands

async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return
    
    user = defs.User.load_by_id(update.effective_user.id)    
    
    if user is None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have a wallet yet. Please /start the bot first.")
        return
    
    try:
        amount = float(context.args[0])
    except (ValueError, IndexError):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a valid amount to fund your wallet.")
        return
    
    eip681_url = create_payment_request(user, amount)

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(eip681_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    metamask_deep_link = f"https://metamask.app.link/send/{eip681_url}"

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=bio,
        caption=f"Scan this QR code with your mobile wallet to fund your wallet with {format_amount(amount)} USDC.\n\n<a href='{metamask_deep_link}'>Or click here to send directly via MetaMask</a>",
        parse_mode=telegram.constants.ParseMode.HTML
    )

async def show_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return
    
    user = defs.User.load_by_id(update.effective_user.id)
    
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
    
    usdc_balance = circle_api.get_user_usdc_balance(user)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"You currently have <b>{format_amount(usdc_balance)} USDC</b> in your wallet.",
        parse_mode=telegram.constants.ParseMode.HTML
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="""This bot makes easy payment to other users in USDC. 

Payment to individuals:
You can chat to the bot to send USDC to someone using only their telegram handle, e.g. Transfer 10 dollars to @alice. Pay 30k IDR to @bob. Sende @carl 15€. 
This bot supports currency conversions, all major languages and responds in English. 

Payment within a group:
To use the payment bot in a group, create your telegram group and add NomNomPaybot as admin. Text recipient's telegram handle to send payment e.g. "pay my roomie @bob $12". You can also split a bill by asking the bot to "split 150k vnd between @alice, @bob and @charlotte". Don't forget to try our Nouns sticker pack to add a splash of fun, e.g. type an emoji like 🍕 or 🚕to show the Nouns stickers
""")

async def send_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return
    
    user_id = update.effective_user.id
    
    user = defs.User.load_by_id(user_id)
    if user is None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have a wallet yet. Please start the bot first.")
        return
    
    
    if len(context.args) != 2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Please provide a recipient username and amount to send. Example: /send @{user.username} 6.50")
        return
    
    # /send @username amount
    recipient, amount = context.args
    transaction = defs.Transaction(
        recipient=recipient,
        currency="USDC",
        recipient_type=defs.RecipientType.USERNAME,
        amount=float(amount),
        currency_type=defs.CurrencyType.TOKEN,
        network="default",
        equivalent_currency=None
    )
    
    await internal_send_money(update, context, [transaction])

async def internal_send_money(update: Update, context: ContextTypes.DEFAULT_TYPE, transactions: list[defs.Transaction]):
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return
    
    user_id = update.effective_user.id
    
    user = defs.User.load_by_id(user_id)
    if user is None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have a wallet yet. Please start the bot first.")
        return
    
    users_without_wallet = []
    for transaction in transactions:
        # TODO check also wallet address and ens, not only telegram username
        if transaction.recipient_type == defs.RecipientType.USERNAME and not defs.User.load_by_username(transaction.recipient):
            users_without_wallet.append(transaction.recipient)
        elif transaction.recipient_type == defs.RecipientType.ENS and not get_ens_address(transaction.recipient):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"ENS name {transaction.recipient} does not exist.")
            return
    
    if len(users_without_wallet) > 0:
        if len(users_without_wallet) == 1:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{users_without_wallet[0]} does not have a wallet yet. Please ask them to start the bot and set one up first.")
        elif len(users_without_wallet) == 2:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{users_without_wallet[0]} and {users_without_wallet[1]} do not have a wallet yet. Please ask them to start the bot and set one up first.")
        else:
            users_without_wallet_text = ', '.join(users_without_wallet[:-1]) + ' and ' + users_without_wallet[-1]
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{users_without_wallet_text} do not have a wallet yet. Please ask them to start the bot and set one up first.")
        return

    total_amount = sum(transaction.get_amount_usd(USD_EXCHANGE_RATES) for transaction in transactions)
    if total_amount <= 0 or total_amount > circle_api.get_user_usdc_balance(user):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have enough money in your account. Check your /balance and top up.")
        return
    
    callback_key = CALLBACK_DATA.set(CallbackDataEntry(update.effective_user.id, transactions))

    keyboard = [[InlineKeyboardButton("❌", callback_data=f'cancel_send:{callback_key}'), InlineKeyboardButton("✅", callback_data=f'confirm_send:{callback_key}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=compose_transfer_money_message(transactions), reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.HTML)

async def internal_confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return
    if update.callback_query is None:
        logging.error(f"Invalid update object, missing callback query: {update}")
        return
    
    query = update.callback_query
    callback_key = query.data.split(':')[1]

    transactions = CALLBACK_DATA.get(callback_key).data

    user = defs.User.load_by_id(update.effective_user.id)
    if user is None: # should never happen
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have a wallet yet. Please start the bot first.")
        return

    transaction_ids = []
    for transaction in transactions:
        if transaction.recipient_type == defs.RecipientType.USERNAME:
            recipient_address = defs.User.load_by_username(transaction.recipient).wallet.address
        elif transaction.recipient_type == defs.RecipientType.ENS:
            recipient_address = get_ens_address(transaction.recipient)
            if recipient_address is None:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"ENS name {transaction.recipient} does not exist.")
                continue
        else:
            recipient_address = transaction.recipient
        internal_transaction_id = str(uuid.uuid4())
        response = circle_api.send_transfer(user.wallet.id, recipient_address, USDC_TOKEN_IDS[user.wallet.blockchain.value], transaction.get_amount_usd(USD_EXCHANGE_RATES), internal_transaction_id)
        transaction_ids.append(response['data']['id'])
        defs.CircleTransaction(
            id=response['data']['id'],
            user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
            state=response['data']['state'],
            transfer_type=defs.TransferType.SINGLE_CHAIN,
            transaction=transaction
        ).save(f'data/transactions/{internal_transaction_id}.json')
    
    await update.callback_query.edit_message_text(f"{update.callback_query.message.text_html}\n\n✅ Money sent successfully!", parse_mode=telegram.constants.ParseMode.HTML)
    # TODO transaction are initiated, but not completed yet, add check and update message if transaction is completed
    # TODO add webhook that informs users about incoming transfers
    # TODO handle cross chain transfer

async def internal_cancel_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query is None:
        logging.error(f"Invalid update object, missing callback query or message: {update}")
        return
    
    query = update.callback_query
    callback_key = query.data.split(':')[1]
    CALLBACK_DATA.get(callback_key) # to invalidate the confirm button
    await update.callback_query.edit_message_text(f"{update.callback_query.message.text_html}\n\n❌ Transaction cancelled.", parse_mode=telegram.constants.ParseMode.HTML)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None or update.effective_user is None:
        logging.error(f"Invalid update object, missing effective chat or user: {update}")
        return
    if update.message is None:
        logging.error(f"Invalid update object, missing message: {update}")
        return
    
    await update.effective_chat.send_action(telegram.constants.ChatAction.TYPING)

    bot_command = txt2command.parse_message(update.message.text or "")
    print(bot_command.model_dump_json(indent=4))

    match bot_command.type:
        case defs.CommandType.TRANSFER_MONEY:
            if bot_command.transactions:
                await internal_send_money(update, context, bot_command.transactions)
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Transfer command received, but no transaction details were provided."
                )

        case defs.CommandType.SHOW_BALANCE:
            await show_balance(update, context)

        case defs.CommandType.SHOW_ADDRESS:
            await show_address(update, context)

        case defs.CommandType.UNKNOWN_COMMAND:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="I'm sorry, I didn't understand that command. Can you please try again? Or check /help for more information."
            )

        case defs.CommandType.ERROR:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="An error occurred while processing your request. Please try again later."
            )

        case _:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Unexpected command type. Please try again."
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
    application.add_handler(CommandHandler('fund', fund))
    application.add_handler(CommandHandler('balance', show_balance))
    application.add_handler(CommandHandler('help', show_help))
    application.add_handler(CommandHandler('send', send_money))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    server.bot_application = application
    threading.Thread(target=server.app.run, kwargs={'port': 5000}).start()

    application.run_polling()