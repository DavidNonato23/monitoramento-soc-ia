import os
import dotenv
from langchain_ollama import OllamaLLM

dotenv.load_dotenv()

def executar_agente_compliance(politica_norma, laudo_auditoria):
    modelo_ia = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    llm = OllamaLLM(model=modelo_ia, num_predict=150)
    
    prompt = f"""
    Você é Auditor LGPD/ISO27001. Avalie este laudo técnico em relação à política:
    LAUDO: {laudo_auditoria}
    POLÍTICA: {politica_norma}

    REGRAS DE RESPOSTA (MUITO IMPORTANTE):
    - Seja EXTREMAMENTE CONCISO.
    - Indique o Nível de Risco (Baixo, Médio, Alto, Crítico) e no máximo 2 artigos/normas violadas em linhas curtas.
    """

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"⚠️ Erro no Agente Compliance: {str(e)}"