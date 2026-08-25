import os
import requests

MODELO_OLLAMA = os.getenv("OLLAMA_MODEL_COMPLIANCE", "qwen2.5:3b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

def executar_agente_compliance(politica_norma, diagnostico_analista):
    """Tier 2 - Especialista em Compliance e Riscos (LGPD & ISO 27001)."""
    prompt = f"""
Você é um Consultor de Compliance e Riscos (LGPD / ISO 27001) apresentando um resumo para um diretor de empresa.

POLÍTICA DE SEGURANÇA E NORMAS APLICÁVEIS:
{politica_norma}

DIAGNÓSTICO DA SITUAÇÃO ATUAL:
{diagnostico_analista}

Resuma a avaliação em PORTUGUÊS de forma direta, simples e concisa (máximo 3 tópicos):
1. **Nível de Risco:** [BAIXO], [MÉDIO] ou <span class='badge-critical'>CRÍTICO</span>.
2. **Impacto Regulatório:** Indique qual artigo da LGPD ou diretriz da ISO foi violado.
3. **Ação Preventiva Sugerida:** Ação recomendada para adequação.
"""
    try:
        payload = {
            "model": MODELO_OLLAMA, 
            "prompt": prompt, 
            "stream": False,
            "options": {
                "num_predict": 180,
                "temperature": 0.2
            }
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get("response", "Análise de compliance não concluída.")
        return "⚠️ Não foi possível avaliar a conformidade no momento."
    except Exception as e:
        return f"⚠️ Erro ao consultar política: {str(e)}"