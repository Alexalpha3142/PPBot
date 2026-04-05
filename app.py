# -*- coding: utf-8 -*-
import arxiv
import telebot
import requests
from telebot import types
from datetime import datetime, timedelta
import threading
from flask import Flask

# Создаем маленькое веб-приложение
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run_web():
    # Render передает порт в переменной окружения PORT
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


# --- Данные бота ---
# Вставь свой токен от BotFather
API_TOKEN = '7524262469:AAFVQB2I4-05tj-1l-0YXvUYY2un-Xl5oHs'
bot = telebot.TeleBot(API_TOKEN)

# Настройки пользователя по умолчанию
user_settings = {
    'topic': 'physics.optics',
    'keywords': ['laser', 'plasma'],
    'days': 7,
    'limit': 5,
    'source': 'Both' 
}

# --- Главное меню ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_topic = types.KeyboardButton(f"📂 Тема: {user_settings['topic']}")
    btn_keys = types.KeyboardButton(f"🔑 Ключи: {len(user_settings['keywords'])} шт.")
    btn_days = types.KeyboardButton(f"📅 Срок: {user_settings['days']} дн.")
    btn_limit = types.KeyboardButton(f"🔢 Лимит: {user_settings['limit']} ст.")
    btn_source = types.KeyboardButton(f"📡 База: {user_settings['source']}")
    btn_report = types.KeyboardButton("🚀 ПОЛУЧИТЬ ОТЧЕТ")
    
    markup.add(btn_topic, btn_keys)
    markup.add(btn_days, btn_limit)
    markup.add(btn_source, btn_report)
    return markup

# --- Инлайновые меню выбора ---
def topic_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    physics_cats = {
        "physics.optics": "Оптика / Лазеры",
        "physics.plasm-ph": "Физика плазмы",
        "physics.gen-ph": "Общая физика",
        "custom": "⌨️ Ввести код вручную"
    }
    for code, name in physics_cats.items():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"set_topic_{code}"))
    return markup

# --- Вспомогательный поиск Semantic Scholar ---
def search_semantic_scholar(query, limit):
    url = "https://semanticscholar.org"
    params = {"query": query, "limit": limit, "fields": "title,authors,url,publicationDate,tldr"}
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json().get('data', []) if r.status_code == 200 else []
    except:
        return []

# --- Обработчики текстовых кнопок ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.send_message(message.chat.id, "🔬 **Научный Радар (Физика)**\nНастройте поиск кнопками:", 
                     reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: "Тема:" in m.text)
def h_topic(m):
    bot.send_message(m.chat.id, "Выберите категорию физики:", reply_markup=topic_menu())

@bot.message_handler(func=lambda m: "Срок:" in m.text)
def h_days_ask(m):
    msg = bot.send_message(m.chat.id, "Введите количество дней (число):")
    bot.register_next_step_handler(msg, save_days)

