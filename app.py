import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import re
import time
from datetime import datetime

from modulos.coletor_ssh import coletar_dados_servidor
from modulos.coletor_winrm import coletar_dados_windows
from modulos.gerador_pdf import gerar_relatorio_pdf
from modulos.notificador import enviar_alerta_webhook
from modulos.politicas import obter_politica_ativa

from agentes.agente_auditor import executar_agente_auditor
from agentes.agente_compliance import executar_agente_compliance
from agentes.agente_remediacao import executar_agente_remediacao

import paramiko
import winrm

st.set_page_config(page_title="VanguardSec AI — Global Command SOC", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #090D16; color: #E2E8F0; }
    .stMetric { background-color: #111827; border: 1px solid #1E293B; border-radius: 8px; padding: 12px; }
    .stSelectbox, .stTextInput { background-color: #0F172A; }
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

def extrair_metricas_remotas(dados_brutos):
    metrics = {"cpu": "N/A", "ram": "N/A", "disk": "N/A"}
    if "--- [ Uso de CPU ] ---" in dados_brutos:
        bloco_cpu = dados_brutos.split("--- [ Uso de CPU ] ---")[1].split("---")[0]
        match = re.search(r"(\d+[\.,]?\d*)", bloco_cpu)
        if match: metrics["cpu"] = f"{match.group(1)}%"

    if "--- [ Uso de RAM ] ---" in dados_brutos:
        bloco_ram = dados_brutos.split("--- [ Uso de RAM ] ---")[1].split("---")[0]
        match = re.search(r"(\d+[\.,]?\d*%)", bloco_ram)
        if match: metrics["ram"] = match.group(1)

    if "--- [ Uso de Disco ] ---" in dados_brutos:
        bloco_disk = dados_brutos.split("--- [ Uso de Disco ] ---")[1].split("---")[0]
        match = re.search(r"(\d+%)", bloco_disk)
        if match: metrics["disk"] = match.group(1)

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
            logs.append(f"<b>$ {cmd}</b><br>{out if out else err}")
        client.close()
        return True, "<br>".join(logs)
    except Exception as e:
        return False, str(e)

# --- SIDEBAR DE CENTRO DE OPERAÇÕES ---
st.sidebar.title("🛡️ VanguardSec Command")
st.sidebar.caption("SecOps Enterprise & Autonomous Threat Response")

st.sidebar.divider()
st.sidebar.subheader("🎯 Target Asset Configuration")
so_alvo = st.sidebar.selectbox("Plataforma Alvo", ["Ubuntu Linux", "Windows Server"])
ssh_host = st.sidebar.text_input("IP / Hostname Alvo", "172.30.0.168")
ssh_user = st.sidebar.text_input("Credencial / User", "servidor" if so_alvo == "Ubuntu Linux" else "Administrator")

ssh_pass = None
ssh_key = None

if so_alvo == "Ubuntu Linux":
    tipo_auth = st.sidebar.radio("Método de Acesso", ["Senha", "Chave SSH Private Key"])
    if tipo_auth == "Senha":
        ssh_pass = st.sidebar.text_input("Secret Password", type="password")
    else:
        ssh_key = st.sidebar.text_input("Caminho (.pem / id_rsa)")
else:
    ssh_pass = st.sidebar.text_input("Secret Admin Password", type="password")

st.sidebar.divider()
st.sidebar.subheader("🔄 Automação Contínua 24/7")
modo_autonomo = st.sidebar.checkbox("Ativar Monitoramento Contínuo", value=False)
intervalo_scan = st.sidebar.slider("Intervalo (segundos)", min_value=10, max_value=300, value=30)

if st.sidebar.button("🔌 Testar Acesso ao Servidor", width="stretch"):
    with st.sidebar.spinner("Testando conectividade..."):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=ssh_host, username=ssh_user, password=ssh_pass, timeout=5)
            client.close()
            st.sidebar.success("Conexão SSH OK! 🟢")
        except Exception as e:
            st.sidebar.error(f"Erro no acesso: {e}")

st.sidebar.divider()
st.sidebar.subheader("📡 SIEM Integration")
webhook_url = st.sidebar.text_input("Webhook URL (Slack/Discord/Teams)", type="password")

btn_executar = st.sidebar.button("⚡ EXECUTE SOC SCAN & HARDENING", width="stretch", type="primary")

# --- FUNÇÃO EXECUTORA DE VARREDURA ---
def rodar_varredura_completa():
    if so_alvo == "Ubuntu Linux":
        dados_servidor = coletar_dados_servidor(ssh_host, ssh_user, password=ssh_pass, key_filename=ssh_key)
    else:
        dados_servidor = coletar_dados_windows(ssh_host, ssh_user, ssh_pass)

    if "Erro ao conectar" in dados_servidor or "timed out" in dados_servidor:
        st.error(f"⚠️ Falha na coleta remota: {dados_servidor}")
        return False
    else:
        m_remotas = extrair_metricas_remotas(dados_servidor)
        politica_norma = obter_politica_ativa()
        
        auditoria = executar_agente_auditor(dados_servidor, so_alvo=so_alvo)
        compliance = executar_agente_compliance(politica_norma, auditoria)
        remediacao = executar_agente_remediacao(auditoria, compliance, so_alvo=so_alvo)

        scan_data = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "host": ssh_host,
            "so": so_alvo,
            "metricas": m_remotas,
            "auditoria": auditoria,
            "compliance": compliance,
            "remediacao": remediacao
        }

        try:
            caminho_pdf = gerar_relatorio_pdf(scan_data)
            scan_data["caminho_pdf"] = caminho_pdf
        except Exception as e:
            st.warning(f"Aviso: Não foi possível salvar PDF: {e}")

        salvar_historico(scan_data)
        st.session_state["ultimo_scan"] = scan_data

        if webhook_url.strip():
            enviar_alerta_webhook(webhook_url, ssh_host, so_alvo, compliance)
        return True

# CONTROLE DE EXECUÇÃO MANUAL
if btn_executar:
    with st.spinner("Executando varredura e consultando Agentes de IA..."):
        if rodar_varredura_completa():
            st.success("Varredura e relatório PDF gerados com sucesso!")

# LEITURA DO HISTÓRICO
historico = carregar_historico()

if historico:
    ultimo_registro = historico[-1]
    metricas_atuais = ultimo_registro.get("metricas", {"cpu": "N/A", "ram": "N/A", "disk": "N/A"})
    alvo_atual = f"{ultimo_registro.get('host', 'N/A')} ({ultimo_registro.get('so', 'N/A')})"
    st.session_state["ultimo_scan"] = ultimo_registro
else:
    metricas_atuais = {"cpu": "N/A", "ram": "N/A", "disk": "N/A"}
    alvo_atual = "Nenhum alvo consultado"

# --- CABEÇALHO GLOBAL ENTERPRISE SOC ---
st.title("🛡️ VanguardSec AI — Security Operations Center (SOC)")
st.caption("Next-Gen Autonomous Cyber Defense | Real-Time Remote Telemetry & Hardening")

# CARDS SUPERIORES DO SERVIDOR REMOTO
st.markdown("##### 🖥️ Recursos do Servidor Remoto Auditado")
r1, r2, r3, r4 = st.columns(4)

r1.metric("CPU Remota", metricas_atuais["cpu"])
r2.metric("RAM Remota", metricas_atuais["ram"])
r3.metric("Disco Remoto", metricas_atuais["disk"])
r4.metric("Ativo Selecionado", alvo_atual)

st.divider()

# CARDS DE STATUS GLOBAL DO SOC
m1, m2, m3, m4, m5, m6 = st.columns(6)

total_scans = len(historico)
ult_scan_data = historico[-1]["data"] if total_scans > 0 else "Nenhum"
ult_host = historico[-1]["host"] if total_scans > 0 else "N/A"

m1.metric("Scans Executados", total_scans)
m2.metric("Ativo Monitorado", ult_host)
m3.metric("Defesa AI", "Online", delta="smollm2:135m")
m4.metric("Engine Local", "Ativo", delta="Ollama")

score_global = 100 if total_scans > 0 else 0
if historico:
    alertas = historico[-1]["auditoria"].lower().count("vulnerabilidade") + historico[-1]["auditoria"].lower().count("erro")
    score_global = max(20, 100 - (alertas * 10))

m5.metric("Postura Global", f"{score_global}%", delta=f"{'-' if score_global < 80 else '+'}{100 - score_global}%")
m6.metric("Último Incidente", ult_scan_data)

st.divider()

# DASHBOARD OPERACIONAL COM 3 GRÁFICOS
g1, g2, g3 = st.columns([2, 2, 2])

with g1:
    st.markdown("##### 🌐 Cobertura de Ativos por Plataforma")
    if historico:
        df_hist = pd.DataFrame(historico)
        fig_so = px.pie(df_hist, names="so", hole=0.5, color_discrete_sequence=["#3B82F6", "#06B6D4"])
    else:
        df_demo = pd.DataFrame({"so": ["Sem Registros"], "qtd": [1]})
        fig_so = px.pie(df_demo, names="so", hole=0.5, color_discrete_sequence=["#1E293B"])
    fig_so.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=240, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_so, width="stretch")

