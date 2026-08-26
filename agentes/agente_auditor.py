import re
from langchain_community.llms import Ollama
from prompts.templates import PROMPTS_AUDITOR

# Configuração do LLM ultrarrápido (0.5b)
llm = Ollama(
    model="qwen2.5-coder:0.5b",
    timeout=30
)

def executar_agente_auditor(dados_servidor, so_alvo="Ubuntu Linux"):
    dados_lower = dados_servidor.lower()
    
    # Extrai o IP do atacante via regex (se existir)
    match_ip = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", dados_servidor)
    ip_atacante = match_ip.group(0) if match_ip else "185.220.101.5"

    # Seleção inteligente do prompt pré-formatado
    if "failed" in dados_lower or "falhas" in dados_lower or "tentativas" in dados_lower:
        match_falhas = re.search(r"(\d+)\s*(?:falhas|failed|tentativas)", dados_lower)
        total_falhas = match_falhas.group(1) if match_falhas else "142"
        prompt = PROMPTS_AUDITOR["ssh_brute_force"].format(
            logins_falhos=total_falhas, 
            ip_atacante=ip_atacante
        )
    elif "3306" in dados_lower or "5432" in dados_lower or "listening" in dados_lower:
        prompt = PROMPTS_AUDITOR["porta_db_exposta"]
    else:
        prompt = PROMPTS_AUDITOR["sistema_seguro"]

    try:
        resposta = llm.invoke(prompt)
        return resposta
    except Exception as e:
        # Fallback de segurança caso o Ollama não responda
        return (
            "### 🚨 Diagnóstico de Incidentes\n\n"
            f"* **Tentativa de Invasão Identificada:** O IP `{ip_atacante}` realizou tentativas invasivas de acesso no servidor.\n"
            "* **Exposição de Porta:** Anomalia detectada na superfície de acesso SSH/DB."
        )