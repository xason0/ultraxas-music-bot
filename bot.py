import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup
from yt_dlp import YoutubeDL
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("ultraxas_music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_sessions = {}
user_lang = {}

RESULTS_PER_PAGE = 10
MAX_RESULTS = 100

translations = {
    "english": {
        "greeting": "Welcome to Ultraxas Music Bot! Send a song or artist name to begin.",
        "pick": "Select a result to download:",
        "cancel": "Search cancelled.",
        "downloading": "Downloading {title}...",
        "no_results": "No results found.",
        "set_lang": "Choose your language:",
        "lang_set": "Language set to: {lang}"
    },
    "french": {
        "greeting": "Bienvenue sur Ultraxas Music Bot ! Envoyez une chanson ou un artiste pour commencer.",
        "pick": "SÃ©lectionnez un rÃ©sultat Ã  tÃ©lÃ©charger :",
        "cancel": "Recherche annulÃ©e.",
        "downloading": "TÃ©lÃ©chargement de {title}...",
        "no_results": "Aucun rÃ©sultat trouvÃ©.",
        "set_lang": "Choisissez votre langue :",
        "lang_set": "Langue dÃ©finie sur : {lang}"
    },
    "spanish": {
        "greeting": "Â¡Bienvenido al bot de mÃºsica Ultraxas! Escribe el nombre de una canciÃ³n o artista.",
        "pick": "Selecciona un resultado para descargar:",
        "cancel": "BÃºsqueda cancelada.",
        "downloading": "Descargando {title}...",
        "no_results": "No se encontraron resultados.",
        "set_lang": "Elige tu idioma:",
        "lang_set": "Idioma cambiado a: {lang}"
    },
    "twi": {
        "greeting": "Akwaaba! Fa din dwom anaa É”deÉ› na yÉ›mfa nsi dwumadie no ase.",
        "pick": "Paw dwom a wopÉ› sÉ› wodownloadi:",
        "cancel": "AhwehwÉ› no atwa mu.",
        "downloading": "Redownloadi {title}...",
        "no_results": "Æ�nnhu biribiara.",
        "set_lang": "Paw kasa a wopÉ›:",
        "lang_set": "Wopaw kasa: {lang}"
    }
}

def get_text(user_id, key, **kwargs):
    lang = user_lang.get(str(user_id), "english")
    template = translations.get(lang, translations["english"]).get(key, "")
    return template.format(**kwargs)

def build_keyboard(results, page, chat_id):
    start = page * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    buttons = []

    for idx in range(start, min(end, len(results))):
        title = results[idx].get("title", "Unknown Title")[:64]
        buttons.append([
            InlineKeyboardButton(f"{idx+1}. {title}", callback_data=f"download|{chat_id}|{idx}")
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("Prev", callback_data=f"page|{chat_id}|{page-1}"))
    if end < len(results):
        nav_buttons.append(InlineKeyboardButton("Next", callback_data=f"page|{chat_id}|{page+1}"))
    nav_buttons.append(InlineKeyboardButton("Stop", callback_data=f"stop|{chat_id}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("ðŸ¤– Made by Manasseh Amoako\n\n" + get_text(message.from_user.id, "greeting"))


@app.on_message(filters.command("language"))
async def set_language(client, message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[["English", "FranÃ§ais"], ["EspaÃ±ol", "Twi"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.reply(get_text(message.from_user.id, "set_lang"), reply_markup=keyboard)

@app.on_message(filters.text & ~filters.command(["start", "language"]))
async def handle_input(client, message):
    user_id = str(message.from_user.id)
    text = message.text.strip().lower()

    if text in ["english", "franÃ§ais", "espaÃ±ol", "twi"]:
        lang_map = {"english": "english", "franÃ§ais": "french", "espaÃ±ol": "spanish", "twi": "twi"}
        user_lang[user_id] = lang_map[text]
        await message.reply(get_text(user_id, "lang_set", lang=text.title()))
        return

    query = message.text
    chat_id = message.chat.id

    try:
        r = requests.get(f"https://api.deezer.com/search?q={query}")
        data = r.json()
        if data["data"]:
            top = data["data"][0]
            query = f"{top['title']} {top['artist']['name']}"
    except:
        pass

    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "format": "bestaudio/best"
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{MAX_RESULTS}:{query}", download=False)
            results = info.get("entries", [])

        if not results:
            await message.reply(get_text(user_id, "no_results"))
            return

        user_sessions[str(chat_id)] = {
            "results": results,
            "page": 0
        }

        keyboard = build_keyboard(results, 0, chat_id)
        await message.reply(get_text(user_id, "pick"), reply_markup=keyboard)

    except Exception as e:
        await message.reply(f"Search error: `{e}`")

@app.on_callback_query()
async def handle_buttons(client, callback_query: CallbackQuery):
    data = callback_query.data
    chat_id = str(callback_query.message.chat.id)
    user_id = str(callback_query.from_user.id)

    action, cb_chat_id, param = data.split("|")

    if cb_chat_id != chat_id:
        await callback_query.answer("Invalid session.", show_alert=True)
        return

    session = user_sessions.get(chat_id)
    if not session:
        await callback_query.answer("Session expired. Please search again.", show_alert=True)
        return

    results = session["results"]

    if action == "page":
        new_page = int(param)
        session["page"] = new_page
        keyboard = build_keyboard(results, new_page, chat_id)
        await callback_query.message.edit_text(get_text(user_id, "pick"), reply_markup=keyboard)

    elif action == "stop":
        del user_sessions[chat_id]
        await callback_query.message.edit_text(get_text(user_id, "cancel"))

    elif action == "download":
        index = int(param)
        video = results[index]
        url = f"https://www.youtube.com/watch?v={video['id']}"
        title = video.get("title", "Unknown Title")
        await callback_query.message.edit_text(get_text(user_id, "downloading", title=title))

        try:
            ydl_opts = {
                "format": "bestaudio",
                "outtmpl": "%(title)s.%(ext)s",
                "quiet": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }]
            }

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = f"{info['title']}.mp3"

            await callback_query.message.reply_audio(
                audio=file_path,
                title=info.get("title"),
                performer=info.get("uploader"),
                caption=f"{info['title']}\nUploaded by Ultraxas Music Bot"
            )
            os.remove(file_path)

        except Exception as e:
            await callback_query.message.edit_text(f"Download failed.\n\nError: `{e}`")


@app.on_message(filters.command("legal"))
async def legal_command(client, message):
    await message.reply("""
âš–ï¸� *Legal Notice*

Ultraxas Music Bot is for personal and educational use only.
It does not host or store copyrighted content.
All audio is sourced via public search APIs.

By using this bot, you agree to respect music ownership rights.

Made with passion by *Manasseh Amoako*.
    """, quote=True)
async def stop_command(client, message):
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)

    if chat_id in user_sessions:
        del user_sessions[chat_id]

    await message.reply(get_text(user_id, "cancel"))



@app.on_message(filters.command("help"))
async def help_command(client, message):
    await message.reply("""
â„¹ï¸� *How to use Ultraxas Music Bot:*

1. Type the name of any song or artist.
2. Select from up to 100 results.
3. Tap to instantly download MP3.

Use /language to change the response language.
Use /stop to clear your current search session.

ðŸ‘¤ Contact: @xasonxtar
    """, quote=True)
async def legal_command(client, message):
    await message.reply("""
âš–ï¸� *Legal Notice*

Ultraxas Music Bot is for personal and educational use only.
It does not host or store copyrighted content.
All audio is sourced via public search APIs.

By using this bot, you agree to respect music ownership rights.

Made with passion by *Manasseh Amoako*.
    """, quote=True)
async def legal_command(client, message):
    await message.reply("""
âš–ï¸� *Legal Notice*

Ultraxas Music Bot is for personal and educational use only.
It does not host or store copyrighted content.
All audio is sourced via public search APIs.

By using this bot, you agree to respect music ownership rights.

Made with passion by *Manasseh Amoako*.
    """, quote=True)
async def stop_command(client, message):
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)

    if chat_id in user_sessions:
        del user_sessions[chat_id]

    await message.reply(get_text(user_id, "cancel"), quote=True)


app.run()
