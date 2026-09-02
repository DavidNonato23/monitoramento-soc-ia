import os
import sys
import re
import json
import time
import socket
import hashlib
import sqlite3
import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pymupdf as fitz
from datetime import datetime, timedelta
import paramiko

# -----------------------------------------------------------------------------
# Resolução de Caminhos do Projeto (Fix de Importação)
# -----------------------------------------------------------------------------
RAIZ_PROJETO = os.path.dirname(os.path.abspath(__file__))
if RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, RAIZ_PROJETO)

try:
    from src.ai.agente_threat_intel import gerar_estatisticas_globais
except ImportError:
    def gerar_estatisticas_globais() -> dict:
        return {}

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Diretórios base
PASTA_DATA = "./data/"
PASTA_POLITICAS = "./politicas/"
PASTA_RELATORIOS = "./relatorios_pdf/"
PASTA_PROMPTS = "./prompts/"

os.makedirs(PASTA_DATA, exist_ok=True)
os.makedirs(PASTA_POLITICAS, exist_ok=True)
os.makedirs(PASTA_RELATORIOS, exist_ok=True)

DB_NAME = os.path.join(PASTA_DATA, "vanguard_sec.db")
ARQUIVO_EXPORTACAO_POWERBI = os.path.join(PASTA_DATA, "vanguard_powerbi_data.csv")

# Configurações do Ollama Local
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODELO_OLLAMA = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# Credenciais do Alvo SSH
SSH_HOST = os.getenv("SSH_HOST", "192.168.15.3")
SSH_PORT = int(os.getenv("SSH_PORT", "22"))
SSH_USER = os.getenv("SSH_USER", "servidor")
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "123456")

# Flags Operacionais
AUTO_REMEDIATION = True
ACTIVE_DEFENSE = True
GERAR_PDF = True

_ULTIMO_HASH_LOG = None


