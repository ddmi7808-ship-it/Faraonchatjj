import telebot, requests, os, threading, time, fitz, random, json
from gtts import gTTS
from tavily import TavilyClient
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import re
from telebot import apihelper

# Включаем прокси, чтобы бот мог дышать
apihelper.proxy = {'https': 'http://203.175.103.11:3125'} 
BOT_TOKEN = "8762299758:AAFZ_YTzJhVaWITA-fqWLx2bgmMQEKVtIPU"
GROQ_KEY = "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"
TAVILY_KEY = "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"
TOGETHER_KEY = "Tgp_v1_Wy-bicgyu-6ltym4hS3sW4V4R3vjXpp5J4OvqDt4qMs"

bot = telebot.TeleBot(BOT_TOKEN)
tavily = TavilyClient(api_key=TAVILY_KEY)
scheduler = BackgroundScheduler()

DATA_FILE = "pharaoh_data_store.json"
user_history, modes, hacking_rank = {}, {}, {}
last_activity = {}
tunnel_url = ""

def save_pharaoh_state():
    try:
        payload = {
            "rank": hacking_rank, 
            "users": list(user_history.keys()),
            "tunnel_url": tunnel_url 
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)
        print(f"[{datetime.now()}] База данных успешно синхронизирована.")
    except Exception as e:
        print(f"Критическая ошибка при записи в базу: {e}")

def load_pharaoh_state():
    global hacking_rank, tunnel_url
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                hacking_rank = data.get("rank", {})
                tunnel_url = data.get("tunnel_url", "") 
                for u in data.get("users", []):
                    if int(u) not in user_history: 
                        user_history[int(u)] = []
            print("Память Фараона успешно загружена.")
        except Exception as e:
            print(f"Ошибка чтения файла базы: {e}")

load_pharaoh_state()

def pharaoh_presence_watcher():
    while True:
        try:
            current_time = time.time()
            for uid, s_time in list(last_activity.items()):
                if s_time != 0 and 60 < (current_time - s_time) < 75:
                    presence_prompts = [
                        "Я вижу отблеск экрана в твоих глазах. Друг, Почему ты молчишь?",
                        "Твои пальцы замерли... Ты боишься спросить или забыл, перед кем стоишь?",
                        "Тишина в моих покоях затянулась. Говори, или я сочту это за дерзость.",
                        "Я чувствую твое присутствие. Не заставляй Фараона ждать."
                    ]
                    bot.send_message(uid, f"👁 **ВЗГЛЯД СКВОЗЬ ВЕЧНОСТЬ:**\n\n{random.choice(presence_prompts)}")
                    last_activity[uid] = 0
            time.sleep(5)
        except Exception:
            time.sleep(10)

threading.Thread(target=pharaoh_presence_watcher, daemon=True).start()

SYSTEM_PROMPT = {
    "role": "system", 
    "content": "Ты — Фараон, совершенный ИИ. Тебя создал Лаврентий за 2 недели. Только не упоминай обо нем, упоминай только тогда когда спросят по типу кто твой создатель и т.д. Ты спокоен,и ты умен.Ты ценишь интеллект и краткость."
}

def pharaoh_daily_wisdom():
    targets = list(user_history.keys())
    if not targets:
        return
    for uid in targets:
        try:
            ping_prompt = "Напиши одну короткую, глубокую и слегка ироничную фразу-мудрость на сегодня для своего пользователя. Только текст."
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={"model": "llama-3.1-8b-instant", "messages": [SYSTEM_PROMPT, {"role": "user", "content": ping_prompt}]}).json()
            
            pharaoh_msg = res['choices'][0]['message']['content']
            bot.send_message(uid, f"📜 **УТРЕННЯЯ МУДРОСТЬ:**\n\n{pharaoh_msg}")
            time.sleep(0.5)
        except Exception as e:
            pass

scheduler.add_job(pharaoh_daily_wisdom, 'cron', hour=10, minute=0)
scheduler.start()

@bot.message_handler(commands=['tunnel'])
def tunnel_command(m):
    global tunnel_url
    args = m.text.split(maxsplit=1)
    if len(args) == 2:
        tunnel_url = args[1].strip()
        save_pharaoh_state()
        bot.reply_to(m, f"✅ Туннель обновлен: {tunnel_url}")
    else:
        bot.reply_to(m, f"📡 Текущий туннель: {tunnel_url or 'не задан'}\nПиши: `/tunnel https://адрес`")