with g2:
    st.markdown("##### 🛡️ Scorecard Geral de Vulnerabilidade")
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score_global,
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "#10B981" if score_global >= 75 else "#F59E0B" if score_global >= 50 else "#EF4444"},
            'steps': [
                {'range': [0, 40], 'color': "#EF4444"},
                {'range': [40, 75], 'color': "#F59E0B"},
                {'range': [75, 100], 'color': "#1E293B"}
            ],
        }
    ))
    fig_gauge.update_layout(margin=dict(t=20, b=10, l=10, r=10), height=240, paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_gauge, width="stretch")

with g3:
    st.markdown("##### ⚠️ Matriz de Severidade de Riscos (Real)")
    criticos = 0
    altos = 0
    medios = 0
    baixos = 0
    
    if historico:
        texto_auditoria = historico[-1]["auditoria"].lower()
        criticos = texto_auditoria.count("crítico") + texto_auditoria.count("critico")
        altos = texto_auditoria.count("alto") + texto_auditoria.count("vulnerabilidade")
        medios = texto_auditoria.count("médio") + texto_auditoria.count("alerta")
        baixos = texto_auditoria.count("baixo") + texto_auditoria.count("sucesso")

    df_vulc = pd.DataFrame({
        "Nível": ["Crítico", "Alto", "Médio", "Baixo"],
        "Ameaças": [criticos, altos, medios, baixos]
    })
    fig_bar = px.bar(
        df_vulc, x="Nível", y="Ameaças", color="Nível",
        color_discrete_map={"Crítico": "#EF4444", "Alto": "#F97316", "Médio": "#F59E0B", "Baixo": "#10B981"}
    )
    fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=240, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_bar, width="stretch")

