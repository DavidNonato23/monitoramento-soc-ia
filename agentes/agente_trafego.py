import os
import dotenv
from langchain_ollama import OllamaLLM

dotenv.load_dotenv()

def executar_agente_trafego(info_rede, metricas_soc):
    modelo_ia = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    # num_predict=150 garante respostas super rápidas
    llm = OllamaLLM(model=modelo_ia, num_predict=150)
    
    ip_alvo = info_rede.get("ip", "Desconhecido")
    tipo_rede = info_rede.get("tipo_rede", "Desconhecido")
    risco_origem = info_rede.get("nivel_risco_origem", "Baixo")
    cliente = info_rede.get("proprietario_vinculado", "Não Identificado")
    
    portas = metricas_soc.get("portas_abertas", "0")
    conexoes = metricas_soc.get("conexoes_estab", "0")
    logins_falhos = metricas_soc.get("logins_falhos", "0")

    prompt = f"""
    Você é um Engenheiro SOC Especialista em NTA (Network Traffic Analysis).
    Analise os seguintes dados do fluxo de rede em tempo real:

    - IP Auditado: {ip_alvo}
    - Classificação da Origem: {tipo_rede}
    - Nível de Risco do Segmento: {risco_origem}
    - Cliente/Proprietário Vinculado: {cliente}
    - Conexões Ativas Registradas: {conexoes}
    - Superfície Exposta (Portas Abertas): {portas}
    - Tentativas Falhas de Acesso: {logins_falhos}

    REGRAS DE RESPOSTA (MUITO IMPORTANTE):
    - Seja EXTREMAMENTE CONCISO e DIRETO.
    - Responda em APENAS 2 frases ou 2 tópicos curtos apontando a origem do tráfego e a severidade da exposição.
    - Não faça introduções nem saudações.
    """

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"⚠️ Erro no Agente de Tráfego: {str(e)}"