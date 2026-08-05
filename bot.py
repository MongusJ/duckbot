# bot.py — DuckBot versión completa
# Comandos: /start, /ayuda, /buscar
# Inline: @Another_duck_bot <consulta> desde cualquier chat
# Vista previa de enlaces con Instant View automático

import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram import InlineQueryResultsButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    InlineQueryHandler,
)
from telegram.constants import ParseMode
from ddgs import DDGS

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("No se encontró el TOKEN. Configúralo como variable de entorno.")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# === SERVIDOR HEALTH (para que Render no mate el proceso) ===
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    server = HTTPServer(("0.0.0.0", 10000), HealthHandler)
    server.serve_forever()

threading.Thread(target=run_health_server, daemon=True).start()

# ──────────────────────────────────────────────
# HANDLER de /start
# ──────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐤 ¡Hola! Soy DuckBot.\n\n"
        "Comandos disponibles:\n"
        "/ayuda — lista de comandos\n"
        "/buscar <término> — busca en DuckDuckGo\n\n"
        "También puedes usarme desde cualquier chat:\n"
        "escribe `@Another_Duck_bot <búsqueda>` y elige un resultado.",
        parse_mode=ParseMode.MARKDOWN
    )

# ──────────────────────────────────────────────
# HANDLER de /ayuda
# ──────────────────────────────────────────────
async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 **Comandos de DuckBot**\n\n"
        "• `/start` — Inicia el bot\n"
        "• `/ayuda` — Esta lista\n"
        "• `/buscar <palabras>` — Busca en DuckDuckGo\n\n"
        "**Uso inline:**\n"
        "En cualquier chat escribe:\n"
        "`@Another_duck_bot <lo que quieras buscar>`\n\n"
        "Ejemplo: `@Another_duck_bot clima en CDMX`",
        parse_mode=ParseMode.MARKDOWN
    )

# ──────────────────────────────────────────────
# HANDLER de /buscar
# ──────────────────────────────────────────────
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❓ ¿Qué quieres buscar?\n"
            "Ejemplo: `/buscar recetas de mole`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    consulta = " ".join(context.args)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        resultados = list(DDGS().text(consulta, max_results=5))

        if not resultados:
            await update.message.reply_text(
                "😕 No encontré resultados para esa búsqueda.\n"
                "Prueba con otras palabras."
            )
            return

        for r in resultados:
            titulo = r.get("title", "Sin título")
            descripcion = r.get("body", "Sin descripción")
            enlace = r.get("href", "")

            await update.message.reply_text(
                f"🔗 [{titulo}]({enlace})\n_{descripcion}_",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )

        await update.message.reply_text(
            f"✅ Mostrando {len(resultados)} resultados para: _{consulta}_",
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Ocurrió un error al buscar.\n"
            "Revisa tu conexión o inténtalo más tarde."
        )
        print(f"Error en búsqueda: {e}")

# ──────────────────────────────────────────────
# HANDLER INLINE — @TuBot desde cualquier chat
# ──────────────────────────────────────────────
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = update.inline_query.query.strip()

    if not consulta:
        await update.inline_query.answer(
            results=[],
            button=InlineQueryResultsButton(
                text="🔍 Escribe algo para buscar",
                start_parameter="buscar"
            )
        )
        return

    try:
        resultados = list(DDGS().text(consulta, max_results=5))

        if not resultados:
            await update.inline_query.answer(
                results=[],
                button=InlineQueryResultsButton(
                    text="😕 Sin resultados. Busca otra cosa",
                    start_parameter="buscar"
                )
            )
            return

        articulos = []
        for r in resultados:
            titulo = r.get("title", "Sin título")
            descripcion = r.get("body", "Sin descripción")
            enlace = r.get("href", "")

            articulos.append(
                InlineQueryResultArticle(
                    id=enlace[:64],
                    title=titulo[:100],
                    description=descripcion[:150],
                    input_message_content=InputTextMessageContent(
                        message_text=f"🔗 [{titulo}]({enlace})\n_{descripcion}_",
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=False
                    )
                )
            )

        await update.inline_query.answer(
            results=articulos[:5],
            cache_time=10
        )

    except Exception as e:
        print(f"Error en inline: {e}")
        await update.inline_query.answer(
            results=[],
            button=InlineQueryResultsButton(
                text="❌ Error al buscar",
                start_parameter="buscar"
            )
        )


# ──────────────────────────────────────────────
# HANDLER para mensajes de texto que NO son comandos
# ──────────────────────────────────────────────
async def texto_generico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    await update.message.reply_text(
        f"Escribiste: \"{texto}\"\n\n"
        "Si quieres buscar algo, usa:\n"
        "`/buscar {texto}`\n\n"
        "O desde cualquier chat:\n"
        "`@Another_duck_bot {texto}`",
        parse_mode=ParseMode.MARKDOWN
    )

# ──────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_generico))

    print("🐤 DuckBot encendido — comandos + inline mode activos!")
    app.run_polling()

if __name__ == "__main__":
    main()
