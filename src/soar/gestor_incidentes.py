import os
import json
from datetime import datetime

BASE_INCIDENTES = "historico_incidentes.json"

def registrar_incidente(scan_data, metricas, r_ia):
    """Salva um novo incidente na base geral se houver anomalias detectadas."""
    falhas = int(metricas.get("logins_falhos", 0))
    portas = int(metricas.get("portas_abertas", 0))
    
    if falhas == 0 and portas == 0:
        return # Se estiver limpo, não gera incidente de ataque

    incidentes = carregar_todos_incidentes()
    
    novo_incidente = {
        "id": f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "data": scan_data.get("data"),
        "host": scan_data.get("host"),
        "tipo": "Brute Force / Tentativa de Acesso" if falhas > 0 else "Exposição de Porta",
        "severidade": "CRÍTICA" if falhas > 5 else "MÉDIA",
        "detalhes": f"{falhas} falhas de login registradas. {portas} portas abertas.",
        "status": "NOVO (Em Triagem)"
    }
    
    incidentes.insert(0, novo_incidente) # Adiciona no topo
    
    with open(BASE_INCIDENTES, "w", encoding="utf-8") as f:
        json.dump(incidentes, f, ensure_ascii=False, indent=4)

def carregar_todos_incidentes():
    if os.path.exists(BASE_INCIDENTES):
        with open(BASE_INCIDENTES, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def atualizar_status_incidente(inc_id, novo_status):
    incidentes = carregar_todos_incidentes()
    for inc in incidentes:
        if inc["id"] == inc_id:
            inc["status"] = novo_status
    with open(BASE_INCIDENTES, "w", encoding="utf-8") as f:
        json.dump(incidentes, f, ensure_ascii=False, indent=4)