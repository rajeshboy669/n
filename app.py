import os
import re
import asyncio
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADLINKFLY_API_KEY = os.getenv("ADLINKFLY_API_KEY")
ADLINKFLY_DOMAIN = os.getenv("ADLINKFLY_DOMAIN")
BLACKLISTED_DOMAINS = ["example.com", "spam.com"]

# Initialize Flask app
app = Flask(__name__)

# Initialize Telegram bot and application
bot = Bot(token=BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

# Function to shorten links using AdLinkFly API
def shorten_link(url, alias=None):
    api_url = f"{ADLINKFLY_DOMAIN}/api?api={ADLINKFLY_API_KEY}&url={url}"
    if alias:
        api_url += f"&alias={alias}"
    response = requests.get(api_url)
    data = response.json()
    
    if data.get("status") == "success":
        return data["shortenedUrl"]
    else:
        return None

# Command Handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Send me any link, and I'll shorten it for you using AdLinkFly!")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("Commands:\n/start - Start the bot\n/help - Get help information\n/shorten <url> [alias] - Shorten a URL with an optional alias\n/api - Get API usage details\n/features - See bot features\n/stats <shortened_url> - Get link analytics")

def api_info(update: Update, context: CallbackContext):
    update.message.reply_text("This bot uses the AdLinkFly API to shorten URLs. Ensure your API key is valid and your AdLinkFly instance is active.")

def features(update: Update, context: CallbackContext):
    update.message.reply_text("Features:\n✅ Shorten URLs with AdLinkFly\n✅ Custom aliases for links\n✅ Fetch link analytics\n✅ Batch URL shortening\n✅ Domain blacklist filtering\n✅ Hosted on Render for high availability")

def shorten(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Please provide a URL to shorten!")
        return
    
    original_url = context.args[0]
    alias = context.args[1] if len(context.args) > 1 else None
    
    if any(domain in original_url for domain in BLACKLISTED_DOMAINS):
        update.message.reply_text("This domain is not allowed!")
        return
    
    short_url = shorten_link(original_url, alias)
    
    if short_url:
        update.message.reply_text(short_url)
    else:
        update.message.reply_text("Failed to shorten the link. Please try again later!")

def detect_and_shorten_links(update: Update, context: CallbackContext):
    message_text = update.message.text
    urls = re.findall(r'https?://\S+', message_text)
    
    if not urls:
        return
    
    shortened_urls = []
    for url in urls:
        if any(domain in url for domain in BLACKLISTED_DOMAINS):
            continue
        short_url = shorten_link(url)
        if short_url:
            message_text = message_text.replace(url, short_url)
            shortened_urls.append(short_url)
    
    if len(shortened_urls) == 1:
        update.message.reply_text(shortened_urls[0])
    else:
        update.message.reply_text(message_text)

def get_link_stats(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Please provide a shortened URL to fetch stats.")
        return
    
    short_url = context.args[0]
    stats_api_url = f"{ADLINKFLY_DOMAIN}/api?api={ADLINKFLY_API_KEY}&url={short_url}&type=stats"
    response = requests.get(stats_api_url)
    data = response.json()
    
    if data.get("status") == "success":
        stats_message = f"📊 Stats for {short_url}:\nClicks: {data['clicks']}\nRevenue: {data['revenue']} {data['currency']}"
        update.message.reply_text(stats_message)
    else:
        update.message.reply_text("Failed to retrieve stats. Please try again later!")

# Flask route to keep bot alive and handle incoming requests
@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(), bot)
        asyncio.run(application.process_update(update))  # Use asyncio.run to await this coroutine
    return "OK"

# Async function to set webhook
async def set_webhook():
    webhook_url = "https://n-2qlu.onrender.com/"  # Replace with your actual Render URL
    await bot.set_webhook(url=webhook_url)

if __name__ == "__main__":
    # Run the async set_webhook function in an asyncio event loop
    asyncio.run(set_webhook())

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("api", api_info))
    application.add_handler(CommandHandler("features", features))
    application.add_handler(CommandHandler("shorten", shorten))
    application.add_handler(CommandHandler("stats", get_link_stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, detect_and_shorten_links))

    # Run Flask app on Render (or locally)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
