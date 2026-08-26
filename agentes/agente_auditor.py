import os
import dotenv
from langchain_ollama import OllamaLLM

dotenv.load_dotenv()

def executar_agente_auditor(dados_servidor, so_alvo="Ubuntu Linux"):
    modelo_ia = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    llm = OllamaLLM(model=modelo_ia, num_predict=150)
    
    prompt = f"""
    Você é um Engenheiro SOC. Analise estes logs do SO ({so_alvo}):
    {dados_servidor}

    REGRAS DE RESPOSTA (MUITO IMPORTANTE):
    - Seja EXTREMAMENTE CONCISO e DIRETO.
    - Responda em no máximo 3 tópicos curtos de 1 linha cada.
    - Apresente apenas os riscos críticos identificados.
    """

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"⚠️ Erro no Agente Auditor: {str(e)}"