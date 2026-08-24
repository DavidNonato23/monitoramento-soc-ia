import ollama

def executar_agente_remediacao(relatorio_auditoria: str, relatorio_compliance: str, so_alvo: str = "Ubuntu Linux") -> str:
    try:
        response = ollama.chat(
            model='smollm2:135m',
            messages=[
                {'role': 'system', 'content': 'Escreva apenas comandos bash para corrigir falhas de SSH e ativar o UFW firewall no Ubuntu. Nao escreva texto.'},
                {'role': 'user', 'content': relatorio_auditoria}
            ],
            options={'num_predict': 100, 'temperature': 0.1}
        )
        return response['message']['content']
    except Exception as e:
        return f"# Erro ao gerar script: {str(e)}"