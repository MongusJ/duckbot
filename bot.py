import os
import logging
import threading
from flask import Flask
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultsButton
from telegram.ext import Application, CommandHandler, ContextTypes, InlineQueryHandler
from ddgs import DuckDuckGoSearch  # 👈 nuevo import

# === CONFIG ===
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# === FLASK (keep-alive) ===
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot alive!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app_flask.run(host='0.0.0.0', port=port)

# === COMANDOS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 ¡Hola! Soy un bot que busca en DuckDuckGo.\n\n"
        "/buscar <término> — busca en la web\n"
        "/ayuda — muestra esta ayuda"
    )

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Usa /buscar <término> para buscar en DuckDuckGo.\n"
        "Ejemplo: /buscar clima hoy"
    )

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Escribe algo para buscar. Ej: /buscar clima")
        return

    query = " ".join(context.args)
    await update.message.chat.send_action(action="typing")

    try:
        ddgs = DuckDuckGoSearch()
        results = ddgs.text(query, max_results=5)

        if not results:
            await update.message.reply_text("😕 No encontré resultados.")
            return

        for r in results:
            title = r.get('title', 'Sin título')
            body = r.get('body', '')
            href = r.get('href', '')
            msg = f"**{title}**\n{body}\n[🔗 {href}]({href})"
            await update.message.reply_text(msg, disable_web_page_preview=False)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")


# === INLINE MODE ===
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        await update.inline_query.answer([], button=InlineQueryResultsButton(
            text="Escribe algo para buscar",
            start_parameter="help"
        ))
        return

    try:
        ddgs = DuckDuckGoSearch()
        results = ddgs.text(query, max_results=5)

        articles = []
        for r in results:
            title = r.get('title', 'Sin título')
            body = r.get('body', '')
            href = r.get('href', '')
            articles.append(InlineQueryResultArticle(
                id=href,
                title=title,
                description=body[:100],
                input_message_content=InputTextMessageContent(
                    f"**{title}**\n{body}\n[🔗 {href}]({href})",
                    parse_mode="Markdown"
                )
            ))

        await update.inline_query.answer(articles, cache_time=10)

    except Exception as e:
        await update.inline_query.answer([], button=InlineQueryResultsButton(
            text="⚠️ Error en la búsqueda",
            start_parameter="error"
        ))

# === MAIN ===
def run_bot():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(InlineQueryHandler(inline_query))

    print("✅ Bot corriendo sin restricciones...")
    app.run_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    run_bot()