def inicializar_banco() -> None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            severidade TEXT,
            tipo_evento TEXT,
            status_sistema TEXT,
            ip_origem TEXT,
            parecer_soc TEXT,
            compliance_lgpd TEXT,
            acao_soar_gerada TEXT,
            analise_trafego TEXT,
            modelo_ia_utilizado TEXT,
            relatorio_normativo TEXT,
            log_raw TEXT,
            origem TEXT
        )
    ''')
    conn.commit()
    conn.close()


def extrair_json_defensivo(texto_resposta: str) -> dict:
    """Parser robusto para extrair JSON sem falhar com marcações markdown."""
    texto_limpo = texto_resposta.strip()
    try:
        return json.loads(texto_limpo)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto_limpo, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    inicio = texto_limpo.find("{")
    fim = texto_limpo.rfind("}")
    if inicio != -1 and fim != -1 and fim > inicio:
        try:
            return json.loads(texto_limpo[inicio:fim+1])
        except json.JSONDecodeError:
            pass

    return {}


def consultar_agente_ia_rapido(caminho_prompt: str, log_raw: str, contexto_extra: str = "") -> dict:
    """Invoca o agente de forma enxuta e otimizada (baixa latência)."""
    if not os.path.exists(caminho_prompt):
        return {}

    try:
        with open(caminho_prompt, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return {}

    prompt_estruturado = (
        f"LOG: '{log_raw}' | CONTEXTO: '{contexto_extra}'\n"
        f"INSTRUÇÃO: {cfg.get('system_prompt', '')}\n"
        f"Schema JSON Obrigatório: {json.dumps(cfg.get('schema_resposta', {}))}\n"
        "RESPONDA EXCLUSIVAMENTE COM O OBJETO JSON BRUTO:"
    )

    payload = {
        "model": MODELO_OLLAMA,
        "prompt": prompt_estruturado,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 0.1,
            "num_predict": 80  # Limita os tokens gerados para resposta imediata
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=15)
        if response.status_code == 200:
            return extrair_json_defensivo(response.json().get("response", ""))
    except Exception:
        pass

    return {}


def contar_reincidencia_ip(ip_atacante: str) -> int:
    if not ip_atacante or ip_atacante in ["127.0.0.1", SSH_HOST]:
        return 1
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        limite_tempo = (datetime.now() - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT COUNT(*) FROM scans WHERE ip_origem = ? AND timestamp >= ?", (ip_atacante, limite_tempo))
        row = cursor.fetchone()
        conn.close()
        return (row[0] + 1) if row else 1
    except Exception:
        return 1


def aplicar_bloqueio_ufw_temporal(ip_atacante: str) -> str:
    if not AUTO_REMEDIATION:
        return f"[SOAR SIMULAÇÃO] Regra UFW pendente para {ip_atacante}"
        
    if not ip_atacante or ip_atacante in ["127.0.0.1", "0.0.0.0", SSH_HOST]:
        return f"[SOAR SAFEGUARD] Bloqueio ignorado para IP local/servidor '{ip_atacante}'."

    reincidencias = contar_reincidencia_ip(ip_atacante)
    if reincidencias < 2:
        return f"[SOAR THRESHOLD] IP {ip_atacante} sob observação ({reincidencias}ª ocorrência). Limiar para UFW é 2."

    comando = f"echo '{SSH_PASSWORD}' | sudo -S ufw insert 1 deny from {ip_atacante} to any"
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=3)
        
        stdin, stdout, stderr = ssh.exec_command(comando)
        err = stderr.read().decode('utf-8', errors='ignore').strip()
        ssh.close()
        
        if "Rule inserted" in err or "Rules updated" in err or not err:
            return f"[SOAR SUCCESS] IP {ip_atacante} bloqueado com sucesso no UFW."
        return f"[SOAR ERROR] Falha na injeção UFW: {err}"
    except Exception as e:
        return f"[SOAR CRITICAL] Erro SSH UFW: {str(e)}"


def derrubar_sessao_ssh_ativa(ip_atacante: str) -> str:
    if not ip_atacante or ip_atacante in ["127.0.0.1", SSH_HOST]:
        return "[KILL SWITCH] IP inválido."

    comando_find = f"ps aux | grep 'sshd:.*@{ip_atacante}' | grep -v grep | awk '{{print $2}}'"
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=3)
        
        stdin, stdout, stderr = ssh.exec_command(comando_find)
        pids = stdout.read().decode('utf-8', errors='ignore').splitlines()
        
        if pids:
            for pid in pids:
                ssh.exec_command(f"echo '{SSH_PASSWORD}' | sudo -S kill -9 {pid}")
            ssh.close()
            return f"[KILL SWITCH] Processos {pids} encerrados para o IP {ip_atacante}."
        
        ssh.close()
        return "[KILL SWITCH] Nenhuma sessão ativa."
    except Exception as e:
        return f"[KILL SWITCH ERROR] {str(e)}"


def extrair_ip_do_log(log_texto: str, ip_servidor_padrao: str) -> str:
    match = re.search(r'(?:from|invalid user\s+\S+|-)\s+([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', log_texto)
    if match:
        ip_encontrado = match.group(1)
        if ip_encontrado != ip_servidor_padrao:
            return ip_encontrado
    return ip_servidor_padrao


def coletar_logs_multi_servico() -> dict:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=3)
        comando = "sudo journalctl -u ssh -n 5 --no-pager 2>/dev/null | grep -iE 'Failed|Invalid|Accepted' | tail -n 1"
        
        stdin, stdout, stderr = ssh.exec_command(comando)
        log_saida = stdout.read().decode('utf-8', errors='ignore').strip()
        ssh.close()
        
        if log_saida and len(log_saida) > 5:
            log_lower = log_saida.lower()
            ip_detectado = extrair_ip_do_log(log_saida, SSH_HOST)
            is_ataque = any(term in log_lower for term in ["failed", "invalid"])
            
            return {
                "origem": "Linux Ubuntu Target (Real Log)",
                "severidade": "ALTO" if is_ataque else "INFO",
                "tipo": "Ataque Detectado (Brute Force SSH)" if is_ataque else "Acesso SSH Autorizado",
                "ip": ip_detectado,
                "status": "ALERTA / SOB ATAQUE" if is_ataque else "OPERACIONAL",
                "log_raw": log_saida,
                "is_ataque": is_ataque
            }
    except Exception:
        pass

    return {"is_ataque": False, "log_raw": "Nenhum evento novo", "ip": SSH_HOST}


def consultar_geoip(ip: str) -> dict:
    if not ip or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("127.0.0.1"):
        return {"pais": "Rede Privada", "cidade": "LAN", "provedor": "Interno"}
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp", timeout=2)
        if res.status_code == 200:
            dados = res.json()
            if dados.get("status") == "success":
                return {"pais": dados.get("country"), "cidade": dados.get("city"), "provedor": dados.get("isp")}
    except Exception:
        pass
    return {"pais": "Desconhecido", "cidade": "Desconhecido", "provedor": "Desconhecido"}


def consultar_pasta_politicas() -> str:
    caminho = os.path.join(PASTA_POLITICAS, "norma_iso27001.pdf")
    conteudo_pdf = ""
    if os.path.exists(caminho):
        try:
            doc = fitz.open(caminho)
            conteudo_pdf = str(doc[0].get_text())[:1000]
            doc.close()
        except Exception:
            pass
    return conteudo_pdf


def gerar_relatorio_pdf(dados: dict, info_geo: dict) -> str:
    if not GERAR_PDF:
        return "PDF desativado."

    nome_arquivo = f"laudo_soc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    caminho_pdf = os.path.join(PASTA_RELATORIOS, nome_arquivo)

    doc = SimpleDocTemplate(caminho_pdf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1a1a2e'), spaceAfter=8)
    texto_style = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.HexColor('#333333'))

    story.append(Paragraph("🛡️ VANGUARDSEC AI — LAUDO TURBO EFICIENTE", titulo_style))
    story.append(Paragraph(f"<b>Data/Hora:</b> {dados.get('timestamp')} | <b>IP:</b> {dados.get('ip_origem')}", texto_style))
    story.append(Spacer(1, 10))

    tabela_data = [
        [Paragraph("<b>Severidade</b>", texto_style), Paragraph(str(dados.get('severidade')), texto_style)],
        [Paragraph("<b>Ação SOAR</b>", texto_style), Paragraph(str(dados.get('acao_soar_gerada')), texto_style)],
        [Paragraph("<b>Parecer IA</b>", texto_style), Paragraph(str(dados.get('parecer_soc')), texto_style)],
    ]
    t = Table(tabela_data, colWidths=[130, 370])
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9ecef')), ('PADDING', (0,0), (-1,-1), 5)]))
    story.append(t)

    try:
        doc.build(story)
        return caminho_pdf
    except Exception as e:
        return str(e)


def executar_ciclo_varredura() -> None:
    global _ULTIMO_HASH_LOG
    timestamp_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Coleta de log enxuta
    evento = coletar_logs_multi_servico()
    log_raw = evento.get("log_raw", "")

    # Se não for ataque ou for log repetido, economiza processamento (Idle Mode)
    hash_atual = hashlib.md5(log_raw.encode('utf-8')).hexdigest()
    if hash_atual == _ULTIMO_HASH_LOG or not evento.get("is_ataque"):
        return
    _ULTIMO_HASH_LOG = hash_atual

    print(f"\n⚡ [ALERTA] Ameaça identificada: {log_raw[:70]}...")
    ip_atacante = evento.get("ip", SSH_HOST)
    info_geo = consultar_geoip(ip_atacante)
    trecho_normativo = consultar_pasta_politicas()

    # Execução Paralela da Esteira de IA (Threads Simultâneas para alta velocidade)
    print("⚡ Acionando Esteira Multi-Tier em paralelo...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        f1 = executor.submit(consultar_agente_ia_rapido, os.path.join(PASTA_PROMPTS, "tier1_soc.json"), log_raw)
        f2 = executor.submit(consultar_agente_ia_rapido, os.path.join(PASTA_PROMPTS, "tier2_compliance.json"), log_raw, trecho_normativo)
        f3 = executor.submit(consultar_agente_ia_rapido, os.path.join(PASTA_PROMPTS, "tier3_soar.json"), log_raw, ip_atacante)

        res_t1 = f1.result()
        res_t2 = f2.result()
        res_t3 = f3.result()

    severidade = str(res_t1.get("severidade", "ALTO"))
    parecer_ia = str(res_t1.get("parecer", "Análise de segurança executada."))
    artigo_lgpd = str(res_t2.get("artigo_lgpd", "Artigo 46 LGPD"))
    controle_iso = str(res_t2.get("controle_iso", "ISO 27001"))
    comando_bash = str(res_t3.get("comando_bash", f"sudo ufw deny from {ip_atacante}"))

    # Mitigação SOAR
    resultado_soar = "Monitorado"
    if severidade in ["ALTO", "CRITICO"] and AUTO_REMEDIATION:
        res_kill = derrubar_sessao_ssh_ativa(ip_atacante)
        res_ufw = aplicar_bloqueio_ufw_temporal(ip_atacante)
        resultado_soar = f"{res_kill} | {res_ufw}"
        print(f"🛡️ {resultado_soar}")

    dados_consolidados = {
        "timestamp": timestamp_atual,
        "severidade": severidade,
        "tipo_evento": evento.get("tipo"),
        "status_sistema": "ALERTA",
        "ip_origem": ip_atacante,
        "parecer_soc": parecer_ia,
        "compliance_lgpd": f"{artigo_lgpd} / {controle_iso}",
        "acao_soar_gerada": resultado_soar,
        "analise_trafego": f"Provedor: {info_geo.get('provedor')}",
        "modelo_ia_utilizado": MODELO_OLLAMA,
        "relatorio_normativo": f"Parecer: {parecer_ia} | Ação: {comando_bash}",
        "log_raw": log_raw,
        "origem": evento.get("origem")
    }

    # Persistência e PDF assíncrono
    inicializar_banco()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO scans (timestamp, severidade, tipo_evento, status_sistema, ip_origem, parecer_soc, compliance_lgpd, acao_soar_gerada, log_raw, origem)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp_atual, severidade, evento.get("tipo"), "ALERTA", ip_atacante,
        parecer_ia, dados_consolidados["compliance_lgpd"], resultado_soar, log_raw, evento.get("origem")
    ))
    conn.commit()
    conn.close()

    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM scans ORDER BY id DESC", conn)
        conn.close()
        df.to_csv(ARQUIVO_EXPORTACAO_POWERBI, index=False, encoding='utf-8-sig')
    except Exception:
        pass

    if GERAR_PDF:
        caminho_pdf = gerar_relatorio_pdf(dados_consolidados, info_geo)
        print(f"📄 Laudo PDF gerado: {caminho_pdf}")

    print("✓ Ciclo de segurança concluído com alta eficiência.\n")


if __name__ == "__main__":
    INTERVALO_SEGUNDOS = 3  # Polling mais rápido e fluido

    print("=========================================================")
    print("⚡ VANGUARDSEC AI — MOTOR CAPADO & ALTA EFICIÊNCIA (TURBO)")
    print(f"[*] Alvo: {SSH_HOST}:{SSH_PORT} | Intervalo: {INTERVALO_SEGUNDOS}s")
    print("=========================================================\n")

    while True:
        try:
            executar_ciclo_varredura()
        except KeyboardInterrupt:
            print("\n🛑 Motor encerrado pelo operador.")
            break
        except Exception as e:
            print(f"[!] Erro no loop: {e}")

        time.sleep(INTERVALO_SEGUNDOS)