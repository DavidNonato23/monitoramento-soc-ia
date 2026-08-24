import getpass

# Novas Importações Modularizadas
from modulos.leitor_politicas import carregar_politicas
from modulos.coletor_ssh import coletar_dados_servidor
from modulos.coletor_winrm import coletar_dados_windows

from agentes.agente_auditor import executar_agente_auditor
from agentes.agente_compliance import executar_agente_compliance
from agentes.agente_remediacao import executar_agente_remediacao

import paramiko
import winrm

def aplicar_remediacao_linux(hostname, username, script, password=None, key_filename=None):
    print(f"\n[+] Conectando via SSH a {hostname} para aplicar correções...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if key_filename:
            client.connect(hostname=hostname, username=username, key_filename=key_filename, timeout=10)
        else:
            client.connect(hostname=hostname, username=username, password=password, timeout=10)

        linhas = [cmd.strip() for cmd in script.split('\n') if cmd.strip() and not cmd.strip().startswith('#')]
        
        for comando in linhas:
            print(f" Executando Bash: {comando}")
            stdin, stdout, stderr = client.exec_command(comando)
            out = stdout.read().decode('utf-8').strip()
            err = stderr.read().decode('utf-8').strip()
            if out: print(f"   ↳ Saída: {out}")
            if err: print(f"   ↳ Aviso/Erro: {err}")

        client.close()
        print("\n[✔] Remediações em Linux concluídas.")
    except Exception as e:
        print(f"\n[✘] Erro ao aplicar via SSH: {str(e)}")

def aplicar_remediacao_windows(hostname, username, password, script):
    print(f"\n[+] Conectando via WinRM a {hostname} para aplicar correções...")
    try:
        session = winrm.Session(f'http://{hostname}:5985/wsman', auth=(username, password), transport='ntlm')
        linhas = [cmd.strip() for cmd in script.split('\n') if cmd.strip() and not cmd.strip().startswith('#')]
        
        for comando in linhas:
            print(f" Executando PowerShell: {comando}")
            res = session.run_ps(comando)
            out = res.std_out.decode('utf-8', errors='ignore').strip()
            err = res.std_err.decode('utf-8', errors='ignore').strip()
            if out: print(f"   ↳ Saída: {out}")
            if err: print(f"   ↳ Aviso/Erro: {err}")

        print("\n[✔] Remediações em Windows concluídas.")
    except Exception as e:
        print(f"\n[✘] Erro ao aplicar via WinRM: {str(e)}")

def main():
    print("=" * 60)
    print(" AEGIS OPS — MULTI-AGENT COMPLIANCE & HARDENING ENGINE ")
    print("=" * 60)

    # 1. Escolha da Plataforma
    print("\nSeleção de Plataforma:")
    print("1. Ubuntu Linux (SSH)")
    print("2. Windows Server (WinRM)")
    opcao_so = input("Opção [1/2]: ").strip()

    so_alvo = "Ubuntu Linux" if opcao_so == '1' else "Windows Server"

    # 2. Configuração do Servidor
    print(f"\n--- [CONFIGURAÇÃO DA CONEXÃO: {so_alvo.upper()}] ---")
    HOST = input("IP/Hostname do Servidor: ").strip()
    USER = input(f"Usuário ({'ubuntu' if opcao_so == '1' else 'Administrator'}): ").strip()
    
    PASS = None
    KEY = None

    if so_alvo == "Ubuntu Linux":
        tipo_auth = input("Autenticação por (1) Senha ou (2) Chave SSH [1/2]: ").strip()
        if tipo_auth == '2':
            KEY = input("Caminho para a chave (.pem / id_rsa): ").strip()
        else:
            PASS = getpass.getpass("Senha SSH: ")
    else:
        PASS = getpass.getpass("Senha do Administrador/WinRM: ")

    # 3. Carregar Políticas Locais
    print("\n--- [1/5] CARREGANDO PASTA DE POLÍTICAS ---")
    politicas = carregar_politicas("politicas")

    # 4. Coleta Automática de Configurações
    print(f"\n--- [2/5] COLETANDO CONFIGURAÇÕES REMOTAS VIA {'SSH' if opcao_so == '1' else 'WINRM'} ---")
    if so_alvo == "Ubuntu Linux":
        dados_servidor = coletar_dados_servidor(HOST, USER, password=PASS, key_filename=KEY)
    else:
        dados_servidor = coletar_dados_windows(HOST, USER, PASS)

    if "Erro ao conectar" in dados_servidor:
        print(f"\n[✘] Falha de Conexão: {dados_servidor}")
        return

    print("[✔] Dados extraídos com sucesso.")

    # 5. Pipeline dos Agentes IA
    print(f"\n--- [3/5] AGENTE 1: AUDITORIA ({so_alvo}) ---")
    relatorio_auditoria = executar_agente_auditor(politicas, dados_servidor, so_alvo=so_alvo)
    print(relatorio_auditoria)

    print("\n--- [4/5] AGENTE 2: MONITOR DE COMPLIANCE ---")
    relatorio_compliance = executar_agente_compliance(politicas, relatorio_auditoria)
    print(relatorio_compliance)

    print(f"\n--- [5/5] AGENTE 3: ANALISTA DE REMEDIAÇÃO ({'BASH' if opcao_so == '1' else 'POWERSHELL'}) ---")
    script_remediacao = executar_agente_remediacao(relatorio_auditoria, relatorio_compliance, so_alvo=so_alvo)
    print(script_remediacao)

    # 6. Execução Opcional das Remediações
    print("\n" + "="*60)
    confirmacao = input(f"Deseja aplicar as correções em {HOST} ({so_alvo}) agora? (s/N): ").strip().lower()
    
    if confirmacao == 's':
        if so_alvo == "Ubuntu Linux":
            aplicar_remediacao_linux(HOST, USER, script_remediacao, password=PASS, key_filename=KEY)
        else:
            aplicar_remediacao_windows(HOST, USER, PASS, script_remediacao)
    else:
        print("\n[!] Processo concluído sem alterações efetuadas no servidor.")

if __name__ == "__main__":
    main()