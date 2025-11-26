import re
import hashlib
import requests
import textwrap
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# আপনার প্রয়োজনীয় ইম্পোর্টস
from info import * 
from utils import * 
from database.ia_filterdb import save_file

# --- GLOBAL SETTINGS & STORAGE ---

# 1. LANGUAGE MAP
LANG_MAP = {
    "hi": "Hindi", "hin": "Hindi", "hindi": "Hindi",
    "en": "English", "eng": "English", "english": "English",
    "bn": "Bengali", "ban": "Bengali", "ben": "Bengali", "bengali": "Bengali",
    "tm": "Tamil", "tam": "Tamil", "tamil": "Tamil",
    "te": "Telugu", "tel": "Telugu", "telugu": "Telugu",
    "ml": "Malayalam", "mal": "Malayalam", "malayalam": "Malayalam",
    "kn": "Kannada", "kan": "Kannada", "kannada": "Kannada",
    "mr": "Marathi", "marathi": "Marathi",
    "pa": "Punjabi", "punjabi": "Punjabi",
    "gu": "Gujarati", "gujarati": "Gujarati",
    "ko": "Korean", "korean": "Korean",
    "ja": "Japanese", "japanese": "Japanese",
    "es": "Spanish", "spanish": "Spanish",
    "fr": "French", "french": "French",
    "ur": "Urdu", "urdu": "Urdu",
    "dual": "Dual Audio", "multi": "Multi Audio"
}

# Global Variables
notified_movies = {} 
user_reactions = {}
reaction_counts = {}
movie_slugs = {} 

media_filter = filters.document | filters.video | filters.audio

# ====================================================================
# 1. OLD HANDLER (CHANNELS)
# ====================================================================

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media_old(bot, message):
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return
    media.file_type = file_type
    media.caption = message.caption
    await save_file(media)

# ====================================================================
# 2. NEW HANDLER (UPCHANNELS - With Update Post)
# ====================================================================

@Client.on_message(filters.chat(UPCHANNELS) & media_filter)
async def media_new(bot, message):
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return
    media.file_type = file_type
    media.caption = message.caption
    
    try:
        success, silentxbotz = await save_file(bot, media)
    except:
        await save_file(media)
        success = True 

    try:  
        if success:            
            await send_movie_update(bot, file_name=media.file_name, caption=media.caption)
    except Exception as e:
        print(f"Error In Movie Update - {e}")
        pass

# ====================================================================
# 3. CORE FUNCTIONS (Main Logic)
# ====================================================================

