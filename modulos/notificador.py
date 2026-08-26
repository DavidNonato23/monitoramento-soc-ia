import requests
import os

def enviar_alerta_webhook(url_webhook: str, dados_incidente: dict) -> bool:
    """
    Envia um alerta genérico de incidente via Webhook (Discord/Slack/SIEM).
    """
    if not url_webhook:
        return False

    payload = {
        "content": f"🚨 **ALERTA SOC** | Servidor: {dados_incidente.get('host', 'N/A')} | Incidente Detectado!"
    }

    try:
        response = requests.post(url_webhook, json=payload, timeout=10)
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"Erro ao enviar webhook: {e}")
        return False


def enviar_notificacao(mensagem: str, token: str, chat_id: str) -> bool:
    """
    Envia uma mensagem de notificação para o Telegram via Bot API.
    """
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao enviar notificação Telegram: {e}")
        return False