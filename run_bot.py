import os
import sys
import logging
import socket
from datetime import datetime
from dotenv import load_dotenv
from telegram.ext import ContextTypes
from modulos.chatops_bot import criar_app_telegram, obter_ip_servidor

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID")

# Variável global de controle para identificar transição de estado (Online <-> Offline)
SERVIDOR_ESTAVA_ONLINE = True

logging.basicConfig(level=logging.INFO)

# --- MONITORAMENTO CONTÍNUO DE DISPONIBILIDADE (STATUS ON/OFF) ---
async def verificar_status_servidor(context: ContextTypes.DEFAULT_TYPE):
    global SERVIDOR_ESTAVA_ONLINE
    host = obter_ip_servidor()
    
    # 1. TRATAMENTO SEGURO DO CHAT_ID (Previne AttributeError)
    chat_id = ALLOWED_CHAT_ID
    if not chat_id and context.job and getattr(context.job, "chat_id", None):
        chat_id = context.job.chat_id

    if not chat_id:
        logging.warning("⚠️ Aviso: TELEGRAM_ALLOWED_USER_ID não definido no arquivo .env. Não foi possível enviar alerta de status.")
        return

    try:
        chat_id = int(chat_id)
    except (ValueError, TypeError):
        pass

    # 2. TESTE DE CONEXÃO REAL NA PORTA SSH (PORTA 22)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    
    try:
        s.connect((host, 22))
        s.close()
        servidor_online_agora = True
    except Exception:
        servidor_online_agora = False

    # 3. QUEDA DETECTADA (ONLINE -> OFFLINE)
    if not servidor_online_agora and SERVIDOR_ESTAVA_ONLINE:
        SERVIDOR_ESTAVA_ONLINE = False
        alerta_queda = (
            f"🔴 *ALERTA CRÍTICO: SERVIDOR DESLIGADO / OFF-LINE!*\n\n"
            f"🖥️ *Servidor Monitorado:* `{host}`\n"
            f"⚠️ *Status:* Inacessível (Porta 22/SSH sem resposta)\n"
            f"⏱️ *Horário da Queda:* {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 *Diagnóstico da IA:*\n"
            f"O monitoramento em tempo real perdeu a comunicação com o servidor. A máquina virtual/física foi desligada ou desconectada da rede.\n\n"
            f"💡 *Ação Recomendada:* Ligue a máquina virtual no VirtualBox/VMware para restabelecer os escudos de proteção."
        )
        await context.bot.send_message(chat_id=chat_id, text=alerta_queda, parse_mode="Markdown")

    # 4. RETORNO DETECTADO (OFFLINE -> ONLINE)
    elif servidor_online_agora and not SERVIDOR_ESTAVA_ONLINE:
        SERVIDOR_ESTAVA_ONLINE = True
        alerta_retorno = (
            f"🟢 *SISTEMA RESTABELECIDO: SERVIDOR LIGADO / ON-LINE!*\n\n"
            f"🖥️ *Servidor Monitorado:* `{host}`\n"
            f"✅ *Status:* Operacional (Porta 22/SSH autenticando ao vivo)\n"
            f"⏱️ *Horário do Retorno:* {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 *Diagnóstico da IA:*\n"
            f"A comunicação SSH foi restabelecida com sucesso. O sistema voltou a coletar telemetria em tempo real e os escudos SOAR estão ativos.\n\n"
            f"💡 *Próximo Passo:* Envie `/scan` no chat para verificar o estado atual da rede."
        )
        await context.bot.send_message(chat_id=chat_id, text=alerta_retorno, parse_mode="Markdown")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Erro Crítico: TELEGRAM_BOT_TOKEN não configurado no arquivo .env.")
        sys.exit(1)

    print("=========================================================")
    print("🤖 VanguardSec AI — ChatOps SOAR (Monitoramento On-Premise)")
    print(f"🖥️ Servidor Alvo: {obter_ip_servidor()}")
    print("📲 Pressione Ctrl+C para encerrar o bot.")
    print("=========================================================\n")

    try:
        app = criar_app_telegram(TOKEN)
        
        # Registra a checagem de estado a cada 5 segundos
        job_queue = app.job_queue
        if job_queue:
            job_queue.run_repeating(verificar_status_servidor, interval=5, first=1)
            
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\n🛑 ChatOps encerrado pelo operador.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro ao inicializar o Bot: {e}")
        sys.exit(1)