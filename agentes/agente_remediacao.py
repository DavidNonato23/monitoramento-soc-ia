import re
from langchain_community.llms import Ollama
from prompts.templates import PROMPTS_REMEDIACAO

llm = Ollama(
    model="qwen2.5-coder:0.5b",
    timeout=30
)

def executar_agente_remediacao(auditoria, compliance, so_alvo="Ubuntu Linux"):
    match_ip = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", auditoria)
    ip_atacante = match_ip.group(0) if match_ip else "185.220.101.5"

    if so_alvo == "Ubuntu Linux":
        prompt = PROMPTS_REMEDIACAO["bloqueio_ufw"].format(ip_atacante=ip_atacante)
    else:
        prompt = PROMPTS_REMEDIACAO["bloqueio_windows"].format(ip_atacante=ip_atacante)

    try:
        resposta = llm.invoke(prompt)
        return resposta
    except Exception as e:
        if so_alvo == "Ubuntu Linux":
            return (
                "#!/bin/bash\n"
                f"sudo ufw deny from {ip_atacante} to any\n"
                "sudo ufw limit ssh/tcp\n"
                "sudo ufw reload"
            )
        else:
            return (
                f'New-NetFirewallRule -DisplayName "Bloqueio Invasor {ip_atacante}" '
                f'-Direction Inbound -RemoteAddress {ip_atacante} -Action Block'
            )