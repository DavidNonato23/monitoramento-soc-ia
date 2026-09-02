import os
import dotenv
from langchain_ollama import OllamaLLM

dotenv.load_dotenv()

def executar_agente_auditor(dados_servidor, so_alvo="Ubuntu Linux"):
    modelo_ia = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    llm = OllamaLLM(model=modelo_ia, num_predict=60, temperature=0.1)

    prompt = f"""
    Você é um Engenheiro SOC. Analise a telemetria do SO ({so_alvo}):
    {dados_servidor}

    REGRAS DE RESPOSTA:
    - Responda em no máximo 1 frase curta.
    - Destaque apenas o principal risco ou anomalia.
    """

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"⚠️ Erro no Agente Auditor: {str(e)}"