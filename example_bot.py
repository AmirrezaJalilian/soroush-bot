#!/usr/bin/env python3
import asyncio
import logging
from soroush_bot import Application, CommandHandler, MessageHandler, filters

logging.basicConfig(level=logging.INFO)

async def start(update, context):
    await update.message.reply_text("سلام! من ربات سروش هستم. از /help استفاده کن.")

async def help_command(update, context):
    await update.message.reply_text("دستورات:\n/start - شروع\n/help - راهنما")

async def echo_text(update, context):
    await update.message.reply_text(update.message.text)

def main():
    token = "YOUR_BOT_TOKEN"
    app = Application(token)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT, echo_text))

    app.run_polling()

if __name__ == "__main__":
    main()