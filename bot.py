import logging
from collections import defaultdict
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# =========================================================================
# INSERISCI I TUOI DATI REALI QUI SOTTO
# =========================================================================
TOKEN = "8662944209:AAGZ2vRusJcV4TO2yCfU-hSjVZ6vdpVGTX4"
SUPER_ADMIN_ID = 670198268     # <--- Metti qui il TUO ID personale (numero)

# Inserisci qui dentro gli username fissi dei tuoi amici (senza la @, tutto in minuscolo)
# Esempio: ADMINS_FISSI = {"antonio_99", "luca_rossi"}
ADMINS_FISSI = {"paolorimedio", "sclerobotomia"}
# =========================================================================

# Lista per gli admin aggiunti temporaneamente via chat
ADMINS_TEMPORANEI = set()

USER_DATA = defaultdict(lambda: {'queue': [], 'waiting_for_title': False})

def controlla_utente(update: Update) -> bool:
    """Controlla se l'utente è autorizzato tramite ID o Username"""
    user = update.effective_user
    username = user.username.lower() if user.username else ""
    user_id = user.id
    
    return (user_id == SUPER_ADMIN_ID or 
            username in ADMINS_FISSI or 
            username in ADMINS_TEMPORANEI or 
            str(user_id) in ADMINS_TEMPORANEI)

# -------------------------------------------------------------------------
# COMANDI DI GESTIONE PER IL SUPER ADMIN (CORRETTI SENZA BLOCCO NUMERI)
# -------------------------------------------------------------------------
async def aggiungi_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPER_ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Uso corretto: `/aggiungi @username` o ID", parse_mode="Markdown")
        return
    
    # Prende l'input, toglie la @, pulisce gli spazi e mette in minuscolo
    nuovo_admin = " ".join(context.args).replace("@", "").strip().lower()
    ADMINS_TEMPORANEI.add(nuovo_admin)
    await update.message.reply_text(f"✅ L'utente `{nuovo_admin}` è stato aggiunto agli Admin!", parse_mode="Markdown")

async def rimuovi_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPER_ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Uso corretto: `/rimuovi @username` o ID", parse_mode="Markdown")
        return
    
    admin_da_togliere = " ".join(context.args).replace("@", "").strip().lower()
    if admin_da_togliere in ADMINS_TEMPORANEI:
        ADMINS_TEMPORANEI.remove(admin_da_togliere)
        await update.message.reply_text(f"✅ L'utente `{admin_da_togliere}` è stato rimosso dagli Admin.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Questo utente non era presente nella lista temporanea (o è fisso nel codice).")

async def mostra_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPER_ADMIN_ID:
        return
    testo = f"👑 **Super Admin ID**: {SUPER_ADMIN_ID}\n\n"
    
    testo += "👥 **Admin Fissi (nel codice)**:\n"
    if not ADMINS_FISSI or "metti_username_amico_1" in ADMINS_FISSI:
        testo += "• Nessuno\n"
    else:
        for adm in ADMINS_FISSI:
            testo += f"• @{adm}\n"
            
    testo += "\n➕ **Admin Aggiunti via chat**:\n"
    if not ADMINS_TEMPORANEI:
        testo += "• Nessuno al momento\n"
    else:
        for adm in ADMINS_TEMPORANEI:
            testo += f"• @{adm}\n"
            
    await update.message.reply_text(testo, parse_mode="Markdown")

# -------------------------------------------------------------------------
# FUNZIONI PRINCIPALES DEL BOT (CODE E BOTTONI)
# -------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    USER_DATA[user_id] = {'queue': [], 'waiting_for_title': False}
    
    messaggio = "Ciao! Sei un utente autorizzato.\nInviami pure i video o i file in serie.\nQuando hai finito, usa i bottoni in basso per procedere."
    if user_id == SUPER_ADMIN_ID:
        messaggio += "\n\n⚙️ **Comandi Creatore**:\n`/aggiungi @username` o ID\n`/rimuovi @username` o ID\n`/lista`"
        
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
    
    tastiera = ReplyKeyboardMarkup(
        [[KeyboardButton("🏷️ Rinomina i file"), KeyboardButton("❌ Svuota la coda")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(f"📥 Ricevuto! Elementi in coda: {quanti}", reply_markup=tastiera)

async def svuota_coda(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"Ci sono {len(stato['queue'])} video pronti nella TUA coda.\nScrivimi adesso il titolo base (es: antonio 1x):",
        reply_markup=ReplyKeyboardRemove()
    )

async def esegui_rinomina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not controlla_utente(update): return
    user_id = update.effective_user.id
    stato = USER_DATA[user_id]
    
    if update.message.text == "❌ Svuota la coda":
        await svuota_coda(update, context)
        return
        
    if update.message.text == "🏷️ Rinomina i file":
        await chiedi_titolo(update, context)
        return
        
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
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("aggiungi", aggiungi_admin))
    application.add_handler(CommandHandler("rimuovi", rimuovi_admin))
    application.add_handler(CommandHandler("lista", mostra_lista))
    
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, ricevi_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, esegui_rinomina))
    
    application.run_polling()

if __name__ == '__main__':
    main()
