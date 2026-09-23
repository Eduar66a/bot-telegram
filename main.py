import io
import os
import threading
from flask import Flask
import telebot

# 1. Mini servidor web para mantener activo Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de búsqueda activo 24/7"

def iniciar_servidor_web():
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=puerto)

# 2. Configuración del Bot
TOKEN = "8630977701:AAGR_eX0cVlG2rNWg-k3CIqPmbWWHSPonag"  # <-- ASEGÚRATE DE DEJAR TU TOKEN AQUÍ
bot = telebot.TeleBot(TOKEN)

# Memoria temporal para guardar el archivo enviado mientras el usuario escribe la búsqueda
archivos_en_espera = {}

@bot.message_handler(commands=['start', 'help'])
def bienvenida(message):
    texto = (
        "🔍 <b>Buscador y Filtrador por Dominio / URL</b>\n\n"
        "1. Envía tu archivo <code>.txt</code> adjunto.\n"
        "2. El bot te pedirá qué dominio, URL o término deseas extraer.\n"
        "3. Recibirás un nuevo archivo <code>.txt</code> con solo las coincidencias."
    )
    bot.reply_to(message, texto, parse_mode="HTML")

@bot.message_handler(content_types=['document'])
def recibir_archivo(message):
    if not message.document.file_name.lower().endswith('.txt'):
        bot.reply_to(message, "❌ Envía únicamente archivos con extensión <code>.txt</code>.", parse_mode="HTML")
        return

    if message.document.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, "❌ El archivo supera el límite de 20 MB.")
        return

    bot.reply_to(message, "📥 Descargando archivo...")

    try:
        info_archivo = bot.get_file(message.document.file_id)
        descargado = bot.download_file(info_archivo.file_path)
        contenido = descargado.decode('utf-8', errors='ignore')

        # Guardamos el archivo asociado al chat
        archivos_en_espera[message.chat.id] = {
            "nombre": message.document.file_name.rsplit('.', 1)[0],
            "texto": contenido
        }

        # Pedimos el término de búsqueda
        mensaje_espera = bot.send_message(
            message.chat.id,
            "✍️ <b>¿Qué dominio, URL o palabra clave deseas extraer?</b>\n\n"
            "<i>Ejemplos: <code>@gmail.com</code>, <code>netflix.com</code>, <code>paypal</code>, <code>hotmail</code></i>",
            parse_mode="HTML"
        )
        # Espera la siguiente respuesta de texto del usuario
        bot.register_next_step_handler(mensaje_espera, ejecutar_filtrado)

    except Exception as e:
        bot.reply_to(message, f"Ocurrió un error al leer el archivo: {e}")

def ejecutar_filtrado(message):
    chat_id = message.chat.id

    if chat_id not in archivos_en_espera:
        bot.reply_to(message, "⚠️ No hay ningún archivo pendiente. Por favor envía de nuevo tu .txt.")
        return

    termino = message.text.strip()
    if not termino:
        bot.reply_to(message, "⚠️ No ingresaste ningún término válido.")
        return

    bot.reply_to(message, f"⏳ Filtrando líneas que contengan: <code>{termino}</code>...", parse_mode="HTML")

    datos = archivos_en_espera.pop(chat_id)
    lineas = datos["texto"].splitlines()

    termino_lower = termino.lower()
    coincidencias = []
    lineas_unicas = set()

    for l in lineas:
        linea_limpia = l.strip()
        if not linea_limpia:
            continue
        
        # Comprueba si el dominio, URL o texto está en la línea
        if termino_lower in linea_limpia.lower():
            if linea_limpia not in lineas_unicas:
                coincidencias.append(linea_limpia)
                lineas_unicas.add(linea_limpia)

    total = len(coincidencias)
    if total == 0:
        bot.send_message(chat_id, f"❌ No se encontraron líneas con el término: <b>{termino}</b>", parse_mode="HTML")
        return

    # Crear el archivo filtrado en memoria
    buffer_salida = io.BytesIO("\n".join(coincidencias).encode('utf-8'))
    # Limpiamos el nombre de caracteres raros para el archivo de salida
    nombre_limpio = "".join(c for c in termino if c.isalnum() or c in ('-', '_'))
    buffer_salida.name = f"{datos['nombre']}_{nombre_limpio}.txt"

    resumen = (
        f"✅ <b>Filtrado completado</b>\n\n"
        f"🎯 <b>Criterio buscado:</b> <code>{termino}</code>\n"
        f"📊 <b>Líneas extraídas:</b> {total:,}"
    )

    bot.send_document(chat_id, buffer_salida, caption=resumen, parse_mode="HTML")

if __name__ == "__main__":
    t = threading.Thread(target=iniciar_servidor_web)
    t.daemon = True
    t.start()

    print("Bot con filtro por dominio/URL iniciado...")
    bot.infinity_polling()