async def send_movie_update(bot, file_name, caption):
    try:
        # --- 1. Smart Link & Check ---
        link_slug = await get_smart_link_slug(file_name)
        unique_id = generate_unique_id(link_slug)
        
        current_time = datetime.now()
        # ডুপ্লিকেট চেকিং (৫ দিন)
        if unique_id in notified_movies:
            last_posted_time = notified_movies[unique_id]
            if (current_time - last_posted_time) < timedelta(days=5):
                print(f"Skipping update for {link_slug}: Posted recently.")
                return 
        
        notified_movies[unique_id] = current_time
        movie_slugs[unique_id] = link_slug

        # --- 2. Initial Data Extraction (Filename Based) ---
        file_title, file_year = await extract_info_from_filename(file_name)
        season_info = await get_season_episode(file_name) # সিজন ইনফো বের করা
        
        # সার্চের জন্য সিজন/এপিসোড এবং ফালতু শব্দ বাদ দেওয়া
        search_query = await clean_search_query(file_title) 
        
        # --- 3. Fetch Data from TMDB ---
        # বছর পেলে সেটা সহ সার্চ, না পেলে শুধু নাম
        tmdb_year_param = file_year if file_year != "N/A" else None
        tmdb_data = await fetch_tmdb_data(search_query, tmdb_year_param)
        
        # --- 4. Final Data Setup (Fallback Logic) ---
        
        if tmdb_data:
            # TMDB ডাটা পাওয়া গেলে
            title = tmdb_data.get("title")
            overview = tmdb_data.get("overview", "")
            rating = tmdb_data.get("vote_average", 0)
            genres = tmdb_data.get("genres", "")
            poster = tmdb_data.get("poster")
            release_year = tmdb_data.get("release_date", "")[:4]
            display_year = release_year if release_year else file_year
        else:
            # TMDB ডাটা না পাওয়া গেলে (Fallback)
            title = file_title
            overview = "" 
            rating = 0
            genres = ""
            poster = None # ছবি নেই
            display_year = file_year

        # ভাষা এবং কোয়ালিটি সবসময় ফাইল থেকেই নেওয়া হবে
        language = await get_formatted_language(file_name, caption)
        quality = await get_qualities(file_name + " " + (caption or ""))
        
        if language == "Unknown":
            language = "Not Sure"

        if unique_id not in reaction_counts:
            reaction_counts[unique_id] = {"❤️": 0, "👍": 0, "👎": 0, "🔥": 0}
            user_reactions[unique_id] = {}

        # --- 5. DESIGN SECTION ---
        
        full_caption = "#𝑵𝒆𝒘_𝑪𝒐𝒏𝒕𝒆𝒏𝒕_𝑨𝒅𝒅𝒆𝒅 💌\n\n╭─━━━⌁ 𝘾𝙊𝙉𝙏𝙀𝙉𝙏 𝙄𝙉𝙁𝙊 ⌁━━━─╮\n"
        full_caption += f"│ 📂 𝐓𝐢𝐭𝐥𝐞: <b>{title}</b>\n"
        
        if genres: 
            full_caption += f"│ 🎭 𝐆𝐞𝐧𝐫𝐞: {genres}\n"
            
        if rating and str(rating) != "0" and str(rating) != "0.0":
            full_caption += f"│ ⭐ 𝐑𝐚𝐭𝐢𝐧𝐠: {rating}/10\n"
            
        # সিজন ইনফো থাকলে দেখাবে, না থাকলে নাই
        if season_info:
            full_caption += f"│ 📺 𝐒𝐞𝐚𝐬𝐨𝐧: {season_info}\n"

        full_caption += f"│ 💎 𝐐𝐮𝐚𝐥𝐢𝐭𝐲: <b>{quality}</b>\n"
        full_caption += f"│ 🔊 𝐀𝐮𝐝𝐢𝐨: {language}\n"
        
        if display_year and display_year != "N/A":
            full_caption += f"│ 📅 𝐘𝐞𝐚𝐫: {display_year}\n"
            
        # Story Section
        if overview and len(overview) > 10:
            full_caption += "├╌╌╌╌╌╌╌ 𝐒𝐓𝐎𝐑𝐘 ╌╌╌╌╌╌╌┤\n"
            short_overview = overview[:250] + "..." if len(overview) > 250 else overview
            full_caption += f"│ {short_overview}\n"
        
        full_caption += "╰━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        
        full_caption += "╭─━━━━⌁ ᴇɴɢᴀɢᴇ ᴡɪᴛʜ ᴘᴏꜱᴛ ⌁━━━━─╮\n"
        full_caption += "┃ ♡ 𝐋𝐢𝐤𝐞  ❍ 𝐂𝐨𝐦𝐦𝐞𝐧𝐭  ⎙ 𝐒𝐚𝐯𝐞  ⌲ 𝐒𝐡𝐚𝐫𝐞\n"
        full_caption += "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        
        full_caption += "        ⬇️ <b>Get File Below</b> ⬇️"

        # --- 6. Buttons ---
        buttons = [[
            InlineKeyboardButton(f"❤️ {reaction_counts[unique_id]['❤️']}", callback_data=f"r_{unique_id}_h"),
            InlineKeyboardButton(f"👍 {reaction_counts[unique_id]['👍']}", callback_data=f"r_{unique_id}_l"),
            InlineKeyboardButton(f"👎 {reaction_counts[unique_id]['👎']}", callback_data=f"r_{unique_id}_d"),
            InlineKeyboardButton(f"🔥 {reaction_counts[unique_id]['🔥']}", callback_data=f"r_{unique_id}_f")
        ], [
            InlineKeyboardButton('📂 Get File 📂', url=f'https://telegram.me/MH_Movie_Seach_Bot?start=getfile-{link_slug}')
        ]]

        if poster:
            await bot.send_photo(chat_id=MOVIE_UPDATE_CHANNEL, photo=poster, caption=full_caption, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            # ছবি না পেলে টেক্সট মেসেজ যাবে (কোনো ডিফল্ট ছবি নেই)
            await bot.send_message(chat_id=MOVIE_UPDATE_CHANNEL, text=full_caption, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    except Exception as e:
        print(f"Error in send_movie_update: {e}")

# --- Reaction Callback Handler ---
@Client.on_callback_query(filters.regex(r"^r_"))
async def reaction_handler(client, query):
    try:
        data = query.data.split("_")
        if len(data) != 3: return        
        
        unique_id = data[1]
        short_code = data[2]
        user_id = query.from_user.id
        
        code_map = {"h": "❤️", "l": "👍", "d": "👎", "f": "🔥"}
        if short_code not in code_map: return
        new_emoji = code_map[short_code]
        
        link_slug = movie_slugs.get(unique_id)
        if not link_slug:
            await query.answer("Bot restarted or Link Expired", show_alert=True)
            return

        if unique_id not in reaction_counts:
            reaction_counts[unique_id] = {"❤️": 0, "👍": 0, "👎": 0, "🔥": 0}
            user_reactions[unique_id] = {}

        if user_id in user_reactions[unique_id]:
            old_emoji = user_reactions[unique_id][user_id]
            if old_emoji == new_emoji:
                await query.answer("You already reacted!", show_alert=False)
                return 
            else:
                reaction_counts[unique_id][old_emoji] -= 1
        
        user_reactions[unique_id][user_id] = new_emoji
        reaction_counts[unique_id][new_emoji] += 1
        
        updated_buttons = [[
            InlineKeyboardButton(f"❤️ {reaction_counts[unique_id]['❤️']}", callback_data=f"r_{unique_id}_h"),
            InlineKeyboardButton(f"👍 {reaction_counts[unique_id]['👍']}", callback_data=f"r_{unique_id}_l"),
            InlineKeyboardButton(f"👎 {reaction_counts[unique_id]['👎']}", callback_data=f"r_{unique_id}_d"),
            InlineKeyboardButton(f"🔥 {reaction_counts[unique_id]['🔥']}", callback_data=f"r_{unique_id}_f")
        ],[
            InlineKeyboardButton('📂 Get File 📂', url=f'https://telegram.me/MH_Movie_Seach_Bot?start=getfile-{link_slug}')
        ]]
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(updated_buttons))
    except Exception as e:
        print("Reaction error:", e)

# ====================================================================
# 4. HELPER FUNCTIONS
# ====================================================================

async def extract_info_from_filename(filename):
    """
    প্রথম ৫টি শব্দের মধ্যে বছর (19xx-20xx) খুঁজবে।
    বছর পেলে তার আগের অংশ টাইটেল হবে।
    """
    clean_text = re.sub(r'\.\w+$', '', filename)
    clean_text = re.sub(r'[._\-\[\]\(\)]', ' ', clean_text)
    words = clean_text.split()
    
    title = ""
    year = None
    check_limit = min(len(words), 8)
    
    for i in range(check_limit):
        word = words[i]
        if re.match(r'^(19|20)\d{2}$', word):
            year = word
            title = " ".join(words[:i])
            break
            
    if not title:
        # বছর না পেলে ক্লিন নাম এবং সিজন রিমুভ করে টাইটেল বানাবে
        temp_title = await clean_display_name(filename)
        # টাইটেল থেকে S01 বা Season 1 এসব রিমুভ করা হচ্ছে যাতে ক্লীন টাইটেল দেখায়
        title = re.sub(r'(?i)\b(S\d+|Season\s*\d+|Ep?\d+)\b', '', temp_title).strip()
    
    if not year:
        year = "N/A"
        
    return title.strip(), year

async def get_season_episode(text):
    """
    S01, Season 1, E01, Combined ডিটেক্ট করার জন্য
    """
    # . বা _ কে স্পেস করে দিচ্ছি যাতে regex ভালো কাজ করে
    text = re.sub(r'[._]', ' ', text)
    
    # Regex Patterns
    season_pattern = r'(?i)\b(?:S|Season)\s*(\d+)'
    episode_pattern = r'(?i)\b(?:E|Ep|Episode)\s*(\d+)'
    combined_pattern = r'(?i)\b(Combined|Complete|Pack|Batch)\b'
    
    parts = []
    
    # Season Check
    s_match = re.search(season_pattern, text)
    if s_match:
        # 01 কে 1 বানাবে (int)
        parts.append(f"Season {int(s_match.group(1))}")
        
    # Episode Check
    e_match = re.search(episode_pattern, text)
    if e_match:
        parts.append(f"Episode {int(e_match.group(1))}")
        
    # Combined Check
    if re.search(combined_pattern, text):
        parts.append("Combined")
        
    if not parts:
        return None
        
    return " ".join(parts)

async def get_smart_link_slug(filename):
    clean = re.sub(r'\.\w+$', '', filename)
    clean = re.sub(r'https?://\S+|@\w+', '', clean)
    clean_text = re.sub(r'[^a-zA-Z0-9\s]', ' ', clean)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    words = clean_text.split()
    selected_words = []
    found_year = False
    for i in range(min(len(words), 3)):
        word = words[i]
        if re.match(r'^(19|20)\d{2}$', word):
            selected_words = words[:i+1]
            found_year = True
            break
    if not found_year:
        selected_words = words[:3]
    base_slug = "-".join(selected_words)
    final_slug = re.sub(r'[^a-zA-Z0-9\-]', '', base_slug)
    return final_slug

async def clean_search_query(text):
    # সার্চের জন্য শুধু মূল নামটা দরকার, সিজন বা এপিসোড বাদে
    text = re.sub(r'[._\-\(\)\[\]\{\}]', ' ', text)
    text = re.sub(r'\b(S\d+|Season\s*\d+|Ep?\d+)\b', '', text, flags=re.IGNORECASE)
    junk = r'\b(Download|Downlo|Complete|Netflix|Amazon|Prime|Hulu|Hotstar|Series|Movie|Official|Dubbed|Dual|Audio|Sub|ESub|NF|AV1|Vista|AAC|AAC5\.1|Combined|Pack)\b'
    text = re.sub(junk, '', text, flags=re.IGNORECASE)
    return re.sub(r'\s{2,}', ' ', text).strip()

async def clean_display_name(filename):
    name = re.sub(r'\.\w+$', '', filename)
    name = re.sub(r'https?://\S+|@\w+', '', name)
    unwanted = r'\b(?:1080p|720p|480p|2160p|4k|5k|HEVC|WEB-DL|BluRay|HDRip|HDTC|HDTS|CAMRip|HDCAM|DVDRip|DVDScr|WEBRip|x264|x265|10bit|60fps|AAC|AAC5\.1|5\.1|Dual|Audio|Multi|Sub|ESub|Line|GB|MB|KB|Downlo|Download|Netflix|Amazon|NF|AV1|ViSTA|V2|PROPER|Combined|Complete)\b'
    name = re.sub(unwanted, '', name, flags=re.IGNORECASE)
    name = re.sub(r'[\[\(\{\]\)\}]', '', name)
    name = re.sub(r'[._-]', ' ', name)
    return re.sub(r'\s{2,}', ' ', name).strip()

async def get_formatted_language(filename, caption):
    text = (filename + " " + (caption or "")).lower()
    text = re.sub(r'[._\-\[\]\(\)]', ' ', text)
    found_langs = set()
    for code, full_name in LANG_MAP.items():
        if re.search(r'\b' + re.escape(code) + r'\b', text):
            found_langs.add(full_name)
    if not found_langs: return "Unknown"
    return ", ".join(sorted(found_langs))

async def get_qualities(text):
    text_lower = (text or "").lower()
    quality_list = []

    # Source Map
    QUALITY_MAP = {
        "uncut": "Uncut", "director's cut": "Director's Cut", "imax": "IMAX",
        "remastered": "Remastered", "org": "Original Aud",
        "hdcam": "HDCAM (Hall Print)", "camrip": "CAMRip", "cam": "CAMRip",
        "hdtc": "HDTC", "dvdscr": "DVDScr", "scr": "Screener",
        "ts": "Telesync (Hall Print)", "telesync": "Telesync",
        "bluray": "BluRay", "bdrip": "BluRay", "brrip": "BluRay",
        "web-dl": "WEB-DL", "webdl": "WEB-DL", "web-rip": "WEBRip", "webrip": "WEBRip",
        "web": "WEB-DL", "hdrip": "HDRip", "dvdrip": "DVDRip",
    }

    for key, value in QUALITY_MAP.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text_lower):
            quality_list.append(value)
            break 

    if not quality_list: return "HDRip"
    return " | ".join(quality_list)


