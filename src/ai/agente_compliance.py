import os
import dotenv
from langchain_ollama import OllamaLLM

dotenv.load_dotenv()

def executar_agente_compliance(dados_servidor, laudo_auditoria="", so_alvo="Ubuntu Linux"):
    modelo_ia = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    llm = OllamaLLM(model=modelo_ia, num_predict=60, temperature=0.1)

    prompt = f"""
    Você é um Auditor LGPD/ISO 27001.
    Telemetria: {dados_servidor}
    Laudo SOC: {laudo_auditoria}

    REGRAS DE RESPOSTA:
    - Responda em no máximo 1 frase curta.
    - Cite a norma ou artigo violado (ex: Art. 46 LGPD / Controle A.9 ISO 27001) ou declare conformidade.
    """

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"⚠️ Erro no Agente Compliance: {str(e)}"