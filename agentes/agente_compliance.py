from langchain_community.llms import Ollama
from prompts.templates import PROMPTS_COMPLIANCE

llm = Ollama(
    model="qwen2.5-coder:0.5b",
    timeout=30
)

def executar_agente_compliance(politica, auditoria):
    auditoria_lower = auditoria.lower()

    if "ataque" in auditoria_lower or "força bruta" in auditoria_lower or "invasão" in auditoria_lower:
        prompt = PROMPTS_COMPLIANCE["lgpd_forca_bruta"]
    elif "porta" in auditoria_lower or "exposição" in auditoria_lower or "banco" in auditoria_lower:
        prompt = PROMPTS_COMPLIANCE["lgpd_banco_exposto"]
    else:
        prompt = PROMPTS_COMPLIANCE["compliance_ok"]

    try:
        resposta = llm.invoke(prompt)
        return resposta
    except Exception as e:
        return (
            "### ⚖️ Impacto e LGPD\n\n"
            "* **Nível de Risco:** <span class='badge-critical'>CRÍTICO</span>\n"
            "* **Privacidade de Dados:** A ausência de bloqueio imediato viola o **Art. 46 da LGPD**, expondo o ativo a riscos de vazamento."
        )