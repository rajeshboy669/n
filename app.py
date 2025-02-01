import os
import re
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackContext, Dispatcher
from pymongo import MongoClient
from urllib.parse import urlparse

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADLINKFLY_API_KEY = os.getenv("ADLINKFLY_API_KEY")
ADLINKFLY_DOMAIN = os.getenv("ADLINKFLY_DOMAIN")
BLACKLISTED_DOMAINS = ["example.com", "spam.com"]  # Add blacklisted domains here
MONGO_URI = os.getenv("MONGO_URI")  # MongoDB connection URI

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client.get_database()  # Connect to the database
users_collection = db.users  # Access the 'users' collection

app = Flask(__name__)

def is_valid_url(url):
    """Check if the provided URL is well-formed"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])  # Ensure URL has a scheme (http/https) and domain
    except ValueError:
        return False

def shorten_link(url, user_api_key, alias=None):
    """Shorten the given URL using AdLinkFly API with user-specific API key"""
    if not is_valid_url(url):
        return None  # Invalid URL
    
    api_url = f"{ADLINKFLY_DOMAIN}/api?api={user_api_key}&url={url}"
    if alias:
        api_url += f"&alias={alias}"
    
    try:
        response = requests.get(api_url, timeout=10)  # Add a timeout to avoid hanging indefinitely
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        
        if data.get("status") == "success":
            return data["shortenedUrl"]
        else:
            return None
    except requests.exceptions.Timeout:
        print("Request to AdLinkFly timed out.")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    return None

def start(update: Update, context: CallbackContext):
    """Start command, ask user to provide their API key"""
    user_id = update.message.from_user.id
    
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        # Ask user for their API key
        update.message.reply_text("Please provide your API key to get started using /api <API_KEY>.")
        return
    else:
        update.message.reply_text("You are already authenticated. Use /shorten to shorten links.")

def api(update: Update, context: CallbackContext):
    """Authenticate user using their API key"""
    user_id = update.message.from_user.id
    
    if not context.args:
        update.message.reply_text("Please provide your API key.")
        return
    
    api_key = context.args[0]
    
    # Check if the API key is valid
    try:
        api_url = f"{ADLINKFLY_DOMAIN}/api?api={api_key}&url=https://example.com"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "success":
            update.message.reply_text("Invalid API key. Please try again with a valid one.")
            return
    except requests.exceptions.RequestException:
        update.message.reply_text("Failed to verify the API key. Please try again.")
        return
    
    # Store the API key in user record
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"api_key": api_key}},
        upsert=True  # If the user doesn't exist, create a new record
    )
    
    update.message.reply_text(f"Authenticated successfully with API key: {api_key}. You can now use /shorten to shorten URLs.")

def shorten(update: Update, context: CallbackContext):
    """Handle shortening a single URL provided by the user"""
    user_id = update.message.from_user.id
    
    user = users_collection.find_one({"user_id": user_id})
    if not user or "api_key" not in user:
        update.message.reply_text("You need to authenticate first using /api <API_KEY>.")
        return
    
    if not context.args:
        update.message.reply_text("Please provide a URL to shorten!")
        return
    
    original_url = context.args[0]
    alias = context.args[1] if len(context.args) > 1 else None
    user_api_key = user["api_key"]  # Get the user's own API key from the database
    
    if any(domain in original_url for domain in BLACKLISTED_DOMAINS):
        update.message.reply_text("This domain is not allowed!")
        return
    
    short_url = shorten_link(original_url, user_api_key, alias)
    
    if short_url:
        # Optionally, store the shortened URL in the user's record
        users_collection.update_one(
            {"user_id": user_id},
            {"$push": {"shortened_links": short_url}},
            upsert=True
        )
        update.message.reply_text(f"Shortened URL: {short_url}")
    else:
        update.message.reply_text("Failed to shorten the link. Please try again later!")

def view_links(update: Update, context: CallbackContext):
    """Allow users to view their previously shortened links"""
    user_id = update.message.from_user.id
    
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        update.message.reply_text("You need to authenticate first using /api <API_KEY>.")
        return
    
    shortened_links = user.get("shortened_links", [])
    
    if not shortened_links:
        update.message.reply_text("You haven't shortened any links yet.")
        return
    
    # Display the user's shortened links
    links_message = "\n".join(shortened_links)
    update.message.reply_text(f"Your shortened links:\n{links_message}")

def stats(update: Update, context: CallbackContext):
    """Get analytics for a shortened URL"""
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

def help_command(update: Update, context: CallbackContext):
    """Help command that lists all available bot commands"""
    help_text = """
    Available commands:
    /start - Start the bot
    /api <API_KEY> - Authenticate with your API key
    /shorten <URL> [alias] - Shorten a URL with an optional alias
    /view_links - View all your shortened links
    /stats <shortened_url> - Get analytics for a shortened URL
    /help - Get a list of available commands
    /features - See bot features
    /api_info - Get details about the API used for shortening links
    """
    update.message.reply_text(help_text)

def features(update: Update, context: CallbackContext):
    """List all the features of the bot"""
    update.message.reply_text("""
    Features:
    ✅ Shorten URLs with AdLinkFly
    ✅ Custom aliases for links
    ✅ Fetch link analytics
    ✅ Batch URL shortening
    ✅ Domain blacklist filtering
    ✅ Hosted on Render for high availability
    """)

def api_info(update: Update, context: CallbackContext):
    """Provide information about the API the bot uses"""
    update.message.reply_text("This bot uses the AdLinkFly API to shorten URLs. Ensure your API key is valid and your AdLinkFly instance is active.")

# Flask route to keep bot alive
@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(), bot)
        dp.process_update(update)
    return "OK"

if __name__ == "__main__":
    from telegram import Bot
    from telegram.ext import Dispatcher
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, None, use_context=True)
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("api", api))
    dp.add_handler(CommandHandler("shorten", shorten))
    dp.add_handler(CommandHandler("view_links", view_links))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("features", features))
    dp.add_handler(CommandHandler("api_info", api_info))
    
    # Run Flask app on Render
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
