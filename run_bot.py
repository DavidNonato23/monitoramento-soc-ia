import os
import sys
from dotenv import load_dotenv
from modulos.chatops_bot import criar_app_telegram

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Erro: TELEGRAM_BOT_TOKEN não configurado no arquivo .env ou nas variáveis de ambiente.")
        sys.exit(1)

    print("🤖 VanguardSec AI Bot ChatOps iniciado com sucesso!")
    print("📲 Abra seu Telegram e envie /start para ver os comandos.")
    
    app = criar_app_telegram(TOKEN)
    app.run_polling()