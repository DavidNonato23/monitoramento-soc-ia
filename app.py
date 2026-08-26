import streamlit as st
import pandas as pd
import json
import os
import re
import time
import socket
import paramiko
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from modulos.coletor_ssh import coletar_dados_servidor
from modulos.coletor_winrm import coletar_dados_windows
from modulos.gerador_pdf import gerar_relatorio_pdf
from modulos.notificador import enviar_notificacao
from modulos.politicas import obter_politica_ativa

from agentes.agente_auditor import executar_agente_auditor
from agentes.agente_compliance import executar_agente_compliance
from agentes.agente_remediacao import executar_agente_remediacao

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="VanguardSec AI — Executive Live SOC", page_icon="🛡️", layout="wide")

# --- ESTILIZAÇÃO CSS EXECUTIVE GLASSMORPHISM ---
st.markdown("""
<style>
    .stApp {
        background-color: #0A0E17;
        color: #E2E8F0;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    div[data-testid="stMetric"] {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: rgba(59, 130, 246, 0.5);
    }

    .card-status-alert {
        background: linear-gradient(135deg, rgba(127, 29, 29, 0.4) 0%, rgba(153, 27, 27, 0.2) 100%);
        border: 1px solid #EF4444;
        border-radius: 14px;
        padding: 20px 24px;
        box-shadow: 0 0 25px rgba(239, 68, 68, 0.15);
        margin-bottom: 24px;
    }

    .card-status-ok {
        background: linear-gradient(135deg, rgba(6, 78, 59, 0.4) 0%, rgba(6, 95, 70, 0.2) 100%);
        border: 1px solid #10B981;
        border-radius: 14px;
        padding: 20px 24px;
        box-shadow: 0 0 25px rgba(16, 185, 129, 0.15);
        margin-bottom: 24px;
    }

    .badge-critical {
        background-color: #EF4444;
        color: #FFFFFF;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-success {
        background-color: #10B981;
        color: #FFFFFF;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.8rem;
    }

    .stButton>button[kind="primary"] {
        background: linear-gradient(90deg, #2563EB 0%, #1D4ED8 100%);
        border: none;
        border-radius: 10px;
        font-weight: 600;
        height: 48px;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    }
</style>
""", unsafe_allow_html=True)

HISTORICO_FILE = "historico_scans.json"

# --- FUNÇÕES AUXILIARES DE CONEXÃO & REMOTA ---
def checar_status_servidor(host, port=22):
    if not host or host.strip() == "":
        return False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.5)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def coletar_telemetria_remota(hostname, username, password, key_file):
    metrics = {"cpu": 0.0, "ram": 0.0, "disk": 0.0}
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if key_file:
            client.connect(hostname=hostname, username=username, key_filename=key_file, timeout=5)
        else:
            client.connect(hostname=hostname, username=username, password=password, timeout=5)

        _, stdout, _ = client.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        cpu_val = stdout.read().decode().strip()
        metrics["cpu"] = float(cpu_val) if cpu_val else 0.0

        _, stdout, _ = client.exec_command("free | awk '/Mem:/ {print $3/$2 * 100.0}'")
        ram_val = stdout.read().decode().strip()
        metrics["ram"] = round(float(ram_val), 1) if ram_val else 0.0

        _, stdout, _ = client.exec_command("df / | tail -1 | awk '{print $5}' | sed 's/%//'")
        disk_val = stdout.read().decode().strip()
        metrics["disk"] = float(disk_val) if disk_val else 0.0

        client.close()
    except Exception:
        pass
    return metrics

