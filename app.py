import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import re
import time
import asyncio
from datetime import datetime

from modulos.coletor_ssh import coletar_dados_servidor
from modulos.coletor_winrm import coletar_dados_windows
from modulos.gerador_pdf import gerar_relatorio_pdf
from modulos.notificador import enviar_alerta_webhook
from modulos.politicas import obter_politica_ativa
from modulos.chatops_bot import enviar_alerta_incidente

from agentes.agente_auditor import executar_agente_auditor
from agentes.agente_compliance import executar_agente_compliance
from agentes.agente_remediacao import executar_agente_remediacao

import paramiko

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="VanguardSec AI — Executive SOC", page_icon="🛡️", layout="wide")

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
        letter-spacing: 0.5px;
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
        transition: all 0.2s ease;
    }
    .stButton>button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.6);
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

HISTORICO_FILE = "historico_scans.json"

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
    return {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "host": "192.168.1.100 (Servidor Clientes)",
        "so": "Ubuntu Linux",
        "metricas": {"logins_falhos": "142", "conexoes_estab": "18", "portas_abertas": "5", "sessoes_ativas": "2"},
        "auditoria": (
            "### 🚨 Diagnóstico de Incidentes\n\n"
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
st.sidebar.caption("Executive Security Command Center")

modo_demo = st.sidebar.toggle("🎭 Modo Apresentação (Demo)", value=False)

with st.sidebar.expander("🖥️ Configuração do Ativo", expanded=not modo_demo):
    if modo_demo:
        st.info("💡 Ambiente de demonstração ativo.")
        so_alvo = "Ubuntu Linux"
        ssh_host = "192.168.1.100 (Demo)"
        ssh_user = "servidor_demo"
        ssh_pass = None
        ssh_key = None
    else:
        so_alvo = st.selectbox("Plataforma", ["Ubuntu Linux", "Windows Server"])
        ssh_host = st.text_input("IP / Host", "192.168.15.2")
        ssh_user = st.text_input("Usuário", "servidor" if so_alvo == "Ubuntu Linux" else "Administrator")

        ssh_pass = None
        ssh_key = None

        if so_alvo == "Ubuntu Linux":
            tipo_auth = st.radio("Autenticação", ["Senha", "Chave (.pem)"])
            if tipo_auth == "Senha":
                ssh_pass = st.text_input("Senha", type="password")
            else:
                ssh_key = st.text_input("Caminho .pem")
        else:
            ssh_pass = st.text_input("Senha Admin", type="password")

with st.sidebar.expander("💬 Notificações Telegram", expanded=False):
    telegram_token = st.text_input("Bot Token", value=os.getenv("TELEGRAM_BOT_TOKEN", ""), type="password")
    telegram_chat_id = st.text_input("Chat ID", value=os.getenv("TELEGRAM_ALLOWED_USER_ID", "8457053029"))

with st.sidebar.expander("🔄 Proteção Automática 24/7", expanded=False):
    modo_autonomo = st.checkbox("Ativar Automação", value=False)
    intervalo_scan = st.slider("Intervalo (segundos)", min_value=15, max_value=300, value=30)

st.sidebar.divider()
btn_executar = st.sidebar.button("⚡ AUDITAR AGORA", use_container_width=True, type="primary")

st.sidebar.caption("👨‍💻 **Desenvolvido por:** [David Nonato](https://github.com/DavidNonato23)")

# --- EXECUÇÃO DE VARREDURA ---
def rodar_varredura_completa():
    if modo_demo:
        scan_data = obter_dados_simulacao()
    else:
        with st.status("🔍 Avaliando segurança do ambiente...", expanded=True) as status:
            st.write("📡 Coletando telemetria do servidor...")
            if so_alvo == "Ubuntu Linux":
                dados_servidor = coletar_dados_servidor(ssh_host, ssh_user, password=ssh_pass, key_filename=ssh_key)
            else:
                dados_servidor = coletar_dados_windows(ssh_host, ssh_user, ssh_pass)

            if "Erro ao conectar" in dados_servidor or "timed out" in dados_servidor:
                status.update(label="❌ Falha no acesso ao servidor", state="error")
                st.error(f"Erro: {dados_servidor}")
                return False

            m_soc = extrair_metricas_soc(dados_servidor)
            politica_norma = obter_politica_ativa()
            
            st.write("🧠 Inteligência Artificial analisando vulnerabilidades...")
            auditoria = executar_agente_auditor(dados_servidor, so_alvo=so_alvo)

            st.write("⚖️ Mapeando riscos de conformidade (LGPD/ISO)...")
            compliance = executar_agente_compliance(politica_norma, auditoria)
            remediacao = executar_agente_remediacao(auditoria, compliance, so_alvo=so_alvo)

            status.update(label="✅ Análise concluída!", state="complete", expanded=False)

        scan_data = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "host": ssh_host,
            "so": so_alvo,
            "metricas": m_soc,
            "auditoria": auditoria,
            "compliance": compliance,
            "remediacao": remediacao
        }

    try:
        caminho_pdf = gerar_relatorio_pdf(scan_data)
        scan_data["caminho_pdf"] = caminho_pdf
    except Exception as e:
        st.warning(f"Aviso ao gerar PDF: {e}")

    salvar_historico(scan_data)
    st.session_state["ultimo_scan"] = scan_data

    # Telegram Alerta
    texto_auditoria = scan_data["auditoria"].lower()
    eh_critico = any(termo in texto_auditoria for termo in ["ataque", "força bruta", "failed", "falha", "crítico", "critico", "vulnerabilidade"])

    if eh_critico and telegram_token and telegram_chat_id:
        try:
            match_ip = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", scan_data["auditoria"])
            ip_detectado = match_ip.group(0) if match_ip else "IP Desconhecido"

            asyncio.run(
                enviar_alerta_incidente(
                    bot_token=telegram_token,
                    chat_id=telegram_chat_id,
                    servidor=scan_data["host"],
                    ip_atacante=ip_detectado,
                    tipo_ataque="Tentativa de Acesso Invasivo"
                )
            )
            st.toast("🚨 Alerta enviado para o Telegram!", icon="🔔")
        except Exception:
            pass

    return True

if btn_executar:
    rodar_varredura_completa()

# CARREGAR HISTÓRICO
historico = carregar_historico()

if historico:
    ultimo_registro = historico[-1]
    m_raw = ultimo_registro.get("metricas", {})
    metricas_atuais = {
        "logins_falhos": m_raw.get("logins_falhos", "0"),
        "conexoes_estab": m_raw.get("conexoes_estab", "0"),
        "portas_abertas": m_raw.get("portas_abertas", "0"),
        "sessoes_ativas": m_raw.get("sessoes_ativas", "0")
    }
    alvo_atual = f"{ultimo_registro.get('host', 'N/A')}"
    st.session_state["ultimo_scan"] = ultimo_registro
else:
    metricas_atuais = {"logins_falhos": "0", "conexoes_estab": "0", "portas_abertas": "0", "sessoes_ativas": "0"}
    alvo_atual = "Aguardando Auditoria"

# --- CABEÇALHO DO DASHBOARD ---
st.title("🛡️ Central Executiva de Segurança Cibernética")
st.caption("Visão Consolidada de Proteção de Dados, Diagnóstico por IA e Resposta Automática")

if modo_demo:
    st.warning("⚠️ **MODO DE DEMONSTRAÇÃO COMERCIAL:** Dados simulados para apresentação.")

# KPIS SUPERIORES
c1, c2, c3, c4 = st.columns(4)

total_falhas = int(metricas_atuais['logins_falhos'])
c1.metric("Ameaças Bloqueadas", f"{total_falhas}", delta="Tentativas Invasivas", delta_color="inverse")
c2.metric("Conexões Ativas", f"{metricas_atuais['conexoes_estab']}", delta="Sessões de Rede")
c3.metric("Portas Expostas", f"{metricas_atuais['portas_abertas']}", delta="Superfície de Acesso")
c4.metric("Ativo Monitorado", alvo_atual, delta="Servidor Atual")

st.divider()

# ABAS
tab1, tab2, tab3 = st.tabs([
    "📋 Visão Geral Executiva (Cliente)", 
    "🛠️ Painel Técnico & Scripts (TI)",
    "📈 Histórico & Relatórios PDF"
])

with tab1:
    if "ultimo_scan" in st.session_state:
        scan = st.session_state["ultimo_scan"]

        # CARD MACRO DE STATUS
        tem_ataque = int(scan.get("metricas", {}).get("logins_falhos", 0)) > 0 or "crítico" in scan["auditoria"].lower() or "não conforme" in scan["compliance"].lower()
        
        if tem_ataque:
            st.markdown("""
            <div class="card-status-alert">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin:0; color:#FCA5A5; font-size: 1.3rem;">🚨 Status: Ação de Bloqueio Recomendada</h3>
                    <span class="badge-critical">AÇÃO NECESSÁRIA</span>
                </div>
                <p style="margin:8px 0 0 0; color:#FECACA; font-size:10.5pt;">A Inteligência Artificial identificou tentativas de invasão no servidor. A regra de bloqueio do IP invasor está pronta para aplicação abaixo.</p>
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
            st.markdown("#### 🔍 Diagnóstico do Incidente")
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
            caminho_pdf = scan.get("caminho_pdf") or gerar_relatorio_pdf(scan)
            if os.path.exists(caminho_pdf):
                with open(caminho_pdf, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Baixar Relatório Executivo (PDF)",
                        data=pdf_file,
                        file_name=os.path.basename(caminho_pdf),
                        mime="application/pdf",
                        use_container_width=True
                    )
    else:
        st.info("💡 Clique no botão **⚡ AUDITAR AGORA** na barra lateral para realizar a primeira varredura.")

with tab2:
    st.subheader("💻 Painel Técnico para Equipe de TI")
    if "ultimo_scan" in st.session_state:
        scan = st.session_state["ultimo_scan"]
        st.markdown("**Playbook SOAR de Contenção (Bash / PowerShell):**")
        script_limpo = scan["remediacao"].replace("```bash", "").replace("```powershell", "").replace("```", "").strip()
        st.code(script_limpo, language="bash" if scan["so"] == "Ubuntu Linux" else "powershell")
        
        st.divider()
        st.markdown("**Evento Formato SIEM (CEF):**")
        cef_log = f"CEF:0|VanguardSec|SOC|1.0|100|Security Scan Completed|5|src={scan['host']} msg=Scan Successful"
        st.code(cef_log, language="text")

with tab3:
    st.subheader("📈 Histórico Consolidado de Auditorias")
    if historico:
        df_hist = pd.DataFrame(historico)
        st.dataframe(df_hist[["data", "host", "so"]], use_container_width=True)
    else:
        st.info("Nenhum histórico registrado até o momento.")

if modo_autonomo:
    @st.fragment(run_every=intervalo_scan)
    def automacao_continua():
        agora = time.time()
        ultimo_tempo = st.session_state.get("ultimo_tempo_scan", 0)
        
        if agora - ultimo_tempo >= intervalo_scan:
            st.session_state["ultimo_tempo_scan"] = agora
            rodar_varredura_completa()

    automacao_continua()