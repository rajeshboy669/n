import os
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)

async def start(update: Update, context) -> None:
    message = (
        "I am nanolinks.in , Bulk Link Converter. I Can Convert Links Directly From Your nanolinks.in Account,\n\n"
        "1. Go To 👉 https://nanolinks.in/member/tools/api\n"
        "2. Then Copy API Key\n"
        "3. Then Type /api then give a single space and then paste your API Key (see example to understand more...)\n"
        "4. How to use nanolinks bot- use this video for reference 👉 https://t.me/nanolinks/2\n\n"
        "(See Example.👇)\n"
        "Example: /api 04e8ee10b5f123456a640c8f33195abc\n\n"
        "🤘 Hit 👉 /features To Know More Features Of This Bot.\n"
        "🔗 Hit 👉 /link To Know More About How To Link nanolinks.in Account To This Bot.\n"
        "💁‍♀ Hit 👉 /help To Get Help.\n"
        "➕ Hit 👉 /add Command To Get Help About Adding your channel to bot.\n"
        "➕ Hit 👉 /footer To Get Help About Adding your Custom Footer to bot.\n\n"
        "Anyone who want to use any other shortener instead of nanolinks.in, contact at 👉 @filmy_boyy (all shortener support available.)\n\n"
        "- Made With ❤️ By @filmy_boyy -"
    )
    await update.message.reply_text(message)

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    """Process Telegram updates"""
    data = request.get_json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return "OK", 200

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
