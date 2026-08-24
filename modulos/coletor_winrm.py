import winrm

def coletar_dados_windows(hostname, username, password, port=5985):
    """
    Conecta ao Windows Server via WinRM e executa comandos PowerShell para auditoria.
    """
    comandos = {
        "Uso de CPU": "Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average",
        "Uso de RAM": "Get-CimInstance Win32_OperatingSystem | Select-Object @{Name='RAM';Expression={round((($_.TotalVisibleMemorySize - $_.FreePhysicalMemory)/$_.TotalVisibleMemorySize)*100,2)}} | Select-Object -ExpandProperty RAM",
        "Uso de Disco": "Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\" | Select-Object @{Name='Disk';Expression={round((($_.Size - $_.FreeSpace)/$_.Size)*100,2)}} | Select-Object -ExpandProperty Disk",
        "Status do Windows Firewall": "Get-NetFirewallProfile | Select-Object Name, Enabled | Format-Table -AutoSize",
        "Políticas de Senha do Sistema": "net accounts",
        "Membros do Grupo Administradores": "Get-LocalGroupMember -Group 'Administradores' | Select-Object Name, PrincipalSource | Format-Table -AutoSize",
        "Portas e Conexões Ativas": "Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort | Unique | Format-Table -AutoSize",
        "Status de Atualizações Pendentes": "Get-HotFix | Select-Object -Last 5 Description, HotFixID, InstalledOn | Format-Table -AutoSize",
        "Falhas de Logon Recentes (Event ID 4625)": "Get-EventLog -LogName Security -InstanceId 4625 -Newest 10 -ErrorAction SilentlyContinue | Select-Object TimeGenerated, Message | Format-Table -AutoSize"
    }

    dados_coletados = f"=== DADOS DO SERVIDOR WINDOWS: {hostname} ===\n\n"

    try:
        session = winrm.Session(f'http://{hostname}:{port}/wsman', auth=(username, password), transport='ntlm')

        for nome_teste, comando in comandos.items():
            resultado = session.run_ps(comando)
            saida = resultado.std_out.decode('utf-8', errors='ignore').strip()
            erro = resultado.std_err.decode('utf-8', errors='ignore').strip()

            dados_coletados += f"--- [ {nome_teste} ] ---\n"
            dados_coletados += f"Comando PowerShell: {comando}\n"
            dados_coletados += f"Resultado:\n{saida if saida else erro}\n\n"

        return dados_coletados

    except Exception as e:
        return f"Erro ao conectar ao servidor Windows {hostname} via WinRM: {str(e)}"