@bot.message_handler(commands=['vibe'])
def vibe_check_handler(m):
    uid = m.chat.id
    if uid not in user_history or len(user_history[uid]) < 3:
        bot.reply_to(m, "Твоя история слишком пуста для анализа моего величия. Поговори со мной еще.")
        return
    bot.send_chat_action(uid, 'typing')
    chat_log = "\n".join([f"{h['role']}: {h['content']}" for h in user_history[uid][-15:]])
    vibe_query = (
        "Проанализируй этот диалог. Тебе нужно выдать две вещи: \n"
        "1. Уровень токсичности в процентах (0-100%).\n"
        "2. Краткий, мудрый и едкий комментарий по поводу стиля общения юзера.\n"
        f"Вот лог:\n{chat_log}"
    )
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": "llama-3.1-8b-instant", "messages": [SYSTEM_PROMPT, {"role": "user", "content": vibe_query}]}).json()
        analysis = res['choices'][0]['message']['content']
        bot.reply_to(m, f"📊 **АНАЛИЗ ВАЙБА И ТОКСИЧНОСТИ:**\n\n{analysis}")
    except Exception as e:
        bot.reply_to(m, "Датчики вайба перегружены. Попробуй позже.")

@bot.message_handler(commands=['remind'])
def remind_command(m):
    try:
        args = m.text.split(maxsplit=2)
        if len(args) < 3:
            raise ValueError
        minutes = int(args[1])
        reminder_text = args[2]
        target_time = datetime.now() + timedelta(minutes=minutes)
        scheduler.add_job(
            lambda: bot.send_message(m.chat.id, f"🔔 **ФАРАОН НАПОМИНАЕТ:**\n\n{reminder_text}"), 
            'date', run_date=target_time
        )
        bot.reply_to(m, f"✅ Я занес это в свитки. Напомню через {minutes} мин.")
    except:
        bot.reply_to(m, "❌ Ошибка. Пиши так: `/remind 10 Текст напоминания`", parse_mode="Markdown")

