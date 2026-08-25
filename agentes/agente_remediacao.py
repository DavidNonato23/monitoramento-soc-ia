import os
import requests

MODELO_OLLAMA = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

def executar_agente_remediacao(diagnostico_analista, parecer_especialista, so_alvo="Ubuntu Linux"):
    """Tier 3 - Engenheiro SOAR: Construção do Playbook de Contenção em Código."""
    sintaxe = "Bash" if so_alvo == "Ubuntu Linux" else "PowerShell"
    
    prompt = f"""
Escreva um script simples em {sintaxe} para bloquear o IP invasor citado no diagnóstico.

Diagnóstico:
{diagnostico_analista}

REGRAS RÍGIDAS:
- Retorne APENAS comandos limpos de firewall executáveis, como:
sudo ufw deny from <IP> to any
sudo ufw limit ssh/tcp
sudo ufw reload
- NÃO use comandos awk, sed ou pipelines complexos.
- NÃO escreva explicações fora do código.
"""
    try:
        payload = {
            "model": MODELO_OLLAMA, 
            "prompt": prompt, 
            "stream": False,
            "options": {"num_predict": 150}
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code == 200:
            script_gerado = response.json().get("response", "")
            return script_gerado.replace("```bash", "").replace("```powershell", "").replace("```", "").strip()
        return "# Erro na geração do script de bloqueio"
    except Exception as e:
        return f"# Erro no script de remediação: {str(e)}"