import paramiko

def coletar_dados_servidor(hostname, username, password=None, key_filename=None, port=22):
    comandos = {
        "Uso de CPU": "top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'",
        "Uso de RAM": "free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'",
        "Uso de Disco": "df -h / | awk 'NR==2{print $5}'",
        "Configuração SSH": "cat /etc/ssh/sshd_config | grep -E '^(PermitRootLogin|PasswordAuthentication|Port)'",
        "Status do Firewall (UFW)": "sudo ufw status | head -n 5",
        "Atualizações de Segurança Pendentes": "apt-get -s upgrade | grep -i security | wc -l",
        "Usuários Sudo": "grep -Po '^sudo:\\x3a.*$' /etc/group",
        "Portas Abertas": "ss -tulpn | head -n 6",
        "Tentativas de Ataque SSH": "grep -a 'Failed password' /var/log/auth.log | tail -n 5 || journalctl -u ssh.service -n 5 --grep='Failed password'"
    }

    dados_coletados = f"=== DADOS DO SERVIDOR LINUX: {hostname} ===\n\n"

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if key_filename:
            client.connect(hostname=hostname, port=port, username=username, key_filename=key_filename, timeout=5)
        else:
            client.connect(hostname=hostname, port=port, username=username, password=password, timeout=5)

        for nome_teste, comando in comandos.items():
            stdin, stdout, stderr = client.exec_command(comando, timeout=5)
            saida = stdout.read().decode('utf-8', errors='ignore').strip()
            erro = stderr.read().decode('utf-8', errors='ignore').strip()
            
            dados_coletados += f"--- [ {nome_teste} ] ---\n"
            dados_coletados += f"{saida if saida else 'Sem registros ou ' + erro}\n\n"

        client.close()
        return dados_coletados

    except Exception as e:
        return f"Erro ao conectar ao servidor {hostname} via SSH: {str(e)}"