st.divider()

# CENTRO DE COMANDO & ABAS ENTERPRISE
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Security Scan & Auto-Remediation", 
    "🎯 MITRE ATT&CK Matrix Mapping", 
    "📜 SIEM Audit Trail & Logs", 
    "📈 Historical Analytics"
])

with tab1:
    if "ultimo_scan" in st.session_state:
        scan = st.session_state["ultimo_scan"]
        st.caption(f"⏱️ **Último Diagnóstico Gravado:** {scan['data']} | Target: `{scan['host']}`")

        col_pdf, col_siem = st.columns(2)
        with col_pdf:
            caminho_pdf = scan.get("caminho_pdf") or gerar_relatorio_pdf(scan)
            if os.path.exists(caminho_pdf):
                with open(caminho_pdf, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Baixar Relatório Executivo PDF",
                        data=pdf_file,
                        file_name=os.path.basename(caminho_pdf),
                        mime="application/pdf",
                        width="stretch"
                    )
        with col_siem:
            cef_log = f"CEF:0|VanguardSec|SOC|1.0|100|Security Scan Completed|5|src={scan['host']} msg=Scan Successful"
            st.download_button(
                label="📡 Exportar Log Formato SIEM (CEF)",
                data=cef_log,
                file_name=f"VanguardSec_SIEM_{scan['host']}.cef",
                mime="text/plain",
                width="stretch"
            )

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🔍 Diagnóstico do Agente Auditor")
            st.info(scan["auditoria"])

        with c2:
            st.subheader("⚖️ Scorecard & Regras de Compliance (ISO 17021)")
            st.warning(scan["compliance"])

        st.subheader(f"🛠️ Script de Remediação Validado ({'Bash' if scan['so'] == 'Ubuntu Linux' else 'PowerShell'})")
        st.code(scan["remediacao"], language="bash" if scan["so"] == "Ubuntu Linux" else "powershell")

        st.divider()
        st.subheader("⚡ Ação de Contenção Automática")
        if st.button("🔥 Executar Mitigation Script em Produção", type="primary"):
            with st.spinner("Despachando payload de remediação..."):
                sucesso, logs = aplicar_remediacao_linux(scan["host"], ssh_user, ssh_pass, ssh_key, scan["remediacao"])
                if sucesso:
                    st.success("Remediação Aplicada com Éxito no Ativo!")
                    st.markdown(logs, unsafe_allow_html=True)
                else:
                    st.error(f"Erro na execução remota: {logs}")
    else:
        st.info("💡 Clique no botão **⚡ EXECUTE SOC SCAN & HARDENING** para a primeira varredura.")

