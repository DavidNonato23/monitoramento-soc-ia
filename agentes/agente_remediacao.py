import os
import dotenv
from langchain_ollama import OllamaLLM

dotenv.load_dotenv()

def executar_agente_remediacao(laudo_auditoria, laudo_compliance, so_alvo="Ubuntu Linux"):
    modelo_ia = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    llm = OllamaLLM(model=modelo_ia, num_predict=120)
    
    prompt = f"""
    Você é um Engenheiro SOAR ({so_alvo}).
    Gere comandos de terminal para bloquear o invasor com base nestes laudos:
    {laudo_auditoria}

    REGRAS DE RESPOSTA:
    - Retorne APENAS o bloco de código de terminal com os comandos (ex: ufw, iptables ou netsh).
    - Não escreva NENHUMA explicação ou introdução antes ou depois dos comandos.
    """

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return "# Error: Não foi possível gerar o playbook SOAR"