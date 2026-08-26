# modulos/automacoes.py

# Dicionário mapeando o ID de cada botão para o comando Bash a ser executado no servidor alvo
COMANDOS_AUTOMACAO = {
    # --- AUDITORIA & TELEMETRIA ---
    "1": "grep -i 'failed' /var/log/auth.log 2>/dev/null | tail -n 20 || journalctl -u sshd -n 20",
    "2": "echo '=== CPU/RAM ===' && free -h && echo '=== DISCO ===' && df -h /",
    "3": "echo 'PDF gerado via Dashboard Streamlit'",
    "4": "uname -a && cat /etc/os-release | grep PRETTY_NAME",
    "5": "uptime && free -m && df -h /",
    "6": "cat historico_scans.json 2>/dev/null | tail -n 30 || echo 'Sem histórico local'",

    # --- REDE & FIREWALL ---
    "7": "ss -tuln || netstat -tuln",
    "8": "ss -tn state established",
    "9": "sudo ufw status verbose",
    "10": "sudo ufw status | grep DENY",
    "11": "ping -c 4 8.8.8.8",
    "12": "ip route show",

    # --- SEGURANÇA & USUÁRIOS ---
    "13": "getent group sudo || getent group wheel",
    "14": "ls -la /root/.ssh/ /home/*/.ssh/ 2>/dev/null",
    "15": "who && w",
    "16": "grep 'Failed password' /var/log/auth.log | tail -n 15",
    "17": "ls -l /etc/passwd /etc/shadow",
    "18": "sudo grep -rnw '/etc/sudoers*' -e 'NOPASSWD'",

    # --- HARDWARE & RECURSOS ---
    "19": "ps aux --sort=-%cpu | head -n 10",
    "20": "ps aux --sort=-%mem | head -n 10",
    "21": "df -h",
    "22": "sensors 2>/dev/null || cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null || echo 'NPS/Sensors indisp.'",
    "23": "uptime -p",
    "24": "iostat -x 1 2 2>/dev/null || vmstat 1 2",

    # --- IA & INTELIGÊNCIA ---
    "25": "python3 agentes/agente_auditor.py 2>/dev/null || echo 'Executando via agente local'",
    "26": "sudo lynis audit system --quick 2>/dev/null || echo 'Lynis não instalado no servidor'"
}

def executar_comando_automacao(client_ssh, id_opcao: str) -> str:
    """
    Executa a automação selecionada via conexão SSH ativa.
    """
    comando = COMANDOS_AUTOMACAO.get(id_opcao)
    if not comando:
        return f"⚠️ Opção [{id_opcao}] não configurada."

    try:
        stdin, stdout, stderr = client_ssh.exec_command(comando, timeout=15)
        out = stdout.read().decode('utf-8').strip()
        err = stderr.read().decode('utf-8').strip()
        
        resultado = out if out else err
        return resultado if resultado else "✅ Comando executado (sem retorno de texto)."
    except Exception as e:
        return f"❌ Erro ao executar automação {id_opcao}: {e}"