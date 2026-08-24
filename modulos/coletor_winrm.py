import winrm

def coletar_dados_windows(hostname, username, password):
    """Conecta ao servidor Windows via WinRM e coleta métricas de sistema."""
    try:
        session = winrm.Session(hostname, auth=(username, password), transport='ntlm')
        
        ps_script = """
        Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory, TotalVisibleMemorySize
        Get-PSDrive C | Select-Object Used, Free
        Get-EventLog -LogName Security -Newest 10 2>$null
        """
        
        result = session.run_ps(ps_script)
        if result.status_code == 0:
            return f"--- [ Telemetria Windows Server ] ---\n{result.std_out.decode('utf-8')}"
        else:
            return f"Erro na execução WinRM: {result.std_err.decode('utf-8')}"

    except Exception as e:
        return f"Erro ao conectar via WinRM: {str(e)}"