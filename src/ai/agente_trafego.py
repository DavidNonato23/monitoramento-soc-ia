import os
import dotenv
from langchain_ollama import OllamaLLM

dotenv.load_dotenv()

def executar_agente_trafego(dados_servidor, metricas_soc="", so_alvo="Ubuntu Linux"):
    modelo_ia = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    llm = OllamaLLM(model=modelo_ia, num_predict=60, temperature=0.1)

    prompt = f"""
    Você é um Analista de Tráfego de Rede.
    Telemetria: {dados_servidor}

    REGRAS DE RESPOSTA:
    - Responda em no máximo 1 frase curta sobre o comportamento da rede e portas.
    """

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"⚠️ Erro no Agente Trafego: {str(e)}"