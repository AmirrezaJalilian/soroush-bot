#!/usr/bin/env python3
import asyncio
import logging
import sqlite3
import os
from typing import Dict, Optional, Tuple
from soroush_bot import Application, CommandHandler, CallbackQueryHandler, filters
from soroush_bot.types import InlineKeyboardButton, InlineKeyboardMarkup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "tap_bot.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            score INTEGER DEFAULT 0,
            first_name TEXT,
            username TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user_score(user_id: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT score FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['score']
    return 0

def update_user_score(user_id: int, new_score: int, first_name: str = "", username: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, score, first_name, username)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            score = excluded.score,
            first_name = COALESCE(excluded.first_name, first_name),
            username = COALESCE(excluded.username, username)
    ''', (user_id, new_score, first_name, username))
    conn.commit()
    conn.close()

def get_leaderboard(limit: int = 10) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, score, first_name, username
        FROM users
        ORDER BY score DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

async def start(update, context):
    user_id = update.message.from_user.id
    first_name = update.message.from_user.first_name or "کاربر"
    username = update.message.from_user.username or ""
    score = get_user_score(user_id)
    if score == 0:
        update_user_score(user_id, 0, first_name, username)

    keyboard = [
        [InlineKeyboardButton("👆 ضربه بزن!", callback_data="tap")],
        [InlineKeyboardButton("🏆 جدول رهبری", callback_data="leaderboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🎮 سلام {first_name}!\n"
        f"امتیاز شما: {score}\n\n"
        "روی دکمه‌ی زیر ضربه بزنید تا امتیاز بگیرید!",
        reply_markup=reply_markup
    )

async def tap_callback(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    first_name = query.from_user.first_name or "کاربر"
    username = query.from_user.username or ""

    current_score = get_user_score(user_id)
    new_score = current_score + 1
    update_user_score(user_id, new_score, first_name, username)

    keyboard = [
        [InlineKeyboardButton("👆 ضربه بزن!", callback_data="tap")],
        [InlineKeyboardButton("🏆 جدول رهبری", callback_data="leaderboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🎯 ضربه ثبت شد!\n"
        f"امتیاز شما: {new_score}\n\n"
        "به ضربه‌زدن ادامه دهید!",
        reply_markup=reply_markup
    )

async def leaderboard_callback(update, context):
    query = update.callback_query
    await query.answer()

    leaderboard_data = get_leaderboard(10)

    if not leaderboard_data:
        await query.edit_message_text("هنوز هیچ امتیازی ثبت نشده است! اولین نفر باشید.")
        return

    leaderboard_text = "🏆 **جدول رهبری**\n\n"
    for i, row in enumerate(leaderboard_data, 1):
        name = row['first_name'] or f"کاربر {row['user_id']}"
        if row['username']:
            name = f"@{row['username']}"
        leaderboard_text += f"{i}. {name}: {row['score']} امتیاز\n"

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_game")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        leaderboard_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def back_to_game_callback(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    score = get_user_score(user_id)

    keyboard = [
        [InlineKeyboardButton("👆 ضربه بزن!", callback_data="tap")],
        [InlineKeyboardButton("🏆 جدول رهبری", callback_data="leaderboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🎮 امتیاز شما: {score}\n\n"
        "روی دکمه‌ی زیر ضربه بزنید تا امتیاز بگیرید!",
        reply_markup=reply_markup
    )

def main():
    init_db()
    logger.info("دیتابیس SQLite مقداردهی شد.")

    token = "YOUR_BOT_TOKEN"
    app = Application(token)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler("tap", tap_callback))
    app.add_handler(CallbackQueryHandler("leaderboard", leaderboard_callback))
    app.add_handler(CallbackQueryHandler("back_to_game", back_to_game_callback))

    logger.info("ربات Tap to Earn با دیتابیس SQLite راه‌اندازی شد!")
    app.run_polling()

if __name__ == "__main__":
    main()