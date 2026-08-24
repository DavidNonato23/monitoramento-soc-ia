# Módulo de Políticas e Frameworks de Conformidade
# Convertido a partir da ABNT NBR ISO/IEC 17021

POLITICA_ISO_17021 = """
NORMA ISO/IEC 17021 (AUDITORIA E REGISTRO):
1. EVIDENCIA OBJETIVA: Auditorias devem se basear em dados reais de logs e metricas sem pressuposicoes.
2. RASTREABILIDADE E CONFIDENCIALIDADE: Registros de acessos e alteracoes devem ser salvos com seguranca.
3. IDENTIFICACAO DE NAO-CONFORMIDADES: Falhas de seguranca, acessos nao autorizados e portas expostas devem ser classificadas como nao-conformidades.
4. ACAO CORRETIVA: Scripts de mitigacao devem eliminar a causa raiz das falhas apontadas.
"""

def obter_politica_ativa():
    return POLITICA_ISO_17021