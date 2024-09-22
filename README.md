# NomNomPay - ETHGlobal Singapore 2024
> The tastiest way to send USDC on Telegram
<p align="center">
  <img src="bot_pizza.png" width="200" alt="NomNomPay Bot Pizza">
</p>
NomNomPay is an AI-powered social payment app built on Telegram, utilizing Circle's programmable wallet for seamless and enjoyable peer-to-peer payments in USDC.

This project integrates Circle’s programmable wallet technology with a large language model (LLM) within the Telegram chat environment, enabling effortless payments through both direct peer-to-peer interactions and group chats using only recipients' telegram handle. Inspired by TXT2TXN, an open-source web app that pairs user intents with LLMs to facilitate blockchain transactions, NomNomPay aims to streamline the everyday use of USDC stablecoins for the average user.

With Circle’s developer-controlled wallet, users do not need to create wallets from scratch or manage their own wallets. The AI-powered payment bot interface simplifies the payment process, especially for those who are new to crypto and unfamiliar with reading transactions. This project is particularly valuable for individuals lacking access to traditional banking systems or living in countries with high inflation, making it a meaningful public good initiative.

## Product Features

1. Smart and Intuitive UX:
    - The AI chatbot allows users to interact via natural language, accurately interpreting various linguistic styles, e.g., "Transfer 10 dollars to @alice," "Pay 30k IDR to @bob," or "Send @carl 15 euros."
    - The AI model supports over 50 languages and major currency conversions within the chat.
    - Users can upload receipts to the bot, which automatically splits bills among group members.
    - USDC-based payments are processed with near-instant speed.
    - Users can securely fund their wallets by scanning a QR code or a link generated in the payment bot.
    - Voice command functionality is available and being enhanced.
    
2. Cross-Chain Payments:
    - Users can fund and receive payments on their preferred blockchain. Currently, 3 chains are supported, including Arbitrum, Polygon and Ethereum Mainnet, allowing for lower gas fees and greater flexibility. Transfers between bot users on different chains will automatically decide between normal and cross-chain transfer based on the users network.
    
3. Fun Social Features:
    - To make payments fun and increase adoption, we have integrated Nouns into a playful sticker pack to allow users to post fun captions alongside payments. e.g., " Beer money, because of priorities 🍺", "Adulting is hard, but paying rent is easier 🏠", "Sending you love (and USDC) 💖"
    - Users can request payments directly through the payment bot app or in a group chat.
    - Group payments are easily managed, allowing users to split rent, utilities, or other expenses among members, with all transactions visible in the group chat to increase engagement.
    
4. ENS Integration:
    - Users can send and receive payments using ENS addresses for a simplified and recognizable user experience.

## How to use
This bot makes easy payment to other users in USDC. 

### Payment to individuals
You can chat to the bot to send USDC to someone using only their telegram handle, e.g. Transfer 10 dollars to @alice. Pay 30k IDR to @bob. Sende @carl 15€. 
This bot supports currency conversions, all major languages and responds in English. 

### Payment within a group
To use the payment bot in a group, create your telegram group and add NomNomPaybot as admin. Text recipient's telegram handle to send payment e.g. "pay my roomie @bob $12". You can also split a bill by asking the bot to "split 150k vnd between @alice, @bob and @charlotte". Don't forget to try our Nouns sticker pack to add a splash of fun, e.g. type an emoji like 🍕 or 🚕to show the Nouns stickers

### Request payment
You can request a payment from another user by using the /request command, e.g. /request @username 10.50 [optional message]
This will send a payment request to the specified user for the given amount in USDC, along with an optional message if provided.

