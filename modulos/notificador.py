import os
import requests

def enviar_notificacao(mensagem, token=None, chat_id=None):
    # Se não passar na chamada, tenta pegar do ambiente (.env)
    token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_ALLOWED_USER_ID")
    
    if not token or not chat_id:
        print("[-] Token ou Chat ID do Telegram não configurados.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[-] Erro ao enviar notificação Telegram: {e}")
        return False