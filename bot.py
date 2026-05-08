# bot.py — Telegram bot interface for the F1 Race Strategy Agent
# Uses python-telegram-bot v20 (async) to wrap the agent from agent.py.
# Includes a per-user daily rate limiter: 10 strategy calls per calendar day.

import os                          # Read environment variables
import logging                     # Log info/errors to stdout for server monitoring
from datetime import date          # Compare calendar dates for the rate limiter
from dotenv import load_dotenv     # Load .env file before anything else

# Load environment variables (TELEGRAM_BOT_TOKEN, GOOGLE_API_KEY, etc.)
load_dotenv()

from telegram import Update                          # Represents an incoming Telegram update (message, command)
from telegram.ext import (
    Application,          # The main bot application class
    CommandHandler,       # Handles /start, /help etc.
    MessageHandler,       # Handles regular text messages
    filters,              # Filter messages by type (text, command, etc.)
    ContextTypes,         # Type hint helper for handler context
)

# Import the core agent logic from agent.py
from agent import run_agent

# ---------------------------------------------------------------------------
# Logging setup — logs timestamps and log level to stdout
# When running 24/7 on a server, this helps you monitor activity and debug issues
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,   # INFO level: logs normal events without being too noisy
)
logger = logging.getLogger(__name__)  # Logger scoped to this module

# ---------------------------------------------------------------------------
# Rate limiter storage — in-memory dict, no database required
# Structure: { user_id (int): {"count": int, "date": date} }
# This resets automatically per calendar day per user — no cron job needed.
# ---------------------------------------------------------------------------
user_usage: dict[int, dict] = {}

# Maximum number of strategy calls each user can make per calendar day
DAILY_LIMIT = 10


def check_rate_limit(user_id: int) -> tuple[bool, int]:
    """
    Checks whether a user has exceeded their daily call limit.

    Args:
        user_id: Telegram user ID (unique integer per user).

    Returns:
        (allowed: bool, remaining: int)
        allowed  — True if the user can make another call, False if limit hit.
        remaining — How many calls remain after this one.
    """
    today = date.today()  # Today's calendar date (resets automatically at midnight)

    if user_id not in user_usage:
        # First time we've seen this user — initialise their record
        user_usage[user_id] = {"count": 0, "date": today}

    record = user_usage[user_id]

    # If the stored date is older than today, reset the counter for the new day
    if record["date"] != today:
        record["count"] = 0         # Reset usage count
        record["date"] = today      # Update to today's date

    # Check if the user has already used all their calls today
    if record["count"] >= DAILY_LIMIT:
        return False, 0  # Not allowed, 0 calls remaining

    # User is within their limit — increment the counter and allow the call
    record["count"] += 1
    remaining = DAILY_LIMIT - record["count"]  # Calls left after this one
    return True, remaining


# ---------------------------------------------------------------------------
# /start command handler
# Sends a welcome message when the user first opens the bot
# ---------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command. Sends a welcome message."""
    welcome_text = (
        "☘️ Welcome to the F1 Race Strategy Agent!\n\n"
        "Ask me anything about race strategy — tyre management, pit windows, undercuts. "
        "You have 10 free strategy calls per day."
    )
    # Send the welcome message back to the user
    await update.message.reply_text(welcome_text)


# ---------------------------------------------------------------------------
# /help command handler
# Shows example questions the user can ask
# ---------------------------------------------------------------------------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command. Provides example questions."""
    help_text = (
        "❓ Here are 3 example questions you can ask Adrian:\n\n"
        "1️⃣ 'What is my current tyre situation and should I pit?'\n"
        "2️⃣ 'We are on lap 30 of 53 on medium tyres aged 24 laps with Sainz 2 s behind. Should we box?'\n"
        "3️⃣ 'What tyre strategy did the winner use at the 2023 Monaco Grand Prix?'\n\n"
        "ℹ️ You have 10 strategy calls per day. Calls reset at midnight."
    )
    await update.message.reply_text(help_text)


# ---------------------------------------------------------------------------
# Text message handler
# Called for every non-command message the user sends.
# Applies rate limiting, then calls run_agent() from agent.py.
# ---------------------------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text messages, applies rate limiting, and calls the agent."""
    user_id = update.effective_user.id          # Unique Telegram user ID
    user_name = update.effective_user.first_name  # Used for friendly logging
    user_text = update.message.text             # The actual question the user asked

    logger.info(f"Message from {user_name} (ID: {user_id}): {user_text}")

    # --- Rate limit check ---
    allowed, remaining = check_rate_limit(user_id)

    if not allowed:
        # User has hit their daily limit — send a polite rejection
        await update.message.reply_text(
            "You've used your 10 daily strategy calls. Come back tomorrow, engineer! ⫣️"
        )
        logger.info(f"Rate limit hit for user {user_id} ({user_name})")
        return  # Do NOT call the agent

    # --- Agent call ---
    # Send a "thinking" message so the user knows the bot is working
    thinking_msg = await update.message.reply_text("⌛ Analysing race data...")

    try:
        # Call the LangChain agent (this may take a few seconds)
        response = run_agent(user_text)

        # Build the final reply with how many calls remain today
        reply = f"☘️ Adrian: {response}\n\nℹ️ {remaining} strategy calls remaining today."

    except Exception as e:
        # If the agent throws an error, catch it gracefully
        logger.error(f"Agent error for user {user_id}: {e}")
        reply = (
            "⚠️ Something went wrong with the race analysis. "
            "Please try rephrasing your question or try again shortly."
        )

    # Delete the "thinking" placeholder message and send the real answer
    await thinking_msg.delete()
    await update.message.reply_text(reply)


# ---------------------------------------------------------------------------
# Main function — builds the bot application and starts polling for messages
# Polling means the bot continuously asks Telegram "any new messages?" every second
# For 24/7 production use, consider switching to webhooks (see python-telegram-bot docs)
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point: builds and runs the Telegram bot."""
    # Read the bot token from the .env file
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Copy .env.example to .env and add your BotFather token."
        )

    # Build the Application — this is the main bot object
    app = Application.builder().token(token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))  # /start
    app.add_handler(CommandHandler("help", help_command))    # /help

    # Register a handler for all plain text messages (non-commands)
    # filters.TEXT & ~filters.COMMAND means "text but not a slash command"
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("☘️ F1 Race Strategy Bot is running... Press Ctrl+C to stop.")

    # Start polling — the bot will run until you press Ctrl+C
    # drop_pending_updates=True: ignore any messages that arrived while bot was offline
    app.run_polling(drop_pending_updates=True)


# Only run main() when this file is executed directly (python bot.py)
if __name__ == "__main__":
    main()