async def fetch_tmdb_data(query, year=None):
    try:
        # TMDB সাধারণত মুভি সার্চে এপিসোড বা সিজন থাকলে রেজাল্ট দেয় না
        # তাই query টা clean থাকা জরুরি
        params = {"api_key": TMDB_API, "query": query}
        if year and year != "N/A": params["year"] = year
        
        res = requests.get("https://api.themoviedb.org/3/search/movie", params=params, timeout=5)
        results = res.json().get("results", [])
        
        if not results: return {}
        
        matched_movie = results[0] # প্রথম রেজাল্ট নেওয়া হচ্ছে
        
        movie_id = matched_movie.get("id")
        details_res = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API}", timeout=5)
        details = details_res.json()
        
        poster_path = details.get("poster_path") or matched_movie.get("poster_path")
        backdrop_path = details.get("backdrop_path")
        image_url = None
        if poster_path: image_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
        elif backdrop_path: image_url = f"https://image.tmdb.org/t/p/w500{backdrop_path}"
        
        genres_list = [g["name"] for g in details.get("genres", [])]
        genres_str = ", ".join(genres_list[:2])
        
        return {
            "title": details.get("title"),
            "overview": details.get("overview"),
            "vote_average": round(details.get("vote_average", 0), 1),
            "genres": genres_str,
            "release_date": details.get("release_date"),
            "poster": image_url
        }
    except Exception:
        return {}

def generate_unique_id(movie_name):
    return hashlib.md5(movie_name.encode('utf-8')).hexdigest()[:5]


