import io
import re
import telebot
from telebot import types

# Coloca aquí el token que te dio @BotFather
TOKEN = "8630977701:AAGR_eX0cVlG2rNWg-k3CIqPmbWWHSPonag"
bot = telebot.TeleBot(TOKEN)

# Memoria temporal para guardar el archivo mientras el usuario elige el filtro
archivos_temporales = {}

def es_correo(texto):
    """Verifica si el login tiene formato de correo electrónico."""
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, texto) is not None

def procesar_contenido(texto_crudo, criterio):
    """Filtra las líneas y elimina duplicados conservando el orden."""
    lineas = texto_crudo.splitlines()
    lineas_unicas = set()
    resultado = []

    for l in lineas:
        l = l.strip()
        if not l or ":" not in l:
            continue

        if l in lineas_unicas:
            continue

        partes = l.split(":", 1)
        usuario = partes[0].strip()
        password = partes[1].strip()

        if not usuario or not password:
            continue

        tiene_arroba = es_correo(usuario)

        if criterio == "solo_correos" and tiene_arroba:
            resultado.append(f"{usuario}:{password}")
            lineas_unicas.add(l)
        elif criterio == "solo_usuarios" and not tiene_arroba:
            resultado.append(f"{usuario}:{password}")
            lineas_unicas.add(l)
        elif criterio == "limpiar_todo":
            resultado.append(f"{usuario}:{password}")
            lineas_unicas.add(l)

    return resultado

@bot.message_handler(commands=['start', 'help'])
def bienvenida(message):
    texto = (
        "👋 <b>Bienvenido al Bot de Filtrado de Combos/Listas</b>\n\n"
        "Adjunta y envía un archivo <code>.txt</code> para limpiarlo y organizarlo."
    )
    bot.reply_to(message, texto, parse_mode="HTML")

@bot.message_handler(content_types=['document'])
def recibir_documento(message):
    if not message.document.file_name.lower().endswith('.txt'):
        bot.reply_to(message, "❌ Envía únicamente archivos con extensión <code>.txt</code>.", parse_mode="HTML")
        return

    # Límite de seguridad: 20 MB
    if message.document.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, "❌ El archivo supera el límite permitido de 20 MB.")
        return

    bot.reply_to(message, "📥 Descargando archivo...")

    try:
        info_archivo = bot.get_file(message.document.file_id)
        descargado = bot.download_file(info_archivo.file_path)
        contenido = descargado.decode('utf-8', errors='ignore')

        archivos_temporales[message.chat.id] = {
            "nombre_base": message.document.file_name.rsplit('.', 1)[0],
            "texto": contenido
        }

        teclado = types.InlineKeyboardMarkup(row_width=1)
        btn1 = types.InlineKeyboardButton("📧 Solo Correo:Pass", callback_data="solo_correos")
        btn2 = types.InlineKeyboardButton("👤 Solo Usuario:Pass", callback_data="solo_usuarios")
        btn3 = types.InlineKeyboardButton("🧹 Limpiar todo (quitar duplicados)", callback_data="limpiar_todo")
        teclado.add(btn1, btn2, btn3)

        bot.send_message(
            message.chat.id,
            "Selecciona la operación que deseas aplicar:",
            reply_markup=teclado
        )

    except Exception as e:
        bot.reply_to(message, f"Ocurrió un error al procesar el archivo: {e}")

@bot.callback_query_handler(func=lambda call: True)
def procesar_opcion(call):
    chat_id = call.message.chat.id

    if chat_id not in archivos_temporales:
        bot.answer_callback_query(call.id, "El archivo expiró. Vuelve a enviarlo.", show_alert=True)
        return

    bot.answer_callback_query(call.id, "Procesando...")
    bot.edit_message_text("⏳ Procesando líneas, un momento...", chat_id=chat_id, message_id=call.message.message_id)

    datos = archivos_temporales.pop(chat_id)
    lineas_filtradas = procesar_contenido(datos["texto"], call.data)

    total = len(lineas_filtradas)
    if total == 0:
        bot.send_message(chat_id, "⚠️ No se encontraron líneas válidas con el criterio seleccionado.")
        return

    buffer_salida = io.BytesIO("\n".join(lineas_filtradas).encode('utf-8'))
    buffer_salida.name = f"{datos['nombre_base']}_{call.data}.txt"

    resumen = (
        f"✅ <b>Proceso completado</b>\n\n"
        f"📊 <b>Líneas obtenidas:</b> {total:,}\n"
        f"⚙️ <b>Filtro:</b> <code>{call.data}</code>"
    )

    bot.send_document(chat_id, buffer_salida, caption=resumen, parse_mode="HTML")

if __name__ == "__main__":
    print("Bot de filtrado en ejecución...")
    bot.infinity_polling()