def coletar_inventario_remoto(hostname, username, password, key_file):
    inventario = {}
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if key_file:
            client.connect(hostname=hostname, username=username, key_filename=key_file, timeout=5)
        else:
            client.connect(hostname=hostname, username=username, password=password, timeout=5)

        cmds = {
            "Hostname": "hostname",
            "Kernel": "uname -r",
            "Sistema Operacional": "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'",
            "Uptime": "uptime -p",
            "Processador (Modelo)": "lscpu | grep 'Model name' | cut -d: -f2 | sed 's/^[ \t]*//'",
            "Cores do CPU": "nproc",
            "Memória Total": "free -h | awk '/Mem:/ {print $2}'",
            "Espaço em Disco Total": "df -h / | tail -1 | awk '{print $2}'",
            "Endereço IP Local": "hostname -I | awk '{print $1}'"
        }

        for chave, cmd in cmds.items():
            _, stdout, _ = client.exec_command(cmd)
            inventario[chave] = stdout.read().decode().strip()

        client.close()
    except Exception as e:
        inventario["Erro"] = f"Falha na coleta: {str(e)}"
    return inventario

def salvar_historico(dados):
    historico = []
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            try:
                historico = json.load(f)
            except Exception:
                historico = []
    historico.append(dados)
    with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=4)

def carregar_historico():
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def extrair_metricas_soc(dados_brutos):
    metrics = {"logins_falhos": "0", "conexoes_estab": "0", "portas_abertas": "0", "sessoes_ativas": "0"}
    
    if "--- [ Total de Logins Falhos ] ---" in dados_brutos:
        bloco_failed = dados_brutos.split("--- [ Total de Logins Falhos ] ---")[1].split("---")[0].strip()
        match = re.search(r"\d+", bloco_failed)
        if match:
            metrics["logins_falhos"] = match.group(0)

    if "--- [ Conexões Estabelecidas ] ---" in dados_brutos:
        bloco_estab = dados_brutos.split("--- [ Conexões Estabelecidas ] ---")[1].split("---")[0].strip()
        linhas = [l for l in bloco_estab.split("\n") if "estab" in l.lower() or "tcp" in l.lower()]
        metrics["conexoes_estab"] = str(len(linhas))

    if "--- [ Portas Abertas / Listening ] ---" in dados_brutos:
        bloco_conn = dados_brutos.split("--- [ Portas Abertas / Listening ] ---")[1].split("---")[0].strip()
        linhas_listen = [l for l in bloco_conn.split("\n") if "listen" in l.lower()]
        metrics["portas_abertas"] = str(len(linhas_listen))

    if "--- [ Sessões SSH / Usuários Ativos ] ---" in dados_brutos:
        bloco_users = dados_brutos.split("--- [ Sessões SSH / Usuários Ativos ] ---")[1].split("---")[0].strip()
        linhas_u = [l for l in bloco_users.split("\n") if l.strip()]
        metrics["sessoes_ativas"] = str(len(linhas_u))

    return metrics

def aplicar_remediacao_linux(hostname, username, password, key_file, script):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if key_file:
            client.connect(hostname=hostname, username=username, key_filename=key_file, timeout=10)
        else:
            client.connect(hostname=hostname, username=username, password=password, timeout=10)

        linhas = [c.strip() for c in script.split('\n') if c.strip() and not c.strip().startswith('#')]
        logs = []
        for cmd in linhas:
            stdin, stdout, stderr = client.exec_command(cmd)
            out = stdout.read().decode('utf-8').strip()
            err = stderr.read().decode('utf-8').strip()
            logs.append(f"$ {cmd}\nStatus: {out if out else err}")
        client.close()
        return True, "\n".join(logs)
    except Exception as e:
        return False, str(e)

