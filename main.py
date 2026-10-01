import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from google import genai
from google.genai import types as genai_types

# Logging ማዘጋጀት
logging.basicConfig(level=logging.INFO)

# API Keys ከ Render Environment Variables ይነበባሉ
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini Client እና Telegram Bot ማዘጋጀት
client = genai.Client(api_key=GEMINI_API_KEY)
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ቋንቋን መሠረት ያደረጉ የኢንላይን ቁልፎች
def get_main_keyboard(is_english=False):
    if is_english:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💡 About Bot", callback_data="about_en"),
                InlineKeyboardButton(text="🚀 Help", callback_data="help_en")
            ]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💡 ስለ ቦቱ", callback_data="about"),
                InlineKeyboardButton(text="🚀 መመሪያ", callback_data="help")
            ]
        ])
    return keyboard

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"👋 <b>Hello {user_name}!</b>\n\n"
        "I am an AI assistant created by <b>Zenebe Muluneh</b> and powered by <b>Google Gemini AI</b> with Web Search capabilities.\n"
        "You can ask me anything in English, Amharic, or any language!"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(is_english=True))

@dp.callback_query(F.data == "about_en")
async def about_en_callback(query: types.CallbackQuery):
    await query.message.answer("🤖 <b>About Bot:</b>\n\nDeveloped by Zenebe Muluneh, powered by Google Gemini AI with real-time web search.")
    await query.answer()

@dp.callback_query(F.data == "help_en")
async def help_en_callback(query: types.CallbackQuery):
    await query.message.answer("ℹ️ <b>Help:</b>\n\nJust type your question directly in any language. I will search the web if needed and reply instantly!")
    await query.answer()

async def keep_typing(chat_id: int):
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass

@dp.message()
async def ai_response_handler(message: types.Message):
    typing_task = asyncio.create_task(keep_typing(message.chat.id))
    
    max_retries = 3
    retry_delay = 2
    success = False

    for attempt in range(max_retries):
        try:
            # Google Search Grounding tool ን በመጠቀም ከድር ላይ መረጃዎችን እንዲፈልግ ማድረግ
            response_stream = await asyncio.to_thread(
                client.models.generate_content_stream,
                model="gemini-3.5-flash",
                contents=message.text,
                config=genai_types.GenerateContentConfig(
                    tools=[{"google_search": {}}],  # ከ Google Search መረጃዎችን እንዲቀዳ ያስችለዋል
                    temperature=0.7,
                )
            )
            
            full_text = ""
            sent_message = None
            last_update_time = asyncio.get_event_loop().time()

            for chunk in response_stream:
                if chunk.text:
                    full_text += chunk.text
                    current_time = asyncio.get_event_loop().time()
                    
                    if current_time - last_update_time > 0.8 or len(full_text) < 100:
                        if sent_message is None:
                            sent_message = await message.answer(full_text, parse_mode=None)
                        else:
                            try:
                                await sent_message.edit_text(full_text)
                            except Exception:
                                pass
                        last_update_time = current_time

            if sent_message:
                try:
                    await sent_message.edit_text(full_text)
                except Exception:
                    pass
            else:
                await message.answer(full_text, parse_mode=None)

            success = True
            break

        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                await message.answer("⚠️ <b>Sorry!</b> The server is busy right now, but I tried my best. Please send your message again.")
        
    typing_task.cancel()

async def main():
    logging.info("ቦቱ በከፍተኛ ዝግጅት መስራት ጀምሯል...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