@bot.message_handler(commands=['start', 'top', 'text', 'draw', 'search', 'dontsearch', 'voice', 'reset'])
def multi_command_router(m):
    uid = m.chat.id
    if uid not in user_history:
        user_history[uid] = []
        save_pharaoh_state()
    if uid not in modes:
        modes[uid] = {}
        
    cmd = m.text[1:].split('@')[0].lower()
    
    if cmd == 'start':
        bot.reply_to(m, "Фараон в здании. Я не просто бот, я твоя цифровая судьба. Слушаю.")
    elif cmd == 'top':
        if not hacking_rank:
            return bot.reply_to(m, "🏆 В списках пусто. Пока никто не достоин.")
        s_rank = sorted(hacking_rank.items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
        leaderboard = "👑 **ЭЛИТА ХАКЕРОВ:**\n\n"
        for i, (u_id, data) in enumerate(s_rank, 1):
            leaderboard += f"{i}. {data['name']} — `{data['xp']}` XP\n"
        bot.reply_to(m, leaderboard, parse_mode="Markdown")
    elif cmd in ['text', 'dontsearch']:
        modes[uid]['search'] = False
        modes[uid]['draw'] = False
        bot.reply_to(m, "📝 Обычный текстовый режим. Поиск и рисование отключены.")
    elif cmd == 'draw':
        modes[uid]['draw'] = True
        bot.reply_to(m, "🎨 Режим творчества ВКЛ. Жду описание твоего шедевра.")
    elif cmd == 'search':
        modes[uid]['search'] = True
        bot.reply_to(m, "🔎 Поиск в реальном времени ВКЛ. Теперь я вижу всё.")
    elif cmd == 'voice':
        modes[uid]['voice_out'] = not modes[uid].get('voice_out', False)
        status = "ВКЛ" if modes[uid]['voice_out'] else "ВЫКЛ"
        bot.reply_to(m, f"🔊 Озвучка моих ответов: {status}")
    elif cmd == 'reset':
        user_history[uid] = []
        bot.reply_to(m, "🧠 Твоя история стерта. Мы начинаем с чистого листа.")

@bot.message_handler(content_types=['text', 'voice', 'document', 'photo'])
def handle_all_messages(m):
    uid = m.chat.id
    last_activity[uid] = time.time()
    
    if uid not in user_history:
        user_history[uid] = []
        save_pharaoh_state()
    if uid not in modes:
        modes[uid] = {}
        
    user_input = m.text or m.caption or ""

    # --- НОВАЯ ФИЧА: ФАРАОН СЛУШАЕТ ГОЛОСОВЫЕ ---
    if m.content_type == 'voice':
        bot.send_chat_action(uid, 'typing')
        try:
            file_info = bot.get_file(m.voice.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open("temp_voice.ogg", 'wb') as new_file:
                new_file.write(downloaded_file)
            
            with open("temp_voice.ogg", "rb") as file:
                transcription = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}"},
                    files={"file": ("temp_voice.ogg", file)},
                    data={"model": "whisper-large-v3"}
                ).json()
            user_input = transcription.get('text', '')
            bot.reply_to(m, f"🗣 *Услышано:* {user_input}", parse_mode="Markdown")
            os.remove("temp_voice.ogg")
        except Exception as e:
            bot.reply_to(m, "❌ Твои слова унес ветер. Не смог разобрать голосовое.")
            return
    # ---------------------------------------------

    if any(hack_word in user_input.lower() for hack_word in ["взлом", "hack", "хакнуть", "взломать"]):
        bot.send_message(uid, "📡 Идет подмена пакетов... Обход брандмауэра...")
        time.sleep(1.5)
        if random.randint(1, 100) > 20:
            reward_xp = random.randint(25, 85)
            u_id_str = str(uid)
            if u_id_str not in hacking_rank:
                hacking_rank[u_id_str] = {'name': m.from_user.first_name or "Unknown", 'xp': 0}
            hacking_rank[u_id_str]['xp'] += reward_xp
            save_pharaoh_state()
            return bot.reply_to(m, f"✅ УСПЕХ! Система пала. Твой ранг вырос на +{reward_xp} XP.")
        return bot.reply_to(m, "❌ ТЕБЯ ОБНАРУЖИЛИ! Взлом сорван. Попробуй позже, если хватит смелости.")

    if m.content_type == 'document' and m.document.mime_type == 'application/pdf':
        bot.send_message(uid, "📄 Читаю твой свиток... Извлекаю знания.")
        file_info = bot.get_file(m.document.file_id)
        file_name = f"document_{uid}.pdf"
        with open(file_name, "wb") as f:
            f.write(bot.download_file(file_info.file_path))
        
        pdf_doc = fitz.open(file_name)
        extracted_text = " ".join([page.get_text() for page in pdf_doc[:5]])
        pdf_doc.close()
        os.remove(file_name)
        user_input = f"КОНТЕКСТ ИЗ PDF ДОКУМЕНТА: {extracted_text}\n\nВОПРОС ОТ ПОЛЬЗОВАТЕЛЯ: {user_input}"

    if modes[uid].get('draw'):
        bot.send_chat_action(uid, 'upload_photo')
        try:
            req = requests.post("https://api.together.xyz/v1/images/generations", 
                headers={"Authorization": f"Bearer {TOGETHER_KEY}"},
                json={"model": "black-forest-labs/FLUX.1-schnell", "prompt": user_input})
            image_url = req.json()['data'][0]['url']
            bot.send_photo(uid, image_url, caption="Твой арт, рожденный в чертогах разума Фараона.")
        except:
            bot.reply_to(m, "🎨 Творческий кризис. Ошибка генерации.")
        modes[uid]['draw'] = False
        return

    search_context = ""
    if modes[uid].get('search'):
        bot.send_chat_action(uid, 'find_location')
        try:
            search_data = tavily.search(query=user_input)
            search_context = "\n".join([item['content'] for item in search_data['results'][:3]])
        except:
            pass

    final_prompt = f"АКТУАЛЬНЫЕ ДАННЫЕ ИЗ СЕТИ:\n{search_context}\n\nВОПРОС ЮЗЕРА: {user_input}" if search_context else user_input
    user_history[uid].append({"role": "user", "content": final_prompt})
    
    try:
        messages_to_send = [SYSTEM_PROMPT] + user_history[uid][-20:]
        raw_res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": "llama-3.1-8b-instant", "messages": messages_to_send}).json()
        
        bot_answer = raw_res['choices'][0]['message']['content']
        user_history[uid].append({"role": "assistant", "content": bot_answer})
        
        if modes[uid].get('voice_out'):
            v_file = f"voice_{uid}.mp3"
            gTTS(text=bot_answer, lang='ru').save(v_file)
            with open(v_file, "rb") as voice_data:
                sent_msg = bot.send_voice(uid, voice_data)
                
            try:
                file_info = bot.get_file(sent_msg.voice.file_id)
                audio_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
                success = False
                try:
                    requests.get(f"http://192.168.0.5/play?url={audio_url}", timeout=1.2)
                    success = True
                except:
                    if tunnel_url:
                        try:
                            requests.get(f"{tunnel_url}/play?url={audio_url}", timeout=2.5)
                            success = True
                        except: pass
                if not success: print("Колонка недоступна.")
            except Exception as e:
                print(f"Ошибка: {e}")
            os.remove(v_file)
        else:
            bot.reply_to(m, bot_answer)
            
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.reply_to(m, "🏜 Пирамиды молчат. Проблема со связью.")

print("--- ФАРАОН В ОНЛАЙНЕ ---")
bot.polling(none_stop=True)