def obter_dados_simulacao():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "data": now_str,
        "host": "192.168.1.100 (Servidor Clientes)",
        "so": "Ubuntu Linux",
        "metricas": {"logins_falhos": "142", "conexoes_estab": "18", "portas_abertas": "5", "sessoes_ativas": "2"},
        "auditoria": (
            f"### 🚨 Diagnóstico de Incidentes ({now_str})\n\n"
            "* **Tentativa de Invasão Identificada:** Um endereço externo (`185.220.101.5`) realizou **142 tentativas de adivinhar senhas** no servidor.\n"
            "* **Exposição de Porta:** O serviço de banco de dados está exposto publicamente sem proteção de firewall."
        ),
        "compliance": (
            "### ⚖️ Impacto e LGPD\n\n"
            "* **Nível de Risco:** <span class='badge-critical'>CRÍTICO</span>\n"
            "* **Privacidade de Dados:** A ausência de bloqueio imediato viola o **Art. 46 da LGPD**, expondo dados de clientes a riscos de vazamento."
        ),
        "remediacao": (
            "#!/bin/bash\n"
            "sudo ufw deny from 185.220.101.5 to any\n"
            "sudo ufw limit ssh/tcp\n"
            "sudo ufw reload"
        )
    }

# --- BARRA LATERAL ---
st.sidebar.title("🛡️ VanguardSec AI")
st.sidebar.caption("Executive Security Command Center & Live SOC")

modo_demo = st.sidebar.toggle("🎭 Modo Apresentação (Demo)", value=False)

with st.sidebar.expander("🖥️ Configuração do Ativo", expanded=True):
    if modo_demo:
        st.info("💡 Ambiente de demonstração ativo.")
        so_alvo = "Ubuntu Linux"
        ssh_host = "192.168.1.100"
        ssh_user = "servidor_demo"
        ssh_pass = None
        ssh_key = None
    else:
        so_alvo = st.selectbox("Plataforma", ["Ubuntu Linux", "Windows Server"])
        ssh_host = st.text_input("IP / Host", value="", placeholder="Ex: 192.168.15.8")
        ssh_user = st.text_input("Usuário", value="" if so_alvo == "Ubuntu Linux" else "Administrator", placeholder="Ex: servidor")

        ssh_pass = None
        ssh_key = None

        if so_alvo == "Ubuntu Linux":
            tipo_auth = st.radio("Autenticação", ["Senha", "Chave (.pem)"])
            if tipo_auth == "Senha":
                ssh_pass = st.text_input("Senha", value="", type="password")
            else:
                ssh_key = st.text_input("Caminho .pem", value="", placeholder="/caminho/chave.pem")
        else:
            ssh_pass = st.text_input("Senha Admin", type="password")

target_ip = "192.168.1.100" if modo_demo else ssh_host
status_servidor_online = True if modo_demo else checar_status_servidor(target_ip)

if modo_demo or (target_ip and status_servidor_online):
    st.sidebar.success(f"🟢 Servidor ONLINE ({target_ip})")
elif target_ip:
    st.sidebar.error(f"🔴 Servidor OFFLINE ({target_ip})")
else:
    st.sidebar.warning("⚠️ Insira o IP do Servidor")

with st.sidebar.expander("💬 Notificações Telegram", expanded=False):
    telegram_token = st.text_input("Bot Token", value=os.getenv("TELEGRAM_BOT_TOKEN", ""), type="password")
    telegram_chat_id = st.text_input("Chat ID", value=os.getenv("TELEGRAM_ALLOWED_USER_ID", "8457053029"))

with st.sidebar.expander("🔄 Proteção Automática 24/7", expanded=True):
    modo_autonomo = st.checkbox("Ativar Varredura Automática (30s)", value=False)
    intervalo_scan = 30 

st.sidebar.divider()
btn_executar = st.sidebar.button("⚡ AUDITAR AGORA", use_container_width=True, type="primary")

st.sidebar.caption("👨‍💻 **Desenvolvido por:** [David Nonato](https://github.com/DavidNonato23)")

