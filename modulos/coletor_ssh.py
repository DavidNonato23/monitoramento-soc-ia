import paramiko

def coletar_dados_servidor(hostname, username, password=None, key_filename=None):
    """Conecta ao servidor Linux via SSH e extrai telemetria bruta."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if key_filename:
            client.connect(hostname=hostname, username=username, key_filename=key_filename, timeout=10)
        else:
            client.connect(hostname=hostname, username=username, password=password, timeout=10)

        cmd_cpu = "top -bn1 | grep 'Cpu(s)'"
        cmd_ram = "free -m"
        cmd_disk = "df -h /"
        cmd_auth = "tail -n 20 /var/log/auth.log 2>/dev/null || tail -n 20 /var/log/syslog"

        _, stdout_cpu, _ = client.exec_command(cmd_cpu)
        _, stdout_ram, _ = client.exec_command(cmd_ram)
        _, stdout_disk, _ = client.exec_command(cmd_disk)
        _, stdout_auth, _ = client.exec_command(cmd_auth)

        telemetria = (
            f"--- [ Uso de CPU ] ---\n{stdout_cpu.read().decode('utf-8')}\n"
            f"--- [ Uso de RAM ] ---\n{stdout_ram.read().decode('utf-8')}\n"
            f"--- [ Uso de Disco ] ---\n{stdout_disk.read().decode('utf-8')}\n"
            f"--- [ Logs de Autenticação / Auth Log ] ---\n{stdout_auth.read().decode('utf-8')}\n"
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