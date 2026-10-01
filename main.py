import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from google import genai

# Logging ማዘጋጀት (Render ላይ ችግር ቢፈጠር ለመመልከት)
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

# ዘመናዊ የኢንላይን ቁልፎች (Inline Keyboards)
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💡 ስለ ቦቱ", callback_data="about"),
            InlineKeyboardButton(text="🚀 መመሪያ", callback_data="help")
        ]
    ])
    return keyboard

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    welcome_text = (
        f"👋 <b>ሰላም {message.from_user.first_name}!</b>\n\n"
        "እኔ በ <b>Google Gemini AI</b> የተሰራሁ የእርስዎ ዘመናዊ ረዳት ነኝ።\n"
        "ማንኛውንም ጥያቄ፣ ጽሁፍ፣ ወይም ሃሳብ መጻፍ ይችላሉ!"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "about")
async def about_callback(query: types.CallbackQuery):
    await query.message.answer("🤖 <b>ስለ ቦቱ፦</b>\n\nይህ ቦት በላቀው Google Gemini AI ሞዴል የተጎላበተ ሲሆን 24/7 አገልግሎት ይሰጣል።")
    await query.answer()

@dp.callback_query(F.data == "help")
async def help_callback(query: types.CallbackQuery):
    await query.message.answer("ℹ️ <b>መመሪያ፦</b>\n\nምንም አይነት ትዕዛዝ መጠቀም አይጠበቅብዎትም! ጥያቄዎን በቀጥታ ይጻፉልኝ።")
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
    # ተጠቃሚው መልስ እስኪያገኝ "typing..." እንዲል ማድረግ
    typing_task = asyncio.create_task(keep_typing(message.chat.id))
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3.5-flash",  # አዲሱ ትክክለኛው የሞዴል ስም ተስተካክሏል
            contents=message.text
        )
        text = response.text
        
        # ረጅም መልሶችን እስከ 4000 ፊደላት ከፋፍሎ መላክ
        for i in range(0, len(text), 4000):
            await message.answer(text[i:i+4000], parse_mode=None)
            
    except Exception as e:
        logging.error(f"Error generating AI response: {e}")
        await message.answer("⚠️ <b>ይቅርታ!</b> መልሱን በማዘጋጀት ላይ ስህተት ተፈጥሯል። እባክዎ ትንሽ ቆይተው እንደገና ይሞክሩ።")
    finally:
        typing_task.cancel()

async def main():
    logging.info("ቦቱ መስራት ጀምሯል...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
