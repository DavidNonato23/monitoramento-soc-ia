import json
import urllib.request

def enviar_alerta_webhook(webhook_url, host, so, compliance_info):
    """Envia payload JSON para sistemas externos de monitoramento."""
    if not webhook_url:
        return False

    payload = {
        "text": f"🚨 *ALERTA VANGUARDSEC AI SOC*\n\n*Target:* `{host}` ({so})\n*Status Compliance:* {compliance_info}"
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except Exception as e:
        print(f"Erro Webhook: {e}")
        return False