# --- EXECUÇÃO ATÔMICA DA VARREDURA COM GERAÇÃO GARANTIDA DE PDF ---
def rodar_varredura_completa():
    if not modo_demo and not ssh_host:
        st.error("❌ Preencha o IP do Servidor na barra lateral antes de auditar.")
        return False

    if "ultimo_scan" in st.session_state:
        del st.session_state["ultimo_scan"]

    if modo_demo:
        scan_data = obter_dados_simulacao()
    else:
        status_box = st.status("🔍 Realizando nova varredura completa...", expanded=True)
        with status_box:
            st.write("📡 Coletando dados em tempo real do servidor...")
            if so_alvo == "Ubuntu Linux":
                dados_servidor = coletar_dados_servidor(ssh_host, ssh_user, password=ssh_pass, key_filename=ssh_key)
            else:
                dados_servidor = coletar_dados_windows(ssh_host, ssh_user, ssh_pass)

            if "Erro ao conectar" in dados_servidor or "timed out" in dados_servidor:
                status_box.update(label="❌ Falha no acesso ao servidor", state="error")
                st.error(f"Erro de Conexão: {dados_servidor}")
                return False

            m_soc = extrair_metricas_soc(dados_servidor)
            politica_norma = obter_politica_ativa()
            
            st.write("🧠 IA VanguardSec analisando novas vulnerabilidades no Ollama...")
            try:
                auditoria = executar_agente_auditor(dados_servidor, so_alvo=so_alvo)
            except Exception as e_aud:
                auditoria = f"⚠️ Erro ao processar o Agente Auditor: {str(e_aud)}"

            st.write("⚖️ Mapeando riscos de conformidade (LGPD/ISO)...")
            try:
                compliance = executar_agente_compliance(politica_norma, auditoria)
            except Exception as e_comp:
                compliance = f"⚠️ Erro ao processar Compliance: {str(e_comp)}"

            try:
                remediacao = executar_agente_remediacao(auditoria, compliance, so_alvo=so_alvo)
            except Exception as e_rem:
                remediacao = "sudo ufw status"

            status_box.update(label="✅ Análise concluída! Compilando relatório PDF...", state="running")

        scan_data = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "host": ssh_host,
            "so": so_alvo,
            "metricas": m_soc,
            "auditoria": auditoria,
            "compliance": compliance,
            "remediacao": remediacao
        }

    # GERAÇÃO DO PDF EXPLICITA
    try:
        caminho_pdf = gerar_relatorio_pdf(scan_data)
        scan_data["caminho_pdf"] = caminho_pdf
        st.toast(f"📄 Relatório PDF gerado com sucesso!", icon="✅")
    except Exception as e:
        st.error(f"Erro na criação do PDF: {e}")

    salvar_historico(scan_data)
    st.session_state["ultimo_scan"] = scan_data

    # Alerta Telegram
    texto_auditoria = scan_data["auditoria"].lower()
    eh_critico = any(termo in texto_auditoria for termo in ["ataque", "força bruta", "failed", "falha", "crítico", "critico", "vulnerabilidade"])

    if eh_critico and telegram_token and telegram_chat_id:
        try:
            match_ip = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", scan_data["auditoria"])
            ip_detectado = match_ip.group(0) if match_ip else "IP Desconhecido"

            mensagem = (
                f"🚨 *NOVO ALERTA DE INCIDENTE DETECTADO*\n\n"
                f"*Data:* `{scan_data['data']}`\n"
                f"*Servidor:* `{scan_data['host']}`\n"
                f"*Ameaça:* Tentativa de Acesso Invasivo\n"
                f"*IP Atacante:* `{ip_detectado}`"
            )

            enviar_notificacao(
                mensagem=mensagem,
                token=telegram_token,
                chat_id=telegram_chat_id
            )
            st.toast("🚨 Novo alerta enviado para o Telegram!", icon="🔔")
        except Exception:
            pass

    return True

if btn_executar:
    rodar_varredura_completa()

