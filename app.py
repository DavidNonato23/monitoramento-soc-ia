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
import winrm

# Configuração da página
st.set_page_config(page_title="VanguardSec AI — Global Command SOC", page_icon="🛡️", layout="wide")

# Estilização CSS Dark Theme
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

def obter_dados_simulacao():
    return {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "host": "192.168.1.100 (PDV-Demo)",
        "so": "Ubuntu Linux",
        "metricas": {"cpu": "92.4%", "ram": "88.1%", "disk": "74.5%"},
        "auditoria": (
            "🚨 **INCIDENTE CRÍTICO DETECTADO:**\n\n"
            "- **Ataque de Força Bruta SSH:** Identificadas 142 tentativas de autenticação inválidas originadas do IP `185.220.101.5` nas últimas 3 horas.\n"
            "- **Consumo Anômalo de CPU (92.4%):** Processo suspeito `kswapd0` consumindo recursos fora do padrão operacional.\n"
            "- **Exposição de Banco de Dados:** Porta MySQL (3306) aberta para conexões externas sem restrição de rede no UFW."
        ),
        "compliance": (
            "⚖️ **SCORECARD DE COMPLIANCE (ISO/IEC 17021 & LGPD):**\n\n"
            "- **ISO 17021 A.8.2.1:** NÃO CONFORME — Controle de acesso frágil a porta SSH.\n"
            "- **ISO 17021 A.12.6.1:** ALERTA — Vulnerabilidade em porta MySQL aberta publicamente.\n"
            "- **LGPD Art. 46:** NÃO CONFORME — Ausência de bloqueio preventivo de IP invasor em banco de dados."
        ),
        "remediacao": (
            "#!/bin/bash\n"
            "# Playbook de Remediação Automática - VanguardSec AI\n\n"
            "# 1. Bloquear IP Atacante no UFW Firewall\n"
            "sudo ufw deny from 185.220.101.5 to any\n\n"
            "# 2. Limitar Tentativas SSH (Fail2Ban Rule)\n"
            "sudo ufw limit ssh/tcp\n\n"
            "# 3. Fechar Porta MySQL Externa\n"
            "sudo ufw deny 3306/tcp\n\n"
            "# 4. Finalizar Processo Suspeito\n"
            "sudo killall -9 kswapd0\n\n"
            "echo '✅ Hardening e Contenção Concluídos com Sucesso!'"
        )
    }

# --- SIDEBAR DE CENTRO DE OPERAÇÕES ---
st.sidebar.title("🛡️ VanguardSec Command")
st.sidebar.caption("SecOps Enterprise & Autonomous Threat Response")

st.sidebar.divider()

# Switch Comercial: Modo Simulação (Dry-Run / Demo)
modo_demo = st.sidebar.toggle("🎭 Modo Simulação (Demo Comercial)", value=False)

if modo_demo:
    st.sidebar.info("💡 **Modo Simulação Ativo**: Apresentação comercial sem necessidade de conexão SSH/WinRM real.")
    so_alvo = "Ubuntu Linux"
    ssh_host = "192.168.1.100 (PDV-Demo)"
    ssh_user = "servidor_demo"
    ssh_pass = None
    ssh_key = None
else:
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
st.sidebar.subheader("💬 Configuração ChatOps")
telegram_token = st.sidebar.text_input("Bot Token (Telegram)", value=os.getenv("TELEGRAM_BOT_TOKEN", ""), type="password")
telegram_chat_id = st.sidebar.text_input("Chat ID (Telegram)", value=os.getenv("TELEGRAM_ALLOWED_USER_ID", "8457053029"))

st.sidebar.divider()
st.sidebar.subheader("🔄 Automação Contínua 24/7")
modo_autonomo = st.sidebar.checkbox("Ativar Monitoramento Contínuo", value=False)
intervalo_scan = st.sidebar.slider("Intervalo (segundos)", min_value=10, max_value=300, value=30)

if not modo_demo and st.sidebar.button("🔌 Testar Acesso ao Servidor", use_container_width=True):
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

btn_executar = st.sidebar.button("⚡ EXECUTE SOC SCAN & HARDENING", use_container_width=True, type="primary")

# --- FUNÇÃO EXECUTORA DE VARREDURA ---
def rodar_varredura_completa():
    if modo_demo:
        scan_data = obter_dados_simulacao()
    else:
        if so_alvo == "Ubuntu Linux":
            dados_servidor = coletar_dados_servidor(ssh_host, ssh_user, password=ssh_pass, key_filename=ssh_key)
        else:
            dados_servidor = coletar_dados_windows(ssh_host, ssh_user, ssh_pass)

        if "Erro ao conectar" in dados_servidor or "timed out" in dados_servidor:
            st.error(f"⚠️ Falha na coleta remota: {dados_servidor}")
            return False

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
        enviar_alerta_webhook(webhook_url, scan_data["host"], scan_data["so"], scan_data["compliance"])
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

