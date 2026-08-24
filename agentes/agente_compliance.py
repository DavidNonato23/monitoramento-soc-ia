import ollama

def executar_agente_compliance(politicas: str, relatorio_auditoria: str) -> str:
    prompt_sistema = f"""
    Você é um Auditor de Compliance ISO 17021.
    Diretrizes da Norma:
    {politicas}

    Com base na auditoria recebida, gere um resumo direto:
    - [NÃO CONFORME]: Se houver falhas críticas de login, portas desnecessárias ou falha de firewall.
    - [ALERTA]: Riscos médios ou alterações pendentes.
    - [CONFORME]: Controles ativos e seguros.
    Seja extremamente breve e objetivo.
    """

    try:
        response = ollama.chat(
            model='smollm2:135m',
            messages=[
                {'role': 'system', 'content': prompt_sistema},
                {'role': 'user', 'content': f"Dados de Auditoria:\n{relatorio_auditoria}"}
            ],
            options={'num_predict': 150, 'temperature': 0.1}
        )
        return response['message']['content']
    except Exception as e:
        return f"Erro no Agente de Compliance: {str(e)}"