# --- AUTOMAÇÃO 24/7 ---
if modo_autonomo and target_ip:
    st_autorefresh(interval=30000, key="soc_autonomo_30s")
    agora = time.time()
    ultimo_tempo = st.session_state.get("ultimo_tempo_scan", 0)
    if agora - ultimo_tempo >= 30:
        st.session_state["ultimo_tempo_scan"] = agora
        rodar_varredura_completa()

# HISTÓRICO E METRICAS
historico = carregar_historico()

if target_ip and "ultimo_scan" in st.session_state:
    scan_atual = st.session_state["ultimo_scan"]
    m_raw = scan_atual.get("metricas", {})
    metricas_atuais = {
        "logins_falhos": m_raw.get("logins_falhos", "0"),
        "conexoes_estab": m_raw.get("conexoes_estab", "0"),
        "portas_abertas": m_raw.get("portas_abertas", "0"),
        "sessoes_ativas": m_raw.get("sessoes_ativas", "0")
    }
else:
    metricas_atuais = {"logins_falhos": "0", "conexoes_estab": "0", "portas_abertas": "0", "sessoes_ativas": "0"}

# --- CABEÇALHO DO DASHBOARD ---
st.title("🛡️ Central Executiva de Segurança Cibernética (Live SOC)")
st.caption(f"Visão Consolidada de Proteção de Dados, Diagnóstico por IA e Resposta Automática — Sinal: {datetime.now().strftime('%H:%M:%S')}")

if modo_demo:
    st.warning("⚠️ **MODO DE DEMONSTRAÇÃO COMERCIAL:** Dados simulados para apresentação.")

# BANNER DINÂMICO DE STATUS
if not target_ip:
    st.info("💡 **Nenhum Servidor Configurado:** Preencha o IP e credenciais na barra lateral para iniciar o monitoramento.")
elif not status_servidor_online:
    st.error(f"🚨 **ALERTA CRÍTICO: SERVIDOR INDISPONÍVEL / FORA DO AR ({target_ip})**\n\nA porta de controle SSH (22) não respondeu. O servidor virtual/físico está desligado ou perdeu a comunicação com a rede.")
else:
    st.success(f"🟢 **SISTEMA OPERACIONAL & MONITORADO** — Ativo `{target_ip}` conectado com sucesso. Escudos de proteção e telemetria ativas.")

# KPIS SUPERIORES
c1, c2, c3, c4 = st.columns(4)

if target_ip:
    status_label = "ONLINE" if status_servidor_online else "OFFLINE"
    status_delta = "SSH Ativo" if status_servidor_online else "Queda Detectada"
else:
    status_label = "AGUARDANDO"
    status_delta = "Sem Alvo"

c1.metric("Status do Ativo", status_label, delta=status_delta, delta_color="normal" if status_servidor_online and target_ip else "inverse")
c2.metric("Conexões Ativas (Rede)", f"{metricas_atuais['conexoes_estab']}", delta="Sessões do Servidor" if target_ip else "Aguardando IP")
c3.metric("Portas Expostas", f"{metricas_atuais['portas_abertas']}", delta="Superfície de Acesso" if target_ip else "Aguardando IP")
c4.metric("Logins Falhos (24h)", f"{metricas_atuais['logins_falhos']}", delta="Tentativas Invasivas" if target_ip else "Aguardando IP", delta_color="inverse")

st.divider()

# ABAS DO DASHBOARD
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Visão Geral Executiva (Cliente)", 
    "📊 Telemetria do Servidor Remoto",
    "🛠️ Painel Técnico & Scripts (TI)",
    "📈 Histórico & Relatórios PDF"
])