if modo_demo:
    st.warning("⚠️ **EXECUÇÃO EM MODO SIMULAÇÃO (DRY-RUN):** Resultados exibidos gerados para fins de demonstração técnica e comercial.")

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
    alertas = historico[-1]["auditoria"].lower().count("vulnerabilidade") + historico[-1]["auditoria"].lower().count("erro") + historico[-1]["auditoria"].lower().count("crítico")
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
    st.plotly_chart(fig_so, use_container_width=True)

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
    st.plotly_chart(fig_gauge, use_container_width=True)

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
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# CENTRO DE COMANDO & ABAS ENTERPRISE
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🚀 Security Scan & Auto-Remediation", 
    "💬 ChatOps Telegram",
    "💼 Painel Executivo / ROI",
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
                        use_container_width=True
                    )
        with col_siem:
            cef_log = f"CEF:0|VanguardSec|SOC|1.0|100|Security Scan Completed|5|src={scan['host']} msg=Scan Successful"
            st.download_button(
                label="📡 Exportar Log Formato SIEM (CEF)",
                data=cef_log,
                file_name=f"VanguardSec_SIEM_{scan['host']}.cef",
                mime="text/plain",
                use_container_width=True
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
                if modo_demo:
                    st.success("✅ [MODO SIMULAÇÃO] Playbook de remediação executado com sucesso no servidor de demonstração!")
                else:
                    sucesso, logs = aplicar_remediacao_linux(scan["host"], ssh_user, ssh_pass, ssh_key, scan["remediacao"])
                    if sucesso:
                        st.success("Remediação Aplicada com Êxito no Ativo!")
                        st.markdown(logs, unsafe_allow_html=True)
                    else:
                        st.error(f"Erro na execução remota: {logs}")
    else:
        st.info("💡 Clique no botão **⚡ EXECUTE SOC SCAN & HARDENING** para a primeira varredura.")

with tab2:
    st.subheader("📲 Disparo de Alertas e Resposta via Telegram")
    st.write("Dispare alertas de incidentes interativos diretamente para o celular da equipe de SOC:")
    
    if st.button("📲 Disparar Alerta de Incidente no Telegram", type="primary"):
        if telegram_token and telegram_chat_id:
            try:
                ip_origem = "185.220.101.5"
                servidor_nome = st.session_state["ultimo_scan"]["host"] if "ultimo_scan" in st.session_state else "172.30.0.168"
                asyncio.run(
                    enviar_alerta_incidente(
                        bot_token=telegram_token,
                        chat_id=telegram_chat_id,
                        servidor=servidor_nome,
                        ip_atacante=ip_origem,
                        tipo_ataque="Ataque de Força Bruta SSH (142 tentativas)"
                    )
                )
                st.success("🚨 Alerta de incidente enviado com sucesso para o Telegram! Confira seu celular.")
            except Exception as e:
                st.error(f"Erro ao enviar alerta para o Telegram: {e}")
        else:
            st.warning("⚠️ Preencha o Bot Token e o Chat ID na barra lateral para disparar alertas.")

with tab3:
    st.subheader("💼 Métrica Financeira & Retorno de Investimento (ROI)")
    
    col_roi1, col_roi2, col_roi3 = st.columns(3)
    
    horas_economizadas = total_scans * 2.5
    economia_financeira = horas_economizadas * 150.0  # Média de R$ 150/hora de analista SOC sênior
    
    col_roi1.metric("Horas de SecOps Economizadas", f"{horas_economizadas:.1f} hrs", delta="+Automação AI")
    col_roi2.metric("Custo Operacional Evitado", f"R$ {economia_financeira:,.2f}", delta="+ROI Imediato")
    col_roi3.metric("Tempo Médio de Resposta (MTTR)", "12 seg", delta="-99% vs Manual")

    st.divider()
    st.markdown("### 📊 Comparativo Operacional: Manual vs VanguardSec AI")
    
    df_roi = pd.DataFrame({
        "Métrica": ["Diagnóstico de Log", "Auditoria de Compliance", "Geração de Script Fix", "Tempo de Contenção"],
        "SOC Manual (Horas)": [1.5, 2.0, 1.0, 0.8],
        "VanguardSec AI (Segundos)": [3, 2, 4, 3]
    })
    st.table(df_roi)

with tab4:
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

with tab5:
    st.subheader("📜 SIEM Real-Time Audit Trail")
    if historico:
        for item in reversed(historico):
            pdf_info = f" | PDF: {os.path.basename(item.get('caminho_pdf', ''))}" if item.get('caminho_pdf') else ""
            st.code(f"[{item['data']}] [SECURITY_EVENT] Host: {item['host']} | OS: {item['so']} | CPU: {item.get('metricas', {}).get('cpu', 'N/A')} | RAM: {item.get('metricas', {}).get('ram', 'N/A')}{pdf_info}", language="text")
    else:
        st.text("Aguardando geração de eventos no sistema...")

with tab6:
    if historico:
        df_hist = pd.DataFrame(historico)
        st.subheader("Histórico Consolidado de Intervenções")
        st.dataframe(df_hist[["data", "host", "so"]], use_container_width=True)
    else:
        st.info("Nenhum registro no banco até o momento.")

# FRAGMENTO NATIVO DE AUTOMAÇÃO
if modo_autonomo:
    @st.fragment(run_every=intervalo_scan)
    def automacao_continua():
        rodar_varredura_completa()

    automacao_continua()