def save_days(m):
    if m.text and m.text.isdigit():
        user_settings['days'] = int(m.text)
        bot.send_message(m.chat.id, f"✅ Срок обновлен: {m.text} дн.", reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "⚠️ Введите целое число.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: "Лимит:" in m.text)
def h_limit_ask(m):
    msg = bot.send_message(m.chat.id, "Сколько статей прислать? (число):")
    bot.register_next_step_handler(msg, save_limit)

def save_limit(m):
    if m.text and m.text.isdigit():
        user_settings['limit'] = int(m.text)
        bot.send_message(m.chat.id, f"✅ Лимит обновлен: {m.text} шт.", reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "⚠️ Введите целое число.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: "Ключи:" in m.text)
def ask_keys(m):
    msg = bot.send_message(m.chat.id, "Пришлите ключевые слова через запятую (на англ.):")
    bot.register_next_step_handler(msg, save_keys)

def save_keys(m):
    new_keys = [k.strip() for k in m.text.split(",") if k.strip()] if m.text else []
    user_settings['keywords'] = new_keys
    bot.send_message(m.chat.id, f"✅ Ключи обновлены ({len(new_keys)} шт.)", reply_markup=main_menu())

@bot.message_handler(func=lambda m: "База:" in m.text)
def h_source(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("arXiv", callback_data="set_src_arXiv"),
               types.InlineKeyboardButton("Semantic Scholar", callback_data="set_src_Semantic"),
               types.InlineKeyboardButton("Обе базы (Both)", callback_data="set_src_Both"))
    bot.send_message(m.chat.id, "Выберите источник:", reply_markup=markup)

# --- Обработка кликов (Callback) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data.startswith("set_topic_"):
        if "custom" in call.data:
            msg = bot.send_message(call.message.chat.id, "Введите код arXiv (напр. physics.optics):")
            bot.register_next_step_handler(msg, save_custom_topic)
        else:
            user_settings['topic'] = call.data.replace("set_topic_", "")
    elif call.data.startswith("set_src_"):
        user_settings['source'] = call.data.replace("set_src_", "")
    
    bot.answer_callback_query(call.id, "Готово")
    bot.send_message(call.message.chat.id, "⚙️ Настройки обновлены", reply_markup=main_menu())
    bot.delete_message(call.message.chat.id, call.message.message_id)

def save_custom_topic(m):
    user_settings['topic'] = m.text.strip()
    bot.send_message(m.chat.id, f"✅ Тема установлена: {user_settings['topic']}", reply_markup=main_menu())

# --- Логика генерации отчета ---
@bot.message_handler(func=lambda m: m.text == "🚀 ПОЛУЧИТЬ ОТЧЕТ")
def run_report(message):
    bot.send_message(message.chat.id, f"📡 Ищу в {user_settings['source']}...")
    results = []
    q_str = f"{user_settings['topic']} " + " ".join(user_settings['keywords'])
    
    # Поиск arXiv
    if user_settings['source'] in ['arXiv', 'Both']:
        try:
            start_dt = (datetime.now() - timedelta(days=user_settings['days'])).strftime("%Y%m%d%H%M%S")
            final_q = f"({q_str}) AND submittedDate:[{start_dt} TO {datetime.now().strftime('%Y%m%d%H%M%S')}]"
            s = arxiv.Search(query=final_q, max_results=user_settings['limit'], sort_by=arxiv.SortCriterion.SubmittedDate)
            for r in arxiv.Client().results(s):
                results.append({
                    'title': r.title, 'src': 'arXiv', 'link': r.entry_id,
                    'authors': ", ".join([a.name.split()[-1] for a in r.authors]),
                    'date': r.published.strftime('%Y-%m-%d')
                })
        except: pass

    # Поиск Semantic Scholar
    if user_settings['source'] in ['Semantic', 'Both']:
        sem_res = search_semantic_scholar(q_str, user_settings['limit'])
        for p in sem_res:
            auth = ", ".join([a['name'].split()[-1] for a in p.get('authors', [])])
            results.append({
                'title': p.get('title'), 'src': 'Semantic', 'link': p.get('url'),
                'authors': auth, 'date': p.get('publicationDate', 'N/A'),
                'tldr': p.get('tldr', {}).get('text') if p.get('tldr') else None
            })

    if not results:
        bot.send_message(message.chat.id, "❌ Ничего не найдено.", reply_markup=main_menu())
        return

    report = "📄 **ОТЧЕТ РАДАРА**\n\n"
    for i in results[:user_settings['limit']]:
        entry = f"🔹 [{i['src']}] {i['title']}\n👥 {i['authors']}\n"
        if i.get('tldr'): entry += f"💡 {i['tldr']}\n"
        entry += f"📅 {i['date']}\n🔗 {i['link']}\n{'-'*20}\n\n"
        if len(report + entry) > 3800:
            bot.send_message(message.chat.id, report, disable_web_page_preview=True)
            report = ""
        report += entry
    bot.send_message(message.chat.id, report, disable_web_page_preview=True, reply_markup=main_menu())

if __name__ == "__main__":
    bot.infinity_polling()

if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке
    threading.Thread(target=run_web).start()
    
    # Запускаем бота
    import time
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)
