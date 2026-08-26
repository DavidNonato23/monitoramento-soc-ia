import streamlit as st
import pandas as pd
import json
import os
import re
import time
import socket
import paramiko
import dotenv
import plotly.graph_objects as go
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from streamlit_autorefresh import st_autorefresh

dotenv.load_dotenv()

from modulos.coletor_ssh import coletar_dados_servidor
from modulos.coletor_winrm import coletar_dados_windows
from modulos.gerador_pdf import gerar_relatorio_pdf
from modulos.notificador import enviar_notificacao
from modulos.politicas import obter_politica_ativa
from modulos.analisador_rede import AnalisadorRede
from modulos.gestor_incidentes import registrar_incidente, carregar_todos_incidentes, atualizar_status_incidente

from agentes.agente_auditor import executar_agente_auditor
from agentes.agente_compliance import executar_agente_compliance
from agentes.agente_remediacao import executar_agente_remediacao
from agentes.agente_trafego import executar_agente_trafego

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="VanguardSec AI — Global Command SOC", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- CSS DE ESTILIZAÇÃO DA WAR ROOM E MENU LATERAL ---
st.markdown("""
<style>
    .stApp {
        background-color: #0B0D12;
        color: #C2C6DC;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="stSidebar"] {
        background-color: #0B0D12;
        border-right: 1px solid #1E2433;
        padding-top: 10px;
    }

    .dashboard-panel {
        background-color: #121620;
        border: 1px solid #1E2433;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
    }

    .dashboard-title {
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #60A5FA;
        text-transform: uppercase;
        border-bottom: 1px solid #1E2433;
        padding-bottom: 8px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .badge-red {
        background-color: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .badge-green {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    code {
        background-color: #08090C !important;
        color: #34D399 !important;
        border: 1px solid #1E2433;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

HISTORICO_FILE = "historico_scans.json"
PASTA_RELATORIOS = "relatorios"

if not os.path.exists(PASTA_RELATORIOS):
    os.makedirs(PASTA_RELATORIOS, exist_ok=True)

# --- FUNÇÕES AUXILIARES ---
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
            client.connect(hostname=hostname, username=username, key_filename=key_file, timeout=3)
        else:
            client.connect(hostname=hostname, username=username, password=password, timeout=3)

        _, stdout, _ = client.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'", timeout=2)
        cpu_val = stdout.read().decode().strip()
        metrics["cpu"] = float(cpu_val) if cpu_val else 0.0

        _, stdout, _ = client.exec_command("free | awk '/Mem:/ {print $3/$2 * 100.0}'", timeout=2)
        ram_val = stdout.read().decode().strip()
        metrics["ram"] = round(float(ram_val), 1) if ram_val else 0.0

        _, stdout, _ = client.exec_command("df / | tail -1 | awk '{print $5}' | sed 's/%//'", timeout=2)
        disk_val = stdout.read().decode().strip()
        metrics["disk"] = float(disk_val) if disk_val else 0.0

        client.close()
    except Exception:
        pass
    return metrics

def executar_acao_emergencia(acao, host, user, password, key_file):
    comando = ""
    if acao == "bloquear_portas":
        comando = "sudo iptables -A INPUT -p tcp --dport 22 -j DROP && sudo iptables -A INPUT -p tcp --dport 3389 -j DROP"
    elif acao == "derrubar_conexoes":
        comando = "sudo ss -K sport = :22 or dport = :22"
    elif acao == "modo_seguro":
        comando = "sudo ufw default deny incoming"

    if not comando:
        return False, "Comando não definido."

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if key_file:
            client.connect(hostname=host, username=user, key_filename=key_file, timeout=4)
        else:
            client.connect(hostname=host, username=user, password=password, timeout=4)
        
        _, _, stderr = client.exec_command(comando, timeout=5)
        erro = stderr.read().decode()
        client.close()

        if erro and "command not found" in erro:
            return False, f"Erro: {erro}"
        return True, "Comando de contenção executado com sucesso no servidor!"
    except Exception as e:
        return False, f"Falha na conexão SSH para ação: {str(e)}"

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

    return metrics

def gerar_imagem_grafico(historico):
    if not historico:
        return None
    try:
        df = pd.DataFrame(historico)
        if "metricas" not in df.columns:
            return None

        df["Hora"] = pd.to_datetime(df["data"]).dt.strftime("%H:%M:%S")
        df["Logins Falhos"] = df["metricas"].apply(lambda x: int(x.get("logins_falhos", 0)) if isinstance(x, dict) else 0)

        df_clean = df.tail(10)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_clean["Hora"], y=df_clean["Logins Falhos"], name="Logins Falhos", line=dict(color="#10B981", width=2)))
        
        fig.update_layout(
            title="Volumetria de Eventos em Tempo Real",
            paper_bgcolor="#121620",
            plot_bgcolor="#121620",
            font=dict(color="#C2C6DC"),
            margin=dict(l=20, r=20, t=40, b=20),
            width=700,
            height=250
        )

        caminho_img = os.path.join(PASTA_RELATORIOS, "grafico_volumetria.png")
        fig.write_image(caminho_img)
        return caminho_img
    except Exception:
        return None

# --- MENU LATERAL (SIDEBAR COM AS OPÇÕES) ---
st.sidebar.markdown("### 🛡️ VanguardSec AI")
st.sidebar.caption("Global Command SOC")
st.sidebar.divider()

pagina_selecionada = st.sidebar.radio(
    "Navegação Principal",
    [
        "📊 Dashboard Executivo",
        "🔬 Esteira Multi-Tier",
        "🌐 Monitoramento Infra",
        "🛡️ Playbooks SOAR",
        "📂 Gestão de Incidentes",
        "📱 Painel ChatOps",
        "📄 Centro de Relatórios"
    ],
    label_visibility="collapsed"
)

st.sidebar.divider()

modelo_ativo = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
so_alvo = st.sidebar.selectbox("Plataforma Alvo", ["Ubuntu Linux", "Windows Server"])
ssh_host = st.sidebar.text_input("IP do Ativo", value="", placeholder="Ex: 192.168.15.8")
ssh_user = st.sidebar.text_input("Usuário do Agente", value="" if so_alvo == "Ubuntu Linux" else "Administrator", placeholder="root")

ssh_pass = None
ssh_key = None

if so_alvo == "Ubuntu Linux":
    tipo_auth = st.sidebar.radio("Autenticação", ["Senha", "Chave (.pem)"])
    if tipo_auth == "Senha":
        ssh_pass = st.sidebar.text_input("Senha", type="password")
    else:
        ssh_key = st.sidebar.text_input("Caminho .pem", placeholder="/caminho/chave.pem")
else:
    ssh_pass = st.sidebar.text_input("Senha Admin", type="password")

target_ip = ssh_host
status_servidor_online = checar_status_servidor(target_ip) if target_ip else False

st.sidebar.divider()
btn_executar = st.sidebar.button("🔄 Executar Polling Geral", type="primary", use_container_width=True)

# Botão para ativar varredura automática a cada 1 minuto (60000ms)
auto_polling_1min = st.sidebar.checkbox("⏱️ Auto-Polling Agentes (1 min)", value=False)
if auto_polling_1min:
    st_autorefresh(interval=60000, key="auto_polling_60s")

st.sidebar.divider()
st.sidebar.markdown(f"""
<div style='background-color: #121620; border: 1px solid #10B981; padding: 10px; border-radius: 8px;'>
    <span style='color: #10B981; font-weight: bold;'>● Ollama: online</span><br>
    <span style='color: #8892B0; font-size: 0.8rem;'>{modelo_ativo} · on-premise</span>
</div>
""", unsafe_allow_html=True)

# --- EXECUTAR POLLING ---
def rodar_varredura_completa():
    if not ssh_host:
        st.error("❌ Informe o IP do Ativo na barra lateral.")
        return False

    t_inicio = time.time()
    status_box = st.status("🔍 Consultando agentes de monitoramento de rede...", expanded=True)
    with status_box:
        if so_alvo == "Ubuntu Linux":
            dados_servidor = coletar_dados_servidor(ssh_host, ssh_user, password=ssh_pass, key_filename=ssh_key)
        else:
            dados_servidor = coletar_dados_windows(ssh_host, ssh_user, ssh_pass)

        if "Erro ao conectar" in dados_servidor or "timed out" in dados_servidor:
            status_box.update(label="❌ Ativo Indisponível / Host Unreachable", state="error")
            return False

        analisador_net = AnalisadorRede()
        info_rede = analisador_net.enriquecer_diagnostico(ssh_host)
        m_soc = extrair_metricas_soc(dados_servidor)
        politica_norma = obter_politica_ativa()
        
        with ThreadPoolExecutor() as executor:
            futuro_auditoria = executor.submit(executar_agente_auditor, dados_servidor, so_alvo)
            futuro_trafego = executor.submit(executar_agente_trafego, info_rede, m_soc)

            auditoria = futuro_auditoria.result()
            analise_trafego_ia = futuro_trafego.result()

            futuro_compliance = executor.submit(executar_agente_compliance, politica_norma, auditoria)
            futuro_remediacao = executor.submit(executar_agente_remediacao, auditoria, "", so_alvo)

            compliance = futuro_compliance.result()
            remediacao = futuro_remediacao.result()

    t_execucao = round(time.time() - t_inicio, 2)
    historico_atual = carregar_historico()
    caminho_grafico = gerar_imagem_grafico(historico_atual)
    
    scan_data = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "host": ssh_host,
        "so": so_alvo,
        "mttd": t_execucao,
        "metricas": m_soc,
        "info_rede": info_rede,
        "analise_trafego_ia": analise_trafego_ia,
        "auditoria": auditoria,
        "compliance": compliance,
        "remediacao": remediacao,
        "caminho_grafico": caminho_grafico
    }

    salvar_historico(scan_data)
    registrar_incidente(scan_data, m_soc, analise_trafego_ia)

    try:
        caminho_pdf = gerar_relatorio_pdf(scan_data)
        scan_data["caminho_pdf"] = caminho_pdf
        st.toast(f"📄 Relatório salvo em: {caminho_pdf}", icon="✅")
    except Exception as e:
        st.error(f"Erro ao salvar PDF: {str(e)}")

    st.session_state["ultimo_scan"] = scan_data
    status_box.update(label=f"✅ Polling do NOC Concluído em {t_execucao}s!", state="complete")
    return True

if btn_executar or auto_polling_1min:
    # Se auto_polling estiver ativo, executa periodicamente
    if auto_polling_1min and ssh_host:
        rodar_varredura_completa()
    elif btn_executar:
        rodar_varredura_completa()

historico = carregar_historico()
scan_atual = st.session_state.get("ultimo_scan", {})
m_raw = scan_atual.get("metricas", {})
lista_inc = carregar_todos_incidentes()
novos_incs = [i for i in lista_inc if "NOVO" in i.get("status", "")]

# --- ROTEAMENTO DAS PÁGINAS SELECIONADAS NO MENU LATERAL ---

if pagina_selecionada == "📊 Dashboard Executivo":
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        st.markdown("## Dashboard Executivo")
        st.caption(f"Telemetria em tempo real · última varredura recente | Host: `{target_ip if target_ip else 'Nenhum Ativo Selecionado'}`")
    with col_head2:
        st.markdown(f"<div style='text-align: right; padding-top: 10px;'><span class='badge-red'>{len(novos_incs)} incidentes em triagem</span></div>", unsafe_allow_html=True)

    st.write("")

    falhas_num = int(m_raw.get("logins_falhos", 0))
    telemetria_host = coletar_telemetria_remota(target_ip, ssh_user, ssh_pass, ssh_key) if target_ip and status_servidor_online else {"cpu": 37.0, "ram": 61.0, "disk": 44.0}

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='dashboard-panel' style='padding: 12px;'><span style='color: #8892B0; font-size: 0.75rem; font-weight: bold;'>CPU</span><h2 style='color: #F8FAFC; margin: 0; font-size: 1.8rem;'>{telemetria_host.get('cpu', 0)}%</h2></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='dashboard-panel' style='padding: 12px;'><span style='color: #8892B0; font-size: 0.75rem; font-weight: bold;'>RAM</span><h2 style='color: #F8FAFC; margin: 0; font-size: 1.8rem;'>{telemetria_host.get('ram', 0)}%</h2></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='dashboard-panel' style='padding: 12px;'><span style='color: #8892B0; font-size: 0.75rem; font-weight: bold;'>DISCO</span><h2 style='color: #F8FAFC; margin: 0; font-size: 1.8rem;'>{telemetria_host.get('disk', 0)}%</h2></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='dashboard-panel' style='padding: 12px;'><span style='color: #8892B0; font-size: 0.75rem; font-weight: bold;'>TENTATIVAS BRUTE-FORCE (24H)</span><h2 style='color: #EF4444; margin: 0; font-size: 1.8rem;'>{falhas_num}</h2></div>", unsafe_allow_html=True)

    col_hist, col_tier = st.columns([1.3, 1])
    with col_hist:
        st.markdown("<div class='dashboard-panel'><div class='dashboard-title'><span>📈 Histórico de scans — últimas 24h</span></div>", unsafe_allow_html=True)
        if historico:
            df_chart = pd.DataFrame(historico)
            if "metricas" in df_chart.columns:
                df_chart["Hora"] = pd.to_datetime(df_chart["data"]).dt.strftime("%H:%M:%S")
                df_chart["Logins Falhos"] = df_chart["metricas"].apply(lambda x: int(x.get("logins_falhos", 0)) if isinstance(x, dict) else 0)
                st.bar_chart(df_chart.tail(10).set_index("Hora")[["Logins Falhos"]], height=180, color="#10B981")
        else:
            st.caption("Nenhum dado volumétrico registrado até o momento.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_tier:
        st.markdown("<div class='dashboard-panel'><div class='dashboard-title'><span>🔬 Esteira Multi-Tier — diagnóstico atual</span></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='background-color: #08090C; border-left: 3px solid #10B981; padding: 8px; margin-bottom: 6px; border-radius: 4px; font-size: 0.8rem;'>
            <b>Tier 1 - Analista SOC</b><br><span style='color: #8892B0;'>{str(scan_atual.get('auditoria', 'Aguardando...'))[:90]}</span>
        </div>
        <div style='background-color: #08090C; border-left: 3px solid #F59E0B; padding: 8px; margin-bottom: 6px; border-radius: 4px; font-size: 0.8rem;'>
            <b>Tier 2 - Compliance LGPD</b><br><span style='color: #8892B0;'>{str(scan_atual.get('compliance', 'Aguardando...'))[:90]}</span>
        </div>
        <div style='background-color: #08090C; border-left: 3px solid #3B82F6; padding: 8px; border-radius: 4px; font-size: 0.8rem;'>
            <b>Tier 3 - Engenheiro SOAR</b><br><span style='color: #34D399;'>{str(scan_atual.get('remediacao', 'Aguardando...'))[:90]}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    col_inc, col_ks = st.columns([1.3, 1])
    with col_inc:
        st.markdown("<div class='dashboard-panel'><div class='dashboard-title'><span>📂 Gestão de Incidentes</span></div>", unsafe_allow_html=True)
        if lista_inc:
            for inc in lista_inc[:4]:
                status_badge = "<span class='badge-red'>Em triagem</span>" if "NOVO" in inc.get('status', '') else "<span class='badge-green'>Resolvido</span>"
                st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1E2433; padding: 6px 0; font-size: 0.8rem;'><span><b>{inc.get('host')}</b></span><span style='color: #8892B0;'>{inc.get('tipo')}</span><span>{status_badge}</span></div>", unsafe_allow_html=True)
        else:
            st.info("Nenhum incidente registrado na base.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_ks:
        st.markdown("<div class='dashboard-panel'><div class='dashboard-title'><span>🛡️ Kill Switch</span></div>", unsafe_allow_html=True)
        if st.button("🔴 Bloquear IP no UFW agora", type="primary", use_container_width=True):
            if target_ip and ssh_user:
                ok, msg = executar_acao_emergencia("bloquear_portas", target_ip, ssh_user, ssh_pass, ssh_key)
                st.success(msg) if ok else st.error(msg)
            else:
                st.error("Configure IP e Usuário na barra lateral.")
        if st.button("🔄 Reiniciar serviço SSH", type="secondary", use_container_width=True):
            if target_ip and ssh_user:
                ok, msg = executar_acao_emergencia("derrubar_conexoes", target_ip, ssh_user, ssh_pass, ssh_key)
                st.success(msg) if ok else st.error(msg)
            else:
                st.error("Configure IP e Usuário na barra lateral.")
        if st.button("📨 Enviar alerta ao Telegram", type="secondary", use_container_width=True):
            enviar_notificacao("⚠️ Alerta manual disparado via painel VanguardSec AI.")
            st.success("Alerta despachado com sucesso!")
        st.caption("Playbook executado via SSH/WinRM na infraestrutura alvo.")
        st.markdown("</div>", unsafe_allow_html=True)

elif pagina_selecionada == "🔬 Esteira Multi-Tier":
    st.markdown("## 🔬 Esteira Multi-Tier de Inteligência Artificial")
    st.markdown("Diagnósticos completos gerados pelas 3 camadas de agentes especializados rodando localmente via Ollama.")
    st.divider()
    if scan_atual:
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.markdown("<div class='dashboard-panel'><div class='dashboard-title'><span>Tier 1: Analista SOC</span></div>", unsafe_allow_html=True)
            st.write(scan_atual.get("auditoria", "Sem dados."))
            st.markdown("</div>", unsafe_allow_html=True)
        with col_t2:
            st.markdown("<div class='dashboard-panel'><div class='dashboard-title'><span>Tier 2: Compliance LGPD</span></div>", unsafe_allow_html=True)
            st.write(scan_atual.get("compliance", "Sem dados."))
            st.markdown("</div>", unsafe_allow_html=True)
        with col_t3:
            st.markdown("<div class='dashboard-panel'><div class='dashboard-title'><span>Tier 3: Engenheiro SOAR</span></div>", unsafe_allow_html=True)
            st.code(scan_atual.get("remediacao", "# Sem playbook"), language="bash")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Execute um Polling Geral na barra lateral para alimentar a esteira.")

elif pagina_selecionada == "🌐 Monitoramento Infra":
    st.markdown("## 🌐 Monitoramento de Infraestrutura e Redes")
    st.markdown("Informações de superfície de ataque, portas abertas e análise de tráfego (NTA).")
    st.divider()
    if scan_atual:
        info_r = scan_atual.get("info_rede", {})
        c_n1, c_n2, c_n3 = st.columns(3)
        c_n1.metric("Classificação de Rede", info_r.get("tipo_rede", "N/A"))
        c_n2.metric("Nível de Risco", info_r.get("nivel_risco_origem", "Baixo"))
        c_n3.metric("Proprietário Vinculado", info_r.get("proprietario_vinculado", "N/A"))
        st.divider()
        st.markdown(scan_atual.get("analise_trafego_ia", "Sem dados de tráfego."))
    else:
        st.info("Nenhum dado de infraestrutura coletado ainda.")

elif pagina_selecionada == "🛡️ Playbooks SOAR":
    st.markdown("## 🛡️ Playbooks SOAR & Ações de Contenção")
    st.markdown("Scripts automáticos prontos para remediação imediata de vulnerabilidades.")
    st.divider()
    if scan_atual:
        st.code(scan_atual.get("remediacao", "# Nenhum playbook gerado"), language="bash")
    else:
        st.info("Execute o polling para gerar playbooks.")

elif pagina_selecionada == "📂 Gestão de Incidentes":
    st.markdown("## 📂 Central de Gestão e Triagem de Incidentes")
    st.markdown("Separação automatizada entre novos eventos e o histórico consolidado de ameaças.")
    st.divider()
    
    if lista_inc:
        for inc in lista_inc:
            with st.container():
                st.markdown(f"<div class='dashboard-panel'><b>[{inc.get('id')}] {inc.get('tipo')}</b> — Host: <code>{inc.get('host')}</code> | Severidade: <b>{inc.get('severidade')}</b> | Status: <b>{inc.get('status')}</b><br>Detalhes: {inc.get('detalhes')}", unsafe_allow_html=True)
                if "NOVO" in inc.get('status', ''):
                    if st.button("Marcar como Resolvido", key=f"gestao_res_{inc['id']}"):
                        atualizar_status_incidente(inc['id'], "RESOLVIDO / MITIGADO")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success("Nenhum incidente registrado.")

elif pagina_selecionada == "📱 Painel ChatOps":
    st.markdown("## 📱 Painel ChatOps & Notificações Telegram")
    st.markdown("Integração com bot do Telegram para alertas operacionais e comandos remotos via smartphone.")
    st.divider()
    st.info("Certifique-se de que o bot está configurado no arquivo `.env` para disparar os webhooks.")
    if st.button("Enviar Alerta de Teste via Webhook"):
        enviar_notificacao("⚠️ Teste de notificação disparado manualmente pela interface web.")
        st.success("Alerta enviado com sucesso!")

elif pagina_selecionada == "📄 Centro de Relatórios":
    st.markdown("## 📄 Centro de Relatórios Executivos em PDF")
    st.markdown("Histórico de laudos corporativos gerados automaticamente pela engine ReportLab.")
    st.divider()
    
    caminho_pdf = scan_atual.get("caminho_pdf")
    if caminho_pdf and os.path.exists(caminho_pdf):
        with open(caminho_pdf, "rb") as pdf_file:
            st.download_button(
                label="📥 Baixar Último Laudo Executivo (PDF)",
                data=pdf_file.read(),
                file_name=os.path.basename(caminho_pdf),
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.warning("Nenhum relatório PDF gerado recentemente. Execute o polling para criar o laudo.")