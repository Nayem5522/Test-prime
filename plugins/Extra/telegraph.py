import os
import requests
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

IMGBB_API_KEY = "b277202f6811a4eae0d12acc18f87347"  # আপনার Imgbb API Key

def upload_image_imgbb(image_path):
    upload_url = "https://api.imgbb.com/1/upload"
    params = {"key": IMGBB_API_KEY}

    try:
        with open(image_path, 'rb') as file:
            files = {'image': file}
            response = requests.post(upload_url, files=files, params=params)

            if response.status_code == 200:
                data = response.json()
                return data['data']['url']  # ইমেজের ডাইরেক্ট লিঙ্ক রিটার্ন করবে
            else:
                return None

    except Exception as e:
        print(f"Error during upload: {e}")
        return None

@Client.on_message(filters.command(["telegraph", "img", "cup"]) & filters.private)  # একাধিক কমান্ড যুক্ত করা হলো
async def telegraph_upload(bot, update):
    t_msg = await bot.ask(chat_id=update.from_user.id, text="Now Send Me Your Photo Or Video Under 5MB To Get Media Link.")
    if not t_msg.media:
        return await update.reply_text("**Only Media Supported.**")
    path = await t_msg.download()
    uploading_message = await update.reply_text("<b>ᴜᴘʟᴏᴀᴅɪɴɢ...</b>")
    try:
        image_url = upload_image_imgbb(path)  # Imgbb দিয়ে আপলোড করবে
        if not image_url:
            return await uploading_message.edit_text("**Failed to upload file.**")
    except Exception as error:
        await uploading_message.edit_text(f"**Upload failed: {error}**")
        return
    await uploading_message.edit_text(
        text=f"<b>Link :-</b>\n\n<code>{image_url}</code>",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup( [[
            InlineKeyboardButton(text="Open Link", url=image_url),
            InlineKeyboardButton(text="Share Link", url=f"https://telegram.me/share/url?url={image_url}")
            ],[
            InlineKeyboardButton(text="✗ Close ✗", callback_data="close")
            ]])
        )
