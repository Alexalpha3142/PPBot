# -*- coding: utf-8 -*-
import arxiv
import telebot
import requests
import os
import time
from telebot import types
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- BOT SETUP ---
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

user_settings = {
    'topic': 'physics.optics',
    'keywords': ['laser', 'plasma'],
    'days': 7,
    'limit': 5,
    'source': 'Both'
}

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton(f"📂 Тема: {user_settings['topic']}"),
        types.KeyboardButton(f"🔑 Ключи: {len(user_settings['keywords'])} шт."),
        types.KeyboardButton(f"📅 Срок: {user_settings['days']} дн."),
        types.KeyboardButton(f"🔢 Лимит: {user_settings['limit']} ст."),
        types.KeyboardButton(f"📡 База: {user_settings['source']}"),
        types.KeyboardButton("🚀 ПОЛУЧИТЬ ОТЧЕТ"),
        types.KeyboardButton("🔄 СБРОС")
    )
    return markup

def topic_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    physics_cats = {
        "physics.optics": "Оптика", "physics.plasm-ph": "Плазма",
        "physics.gen-ph": "Общая физика", "physics.app-ph": "Прикладная",
        "custom": "⌨️ Свой код"
    }
    buttons = [types.InlineKeyboardButton(name, callback_data=f"set_topic_{code}") 
               for code, name in physics_cats.items()]
    markup.add(*buttons)
    return markup

# --- SEARCH LOGIC ---
def search_semantic_scholar(query, limit):
    url = "https://semanticscholar.org" # Исправлен URL API
    params = {"query": query, "limit": limit, "fields": "title,authors,url,publicationDate,tldr"}
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json().get('data', []) if r.status_code == 200 else []
    except:
        return []

# --- HANDLERS ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.send_message(message.chat.id, "🔬 **Научный Радар**\nНастройте поиск:", 
                     reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: "Тема:" in m.text)
def h_topic(m):
    bot.send_message(m.chat.id, "Выберите категорию:", reply_markup=topic_menu())

@bot.message_handler(func=lambda m: "Срок:" in m.text)
def h_days_ask(m):
    msg = bot.send_message(m.chat.id, "Введите количество дней (число):")
    bot.register_next_step_handler(msg, lambda msg: save_setting(msg, 'days'))

@bot.message_handler(func=lambda m: "Лимит:" in m.text)
def h_limit_ask(m):
    msg = bot.send_message(m.chat.id, "Сколько статей прислать? (число):")
    bot.register_next_step_handler(msg, lambda msg: save_setting(msg, 'limit'))

def save_setting(m, key):
    if m.text and m.text.isdigit():
        user_settings[key] = int(m.text)
        bot.send_message(m.chat.id, f"✅ Обновлено: {m.text}", reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "⚠️ Введите число.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: "Ключи:" in m.text)
def ask_keys(m):
    msg = bot.send_message(m.chat.id, "Пришлите ключевые слова через запятую (на англ.):")
    bot.register_next_step_handler(msg, save_keys)

def save_keys(m):
    user_settings['keywords'] = if m.text else []
    bot.send_message(m.chat.id, "✅ Ключи обновлены", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data.startswith("set_topic_"):
        user_settings['topic'] = call.data.replace("set_topic_", "")
    elif call.data.startswith("set_src_"):
        user_settings['source'] = call.data.replace("set_src_", "")
    
    bot.answer_callback_query(call.id, "Готово")
    bot.send_message(call.message.chat.id, "⚙️ Настройки обновлены", reply_markup=main_menu())

# --- REPORT GENERATION ---
@bot.message_handler(func=lambda m: m.text == "🚀 ПОЛУЧИТЬ ОТЧЕТ")
def run_report(message):
    bot.send_message(message.chat.id, f"📡 Ищу в {user_settings['source']}...")
    results = []
    q_str = f"{user_settings['topic']} " + " ".join(user_settings['keywords'])

    # 1. arXiv
    if user_settings['source'] in ['arXiv', 'Both']:
        try:
            start_dt = (datetime.now() - timedelta(days=user_settings['days'])).strftime("%Y%m%d%H%M%S")
            final_q = f"({q_str}) AND submittedDate:[{start_dt} TO {datetime.now().strftime('%Y%m%d%H%M%S')}]"
            s = arxiv.Search(query=final_q, max_results=user_settings['limit'], sort_by=arxiv.SortCriterion.SubmittedDate)
            for r in arxiv.Client().results(s):
                results.append({
                    'title': r.title, 'src': 'arXiv', 'link': r.entry_id,
                    'authors': ", ".join([a.name for a in r.authors[:3]]),
                    'date': r.published.strftime('%Y-%m-%d')
                })
        except: pass

    # 2. Semantic Scholar
    if user_settings['source'] in ['Semantic', 'Both']:
        sem_res = search_semantic_scholar(q_str, user_settings['limit'])
        for p in sem_res:
            results.append({
                'title': p.get('title'), 'src': 'Semantic', 'link': p.get('url'),
                'authors': ", ".join([a['name'] for a in p.get('authors', [])[:3]]),
                'date': p.get('publicationDate', 'N/A'),
                'tldr': p.get('tldr', {}).get('text') if p.get('tldr') else None
            })

    if not results:
        bot.send_message(message.chat.id, "❌ Ничего не найдено.", reply_markup=main_menu())
        return

    # Отправка
    report = "📄 **ОТЧЕТ РАДАРА**\n\n"
    for i in results[:user_settings['limit']]:
        entry = f"🔹 [{i['src']}] {i['title']}\n👥 {i['authors']}\n"
        if i.get('tldr'): entry += f"💡 {i['tldr']}\n"
        entry += f"📅 {i['date']}\n🔗 {i['link']}\n{'-'*20}\n\n"
        
        if len(report + entry) > 3800:
            bot.send_message(message.chat.id, report, disable_web_page_preview=True, parse_mode="Markdown")
            report = ""
        report += entry
    
    bot.send_message(message.chat.id, report, disable_web_page_preview=True, reply_markup=main_menu(), parse_mode="Markdown")

if __name__ == "__main__":
    keep_alive()
    print("Бот запущен!")
    bot.infinity_polling()
