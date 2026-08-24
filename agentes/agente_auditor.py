import ollama

def executar_agente_auditor(dados_servidor: str, so_alvo: str = "Ubuntu Linux") -> str:
    try:
        response = ollama.chat(
            model='smollm2:135m',
            messages=[
                {'role': 'system', 'content': 'Resuma as métricas de CPU, RAM, Disco e vulnerabilidades SSH encontradas nos dados fornecidos.'},
                {'role': 'user', 'content': dados_servidor}
            ],
            options={'num_predict': 150, 'temperature': 0.1}
        )
        return response['message']['content']
    except Exception as e:
        return f"Erro no Agente Auditor: {str(e)}"