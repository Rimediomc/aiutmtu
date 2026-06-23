import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Mostra i passaggi sullo schermo per capire se tutto funziona
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# INSERISCI I TUOI DATI REALI QUI SOTTO
# ==========================================
TOKEN = "8662944209:AAGZ2vRusJcV4TO2yCfU-hSjVZ6vdpVGTX4"
IL_MIO_ID = 670198268  # <--- Sostituisci questo numero con il tuo ID vero
# ==========================================

USER_DATA = defaultdict(lambda: {'queue': [], 'waiting_for_title': False, 'ext': '.mp4'})

def controlla_utente(update: Update) -> bool:
    """Controlla se chi scrive è il padrone del bot"""
    return update.effective_user.id == IL_MIO_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    USER_DATA[user_id] = {'queue': [], 'waiting_for_title': False, 'ext': '.mp4'}
    await update.message.reply_text(
        "Ciao padrone! Inviami pure tutti i file o video che vuoi rinominare.\n"
        "Puoi inoltrarli anche tutti insieme a pacchetti.\n"
        "Quando hai finito di inviarli tutti, scrivi il comando: /rinomina"
    )

async def ricevi_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    stato = USER_DATA[user_id]
    
    if update.message.video:
        file_id = update.message.video.file_id
        ext = ".mp4" 
    elif update.message.document:
        file_id = update.message.document.file_id
        nome_originale = update.message.document.file_name
        ext = f".{nome_originale.split('.')[-1]}" if nome_originale and '.' in nome_originale else ".mp4"
    else:
        return

    stato['queue'].append(file_id)
    stato['ext'] = ext
    
    quanti = len(stato['queue'])
    # Ti avvisa ogni volta che riceve un file per darti conferma
    await update.message.reply_text(f"?? Ricevuto! File in coda: {quanti}")

async def chiedi_titolo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    stato = USER_DATA[user_id]
    
    if not stato['queue']:
        await update.message.reply_text("La coda è vuota! Inviami prima dei file.")
        return
        
    stato['waiting_for_title'] = True
    await update.message.reply_text(
        f"Ci sono {len(stato['queue'])} file pronti.\n"
        "Scrivimi adesso il titolo base che vuoi dare (es: antonio 1x):"
    )

async def esegui_rinomina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    stato = USER_DATA[user_id]
    
    if not stato['waiting_for_title']:
        return
        
    titolo_base = update.message.text
    stato['waiting_for_title'] = False
    
    lista_file = stato['queue'].copy()
    estensione = stato['ext']
    totale = len(lista_file)
    
    await update.message.reply_text(f"Sto elaborando {totale} file... Attendi qualche istante.")
    stato['queue'] = [] # Svuota la coda così puoi mandare altri file subito dopo
    
    for posizione, file_id in enumerate(lista_file, start=1):
        # Mette lo zero davanti se il numero è minore di 10 (01, 02, 03...)
        numero = str(posizione).zfill(2)
        nuovo_nome = f"{titolo_base}{numero}{estensione}"
        
        try:
            # Rimanda il file modificando nome e didascalia
            await context.bot.send_document(
                chat_id=user_id,
                document=file_id,
                filename=nuovo_nome,
                caption=nuovo_nome
            )
        except Exception as errore:
            await update.message.reply_text(f"Errore sul file numero {posizione}: {str(errore)}")

    await context.bot.send_message(chat_id=user_id, text="? Fatto! Ho finito di rinominare tutto.")

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rinomina", chiedi_titolo))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, ricevi_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, esegui_rinomina))
    
    print("Il bot è partito correttamente ed è in ascolto...")
    application.run_polling()

if __name__ == '__main__':
    main()