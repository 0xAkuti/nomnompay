from flask import Flask, request, jsonify
import telegram
from telegram.ext import Application
import json
import asyncio
import definitions as defs
import requests
from constants import *

app = Flask(__name__)
bot_application: Application = None  # This will be set when the bot starts

def format_amount(amount: float) -> str:
    amount = float(amount)
    if amount.is_integer():
        return f'{amount:,.0f}'
    return f'{amount:,.2f}'

@app.route('/circle-webhook', methods=['POST'])
def circle_webhook():
    data = request.json
    asyncio.run(handle_circle_webhook(data))
    return jsonify({"status": "success"}), 200

async def handle_circle_webhook(data):
    if not bot_application:
        print("Bot application not initialized")
        return
    
    notification_type = data.get('notificationType')
    notification = data['notification']
    if notification_type == 'transactions.inbound':
        await handle_inbound_transaction(notification)
        return
    if notification_type == 'transactions.outbound':
        await handle_outbound_transaction(notification)
        return

async def handle_inbound_transaction(notification):
    print('Received INBOUND transaction')
    if notification['state'] == 'CONFIRMED':
        wallet_id = notification['walletId']
        amount = float(notification['amounts'][0])
        user = defs.User.load_by_wallet_id(wallet_id)
        sender = defs.User.load_by_wallet_address(notification['sourceAddress'])
        
        # inbound does not have a refId
        message_parts = f"You just received <b>{format_amount(amount)} USDC</b>"
        if sender:
            message_parts += f" from @{sender.username}"
        else:
            message_parts += f" from {notification['sourceAddress']}"
        if user:
            await bot_application.bot.send_message(
                chat_id=user.telegram_id,
                text=message_parts,
                parse_mode=telegram.constants.ParseMode.HTML
            )
        else:
            print(f"User not found for wallet ID: {wallet_id}")

async def handle_outbound_transaction(notification):
    ...
if __name__ == '__main__':
    app.run(port=5000)  # Run on port 5000