with tab1:
    if target_ip and "ultimo_scan" in st.session_state:
        scan = st.session_state["ultimo_scan"]

        tem_ataque = int(scan.get("metricas", {}).get("logins_falhos", 0)) > 0 or "crítico" in scan["auditoria"].lower() or "não conforme" in scan["compliance"].lower()
        
        if tem_ataque and status_servidor_online:
            st.markdown("""
            <div class="card-status-alert">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin:0; color:#FCA5A5; font-size: 1.3rem;">🚨 Status: Ação de Bloqueio Recomendada</h3>
                    <span class="badge-critical">AÇÃO NECESSÁRIA</span>
                </div>
                <p style="margin:8px 0 0 0; color:#FECACA; font-size:10.5pt;">A Inteligência Artificial identificou tentativas de invasão no servidor. A regra de bloqueio do IP invasor está pronta para aplicação abaixo.</p>
            </div>
            """, unsafe_allow_html=True)
        elif not status_servidor_online:
            st.markdown("""
            <div class="card-status-alert">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin:0; color:#FCA5A5; font-size: 1.3rem;">🔴 Status: Servidor Desligado ou Inacessível</h3>
                    <span class="badge-critical">OFFLINE</span>
                </div>
                <p style="margin:8px 0 0 0; color:#FECACA; font-size:10.5pt;">A máquina monitorada não respondeu à tentativa de comunicação na porta 22.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card-status-ok">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin:0; color:#6EE7B7; font-size: 1.3rem;">🟢 Status: Ambiente Seguro e Operacional</h3>
                    <span class="badge-success">PROTEGIDO</span>
                </div>
                <p style="margin:8px 0 0 0; color:#A7F3D0; font-size:10.5pt;">Nenhuma anomalia crítica ou atividade invasiva identificada nas últimas auditorias.</p>
            </div>
            """, unsafe_allow_html=True)

        col_ex1, col_ex2 = st.columns(2)

        with col_ex1:
            st.markdown(f"#### 🔍 Diagnóstico do Incidente (`{scan['data']}`)")
            with st.container(border=True):
                st.markdown(scan["auditoria"], unsafe_allow_html=True)

        with col_ex2:
            st.markdown("#### ⚖️ Riscos & LGPD")
            with st.container(border=True):
                st.markdown(scan["compliance"], unsafe_allow_html=True)

        st.divider()

        st.markdown("#### 🛡️ Resposta Automática a Ameaças")
        st.write("Clique abaixo para acionar o escudo inteligente e isolar o IP atacante do servidor:")
        
        col_b1, col_b2 = st.columns([2, 1])
        with col_b1:
            if st.button("🔥 APLICAR PROTEÇÃO E BLOQUEAR INVASOR", type="primary", use_container_width=True):
                with st.spinner("Aplicando regras de segurança no firewall..."):
                    if modo_demo:
                        st.success("✅ Servidor protegido com sucesso no modo de demonstração!")
                    else:
                        script_limpo = scan["remediacao"].replace("```bash", "").replace("```powershell", "").replace("```", "").strip()
                        sucesso, logs = aplicar_remediacao_linux(scan["host"], ssh_user, ssh_pass, ssh_key, script_limpo)
                        if sucesso:
                            st.success("✅ O IP invasor foi bloqueado com sucesso no firewall!")
                        else:
                            st.error(f"Erro ao aplicar bloqueio: {logs}")
        with col_b2:
            # BOTÃO DE DOWNLOAD DO RELATÓRIO EXECUTIVO PDF
            caminho_pdf = scan.get("caminho_pdf")
            if not caminho_pdf or not os.path.exists(caminho_pdf):
                try:
                    caminho_pdf = gerar_relatorio_pdf(scan)
                except Exception:
                    caminho_pdf = None

            if caminho_pdf and os.path.exists(caminho_pdf):
                with open(caminho_pdf, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Baixar Relatório Executivo PDF",
                        data=pdf_file.read(),
                        file_name=os.path.basename(caminho_pdf),
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.warning("⚠️ Não foi possível gerar o PDF.")
    else:
        st.info("💡 Informe o IP do Servidor na barra lateral e clique em **⚡ AUDITAR AGORA** para iniciar a primeira varredura.")

with tab2:
    st.subheader(f"📊 Telemetria Direta do Servidor ({target_ip if target_ip else 'Nenhum Alvo'})")
    
    if target_ip and status_servidor_online:
        if modo_demo:
            hw_remoto = {"cpu": 12.5, "ram": 42.8, "disk": 35.0}
        else:
            hw_remoto = coletar_telemetria_remota(ssh_host, ssh_user, ssh_pass, ssh_key)

        col_h1, col_h2, col_h3 = st.columns(3)
        
        with col_h1:
            st.markdown("##### PROCESSADOR (CPU REMOTA)")
            st.progress(min(hw_remoto["cpu"] / 100.0, 1.0))
            st.write(f"**Uso no Servidor:** {hw_remoto['cpu']}%")

        with col_h2:
            st.markdown("##### MEMÓRIA RAM REMOTA")
            st.progress(min(hw_remoto["ram"] / 100.0, 1.0))
            st.write(f"**Uso no Servidor:** {hw_remoto['ram']}%")

        with col_h3:
            st.markdown("##### ARMAZENAMENTO EM DISCO")
            st.progress(min(hw_remoto["disk"] / 100.0, 1.0))
            st.write(f"**Uso no Servidor:** {hw_remoto['disk']}%")

        st.divider()
        
        st.subheader("📦 Inventário Completo de Ativos (Hardware & SO)")
        if st.button("🔍 GERAR INVENTÁRIO DO SERVIDOR", use_container_width=True):
            with st.spinner("Auditando componentes e especificações do servidor via SSH..."):
                if modo_demo:
                    inv = {
                        "Hostname": "srv-prod-ubuntu",
                        "Kernel": "5.15.0-101-generic",
                        "Sistema Operacional": "Ubuntu 22.04.4 LTS",
                        "Uptime": "up 14 weeks, 2 days",
                        "Processador (Modelo)": "Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz",
                        "Cores do CPU": "8",
                        "Memória Total": "16Gi",
                        "Espaço em Disco Total": "250G",
                        "Endereço IP Local": "192.168.1.100"
                    }
                else:
                    inv = coletar_inventario_remoto(ssh_host, ssh_user, ssh_pass, ssh_key)

                df_inv = pd.DataFrame(list(inv.items()), columns=["Componente", "Especificação / Detalhe"])
                st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("💡 Insira o IP do Servidor na barra lateral e certifique-se de que ele esteja ONLINE para visualizar a telemetria remota.")

with tab3:
    st.subheader("💻 Painel Técnico para Equipe de TI")
    if target_ip and "ultimo_scan" in st.session_state:
        scan = st.session_state["ultimo_scan"]
        st.markdown("**Playbook SOAR de Contenção (Bash / PowerShell):**")
        script_limpo = scan["remediacao"].replace("```bash", "").replace("```powershell", "").replace("```", "").strip()
        st.code(script_limpo, language="bash" if scan["so"] == "Ubuntu Linux" else "powershell")
        
        extensao = "sh" if scan["so"] == "Ubuntu Linux" else "ps1"
        st.download_button(
            label=f"💾 Baixar Script de Remediação (.{extensao})",
            data=script_limpo,
            file_name=f"playbook_bloqueio_{scan['host']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extensao}",
            mime="text/plain"
        )

        st.divider()
        st.markdown("**Evento Formato SIEM (CEF):**")
        cef_log = f"CEF:0|VanguardSec|SOC|1.0|100|Security Scan Completed|5|src={scan['host']} msg=Scan Successful"
        st.code(cef_log, language="text")
    else:
        st.info("💡 Realize a primeira auditoria para gerar o playbook de remediação do servidor.")

with tab4:
    st.subheader("📈 Histórico Consolidado de Auditorias e Downloads")
    if historico:
        df_hist = pd.DataFrame(historico)
        st.dataframe(df_hist[["data", "host", "so"]], use_container_width=True)
    else:
        st.info("Nenhum histórico registrado até o momento.")