with tab2:
    st.subheader("🎯 Mapeamento de Táticas e Técnicas (MITRE ATT&CK Framework)")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("**Táticas Identificadas nos Scans:**")
        st.error("• T1078 - Valid Accounts (Uso de credenciais fracas no SSH/WinRM)")
        st.warning("• T1021 - Remote Services (Serviço de gerenciamento exposto)")
        st.info("• T1059 - Command and Scripting Interpreter (Execução de scripts)")

    with col_m2:
        st.markdown("**Mitigações Automáticas do VanguardSec:**")
        st.success("✔ M1036 - Account Use Policies (Aplica regras complexas de senha)")
        st.success("✔ M1042 - Disable or Remove Feature or Program (Desativa portas vulneráveis)")
        st.success("✔ M1037 - Filter Network Traffic (Aplica regras rígidas de UFW/Firewall)")

with tab3:
    st.subheader("📜 SIEM Real-Time Audit Trail")
    if historico:
        for item in reversed(historico):
            pdf_info = f" | PDF: {os.path.basename(item.get('caminho_pdf', ''))}" if item.get('caminho_pdf') else ""
            st.code(f"[{item['data']}] [SECURITY_EVENT] Host: {item['host']} | OS: {item['so']} | CPU: {item.get('metricas', {}).get('cpu', 'N/A')} | RAM: {item.get('metricas', {}).get('ram', 'N/A')}{pdf_info}", language="text")
    else:
        st.text("Aguardando geração de eventos no sistema...")

with tab4:
    if historico:
        df_hist = pd.DataFrame(historico)
        st.subheader("Histórico Consolidado de Intervenções")
        st.dataframe(df_hist[["data", "host", "so"]], width="stretch")
    else:
        st.info("Nenhum registro no banco até o momento.")

# FRAGMENTO NATIVO DE AUTOMAÇÃO
if modo_autonomo:
    @st.fragment(run_every=intervalo_scan)
    def automacao_continua():
        rodar_varredura_completa()

    automacao_continua()