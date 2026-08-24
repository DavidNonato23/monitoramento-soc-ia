import requests

def enviar_alerta_webhook(webhook_url: str, servidor: str, so: str, total_vulnerabilidades: str):
    """
    Envia alertas formatados para o Slack ou Discord quando uma varredura é concluída.
    """
    payload = {
        "content": f"🚨 **VanguardSec AI — Alerta de Segurança** 🚨\n"
                   f"**Servidor:** `{servidor}` ({so})\n"
                   f"**Status:** Varredura Concluída\n"
                   f"**Resumo:**\n```{total_vulnerabilidades[:500]}...```"
    }
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        print(f"Erro ao enviar webhook: {e}")