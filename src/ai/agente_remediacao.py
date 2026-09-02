import os
import dotenv
from langchain_ollama import OllamaLLM

dotenv.load_dotenv()

def executar_agente_remediacao(dados_servidor, laudo_auditoria="", laudo_compliance="", so_alvo="Ubuntu Linux"):
    modelo_ia = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    llm = OllamaLLM(model=modelo_ia, num_predict=60, temperature=0.1)

    prompt = f"""
    Você é um especialista em SOAR/Resposta a Incidentes.
    Laudo SOC: {laudo_auditoria}
    Laudo Compliance: {laudo_compliance}

    REGRAS DE RESPOSTA:
    - Indique apenas o comando de mitigação (ex: ufw deny / kill PID) ou 'Nenhuma ação necessária'.
    - Máximo de 1 linha.
    """

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"⚠️ Erro no Agente Remediação: {str(e)}"