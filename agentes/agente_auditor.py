import os
import requests

MODELO_OLLAMA = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

def executar_agente_auditor(telemetria_bruta, so_alvo="Ubuntu Linux"):
    """Tier 1 - Analista de SOC: Identificação de anomalias e triagem inicial."""
    prompt = f"""
Você é um Analista de Segurança Cibernética apresentando um diagnóstico para um Diretor de Empresa (não técnico).
Analise os logs brutos e resuma a situação do servidor ({so_alvo}):

{telemetria_bruta}

Escreva em PORTUGUÊS de forma MUITO SIMPLES e MASTIGADA em 3 tópicos:
1. **Status Geral:** Ex: Tentativa de invasão identificada / Sistema operando normalmente.
2. **Origem da Ameaça:** Ex: Identificado IP x.x.x.x tentando adivinhar senhas de acesso.
3. **Serviços Afetados:** Ex: Porta SSH ou Banco de Dados.

Seja direto, curto e sem termos de código complexos.
"""
    try:
        payload = {
            "model": MODELO_OLLAMA, 
            "prompt": prompt, 
            "stream": False,
            "options": {"num_predict": 180, "temperature": 0.2}
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json().get("response", "Análise não concluída.")
        return "⚠️ Não foi possível gerar a análise técnica no momento."
    except Exception as e:
        return f"⚠️ Erro no Analista Tier 1: {str(e)}"