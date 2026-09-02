import os
import json
import logging
import requests

PASTA_DATA = "./data/"
ARQUIVO_CISA_KEV = os.path.join(PASTA_DATA, "cisa_kev.json")
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

def atualizar_feed_cisa_kev() -> dict:
    try:
        response = requests.get(CISA_KEV_URL, timeout=5)
        if response.status_code == 200:
            dados = response.json()
            os.makedirs(PASTA_DATA, exist_ok=True)
            with open(ARQUIVO_CISA_KEV, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            return dados
    except Exception as e:
        logging.warning(f"Falha ao conectar com o feed CISA KEV: {e}")

    if os.path.exists(ARQUIVO_CISA_KEV):
        try:
            with open(ARQUIVO_CISA_KEV, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {"vulnerabilities": []}

def gerar_estatisticas_globais() -> dict:
    dados_cisa = atualizar_feed_cisa_kev()
    vulnerabilidades = dados_cisa.get("vulnerabilities", [])
    total_cisa = len(vulnerabilidades)
    cves_recentes = [v.get("cveID") for v in vulnerabilidades[:5] if "cveID" in v]

    return {
        "total_vulnerabilidades_cisa": total_cisa,
        "amostra_cves_criticos": cves_recentes,
        "status_feed": "ONLINE" if total_cisa > 0 else "OFFLINE / CACHE"
    }