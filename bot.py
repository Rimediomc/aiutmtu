import logging
from collections import defaultdict
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# =========================================================================
# INSERISCI I TUOI DATI REALI QUI SOTTO
# =========================================================================
TOKEN = "8662944209:AAGZ2vRusJcV4TO2yCfU-hSjVZ6vdpVGTX4"
SUPER_ADMIN = 670198268       # <--- Metti qui il TUO ID personale
# =========================================================================

# Lista iniziale degli admin (puoi lasciarla vuota o mettere gli ID di partenza)
# Il Super Admin viene aggiunto automaticamente dal codice più in basso
ADMINS_CORRENTI = set() 

USER_DATA = defaultdict(lambda: {'queue': [], 'waiting_for_title': False})

def controlla_utente(update: Update) -> bool:
    """Controlla se l'utente è il Super Admin o un Admin autorizzato"""
    user_id = update.effective_user.id
    return user_id == SUPER_ADMIN or user_id in ADMINS_CORRENTI

# -------------------------------------------------------------------------
# COMANDI DI GESTIONE PER IL SUPER ADMIN
# -------------------------------------------------------------------------
async def aggiungi_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permette al Super Admin di aggiungere un admin tramite chat"""
    if update.effective_user.id != SUPER_ADMIN:
        return
    if not context.args:
        await update.message.reply_text("Uso corretto: `/aggiungi ID_NUMERICO`", parse_mode="Markdown")
        return
    try:
        nuovo_id = int(context.args[0])
        ADMINS_CORRENTI.add(nuovo_id)
        await update.message.reply_text(f"✅ Utente {nuovo_id} aggiunto alla lista degli Admin!")
    except ValueError:
        await update.message.reply_text("❌ L'ID deve essere composto solo da numeri.")

async def rimuovi_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permette al Super Admin di rimuovere un admin tramite chat"""
    if update.effective_user.id != SUPER_ADMIN:
        return
    if not context.args:
        await update.message.reply_text("Uso corretto: `/rimuovi ID_NUMERICO`", parse_mode="Markdown")
        return
    try:
        id_da_togliere = int(context.args[0])
        if id_da_togliere in ADMINS_CORRENTI:
            ADMINS_CORRENTI.remove(id_da_togliere)
            await update.message.reply_text(f"✅ Utente {id_da_togliere} rimosso dagli Admin.")
        else:
            await update.message.reply_text("❌ Questo ID non era presente nella lista.")
    except ValueError:
        await update.message.reply_text("❌ L'ID deve essere composto solo da numeri.")

async def mostra_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la lista attuale degli admin al Super Admin"""
    if update.effective_user.id != SUPER_ADMIN:
        return
    if not ADMINS_CORRENTI:
        await update.message.reply_text(f"👑 Tu sei il Super Admin ({SUPER_ADMIN}). Non ci sono altri admin associati al momento.")
        return
    testo = f"👑 **Super Admin**: {SUPER_ADMIN}\n\n👥 **Admin abilitati**:\n"
    for adm in ADMINS_CORRENTI:
        testo += f"• {adm}\n"
    await update.message.reply_text(testo, parse_mode="Markdown")

# -------------------------------------------------------------------------
# FUNZIONI PRINCIPALI DEL BOT (CODE E BOTTONI)
# -------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    USER_DATA[user_id] = {'queue': [], 'waiting_for_title': False}
    
    messaggio = "Ciao! Inviami pure i video o i file in serie.\nQuando hai finito, usa i bottoni in basso per procedere."
    if user_id == SUPER_ADMIN:
        messaggio += "\n\n⚙️ **Comandi Creatore**:\n`/aggiungi ID`\n`/rimuovi ID`\n`/lista`"
        
    await update.message.reply_text(messaggio, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

async def ricevi_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    stato = USER_DATA[user_id]
    
    if update.message.video:
        file_id = update.message.video.file_id
    elif update.message.document and update.message.document.mime_type and "video" in update.message.document.mime_type:
        file_id = update.message.document.file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        return

    stato['queue'].append(file_id)
    quanti = len(stato['queue'])
    
    # Crea la tastiera con i due bottoni cliccabili grandi sotto la chat
    tastiera = ReplyKeyboardMarkup(
        [[KeyboardButton("🏷️ Rinomina i file"), KeyboardButton("❌ Svuota la coda")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(f"📥 Ricevuto! Elementi in coda: {quanti}", reply_markup=tastiera)

async def svuota_coda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancella tutti gli elementi accumulati fino ad ora"""
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    USER_DATA[user_id]['queue'] = []
    USER_DATA[user_id]['waiting_for_title'] = False
    await update.message.reply_text("🧹 Coda svuotata con successo!", reply_markup=ReplyKeyboardRemove())

async def chiedi_titolo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    stato = USER_DATA[user_id]
    
    if not stato['queue']:
        await update.message.reply_text("La tua coda è vuota! Mandami prima dei video.", reply_markup=ReplyKeyboardRemove())
        return
        
    stato['waiting_for_title'] = True
    await update.message.reply_text(
        f"Ci sono {len(stato['queue'])} video pronti.\nScrivimi adesso il titolo base (es: antonio 1x):",
        reply_markup=ReplyKeyboardRemove()
    )

async def esegui_rinomina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    stato = USER_DATA[user_id]
    
    # Se clicca sul bottone per svuotare la coda
    if update.message.text == "❌ Svuota la coda":
        await svuota_coda(update, context)
        return
        
    # Se clicca sul bottone per rinominare
    if update.message.text == "🏷️ Rinomina i file":
        await chiedi_titolo(update, context)
        return
        
    # Se l'utente non doveva inserire un titolo di testo, ignora il messaggio
    if not stato['waiting_for_title']:
        return
        
    titolo_base = update.message.text
    stato['waiting_for_title'] = False
    
    lista_file = stato['queue'].copy()
    totale = len(lista_file)
    
    await update.message.reply_text(f"Sto elaborando {totale} video... Attendi.")
    stato['queue'] = [] 
    
    for posizione, file_id in enumerate(lista_file, start=1):
        numero = str(posizione).zfill(2)
        nuovo_nome = f"{titolo_base}{numero}.mp4"
        
        try:
            await context.bot.send_video(
                chat_id=user_id,
                video=file_id,
                caption=nuovo_nome,
                supports_streaming=True
            )
        except Exception as errore:
            try:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=file_id,
                    filename=nuovo_nome,
                    caption=nuovo_nome
                )
            except Exception:
                await update.message.reply_text(f"Errore sul file {posizione}: {str(errore)}")

    await context.bot.send_message(chat_id=user_id, text="✨ Fatto! Tutti i tuoi video sono stati elaborati.")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Comandi di amministrazione
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("aggiungi", aggiungi_admin))
    application.add_handler(CommandHandler("rimuovi", rimuovi_admin))
    application.add_handler(CommandHandler("lista", mostra_lista))
    
    # Gestione file e messaggi di testo/pulsanti
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, ricevi_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, esegui_rinomina))
    
    application.run_polling()

if __name__ == '__main__':
    main()
