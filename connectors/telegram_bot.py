import os
import logging
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update
from telegram.error import Conflict, NetworkError
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from core.ingestion import process_and_ingest

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="I'm your AI Data Assistant! Send me notes, tasks, or ideas, and I'll ingest them into your personal memory bank."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
        
    text = msg.text
    chat_id = msg.chat_id
    msg_id = msg.message_id
    date = msg.date # datetime object
    
    # Security: Verify User Allowlist
    allowed_users_str = os.getenv("TELEGRAM_ALLOWED_USERS", "")
    allowed_users = [u.strip() for u in allowed_users_str.split(",") if u.strip()]
    if str(chat_id) not in allowed_users and str(msg.from_user.id) not in allowed_users:
        logger.warning(f"SECURITY: Unauthorized access attempt from Chat ID {chat_id} User ID {msg.from_user.id}")
        return
        
    # Store it
    source_id = f"telegram_{chat_id}_{msg_id}"
    
    try:
        success = process_and_ingest(
            content=text,
            source_type="telegram",
            created_at=date,
            source_id=source_id,
            metadata={"chat_id": chat_id, "message_id": msg_id}
        )
        
        if success:
            await context.bot.send_message(chat_id=chat_id, text="✅ Note ingested and vectorized!")
        else:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Note was skipped (already exists or empty).")
    except Exception as e:
        logger.error(f"Failed to ingest note: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ Error ingesting note.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and handle known conflict gracefully."""
    err = context.error
    if isinstance(err, Conflict):
        logger.error("Conflict: another bot instance is already running. Kill it with: pkill -f telegram_bot")
    elif isinstance(err, NetworkError):
        logger.warning(f"Network error (will retry): {err}")
    else:
        logger.error(f"Unhandled exception: {err}", exc_info=err)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN provided in .env!")
        return

    application = ApplicationBuilder().token(token).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("Starting Telegram Bot (Polling)...")
    application.run_polling()

if __name__ == '__main__':
    main()
