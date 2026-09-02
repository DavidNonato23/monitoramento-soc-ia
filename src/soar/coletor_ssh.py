import paramiko
import re

def coletar_dados_servidor(hostname, username, password=None, key_filename=None):
    """Conecta ao servidor Linux via SSH e extrai telemetria focada em Segurança e Rede (SOC)."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if key_filename:
            client.connect(hostname=hostname, username=username, key_filename=key_filename, timeout=10)
        else:
            client.connect(hostname=hostname, username=username, password=password, timeout=10)

        # Comandos focados em Anomalias de Rede, Sessões e Autenticação
        cmd_tx_rx = "ip -s link | grep -A 1 -E 'eth0|enp|wlan0|lo' | grep -v 'valid_lft'"
        cmd_connections = "ss -tuln"
        cmd_established = "ss -ta state established"
        cmd_active_users = "who"
        cmd_failed_logins = "grep -c 'Failed password' /var/log/auth.log 2>/dev/null || echo 0"
        cmd_auth_tail = "tail -n 25 /var/log/auth.log 2>/dev/null || tail -n 25 /var/log/syslog"

        _, stdout_tx_rx, _ = client.exec_command(cmd_tx_rx)
        _, stdout_conn, _ = client.exec_command(cmd_connections)
        _, stdout_estab, _ = client.exec_command(cmd_established)
        _, stdout_users, _ = client.exec_command(cmd_active_users)
        _, stdout_failed, _ = client.exec_command(cmd_failed_logins)
        _, stdout_auth, _ = client.exec_command(cmd_auth_tail)

        telemetria = (
            f"--- [ Tráfego de Interface TX/RX ] ---\n{stdout_tx_rx.read().decode('utf-8')}\n"
            f"--- [ Portas Abertas / Listening ] ---\n{stdout_conn.read().decode('utf-8')}\n"
            f"--- [ Conexões Estabelecidas ] ---\n{stdout_estab.read().decode('utf-8')}\n"
            f"--- [ Sessões SSH / Usuários Ativos ] ---\n{stdout_users.read().decode('utf-8')}\n"
            f"--- [ Total de Logins Falhos ] ---\n{stdout_failed.read().decode('utf-8').strip()}\n"
            f"--- [ Logs do Auth Log ] ---\n{stdout_auth.read().decode('utf-8')}\n"
        )

        client.close()
        return telemetria

    except Exception as e:
        return f"Erro ao conectar via SSH: {str(e)}"


def aplicar_remediacao_linux(hostname, username, password=None, key_file=None, script=""):
    """Executa comandos de hardening/bloqueio diretamente no servidor remoto."""
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
            logs.append(f"$ {cmd}\nOutput: {out if out else err}")

        client.close()
        return True, "\n".join(logs)

    except Exception as e:
        return False, f"Erro SSH na remediação: {str(e)}"