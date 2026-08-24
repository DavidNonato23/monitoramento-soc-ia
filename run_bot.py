import os
import logging
from telegram.ext import Application, CallbackQueryHandler
from modulos.chatops_bot import callback_handler

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Cole o seu NOVO Token revogado aqui ou defina na variável de ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "COLE_SEU_NOVO_TOKEN_AQUI")

def main():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "COLE_SEU_NOVO_TOKEN_AQUI":
        print("❌ Defina o TELEGRAM_BOT_TOKEN antes de iniciar o bot!")
        return

    print("🤖 VanguardSec ChatOps Bot está ONLINE e aguardando comandos...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Registra o gerenciador dos botões do Telegram
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Inicia o bot em loop contínuo
    app.run_polling()

if __name__ == "__main__":
    main()