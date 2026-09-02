import subprocess
import logging

class ActiveDefenseSOAR:
    def __init__(self, modo_execucao: str = "PROD"):
        self.modo = modo_execucao

    def bloquear_ip_ufw(self, ip_origem: str) -> dict:
        """
        Executa o comando de bloqueio real no firewall UFW.
        """
        if not ip_origem or ip_origem == "UNKNOWN":
            return {"status": "ERRO", "mensagem": "IP inválido para bloqueio."}

        comando = ["sudo", "ufw", "deny", "from", ip_origem, "to", "any"]
        
        try:
            # Execução do comando no sistema operacional
            resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
            return {
                "status": "SUCESSO",
                "comando_executado": " ".join(comando),
                "saida_sistema": resultado.stdout.strip()
            }
        except subprocess.CalledProcessError as e:
            logging.error(f"Falha ao executar bloqueio UFW: {e.stderr}")
            return {
                "status": "ERRO",
                "comando_executado": " ".join(comando),
                "erro": e.stderr.strip()
            }

    def encerrar_sessoes_ip(self, ip_origem: str) -> dict:
        """
        Kill Switch: Encerra sessões ativas associadas ao IP atacante.
        """
        if not ip_origem or ip_origem == "UNKNOWN":
            return {"status": "ERRO", "mensagem": "IP inválido para encerramento de sessão."}

        comando = f"sudo pkill -f {ip_origem}"
        try:
            subprocess.run(comando, shell=True, check=False)
            return {"status": "SUCESSO", "acao": f"Sessões do IP {ip_origem} encerradas."}
        except Exception as e:
            return {"status": "ERRO", "mensagem": str(e)}

# Bloco de teste executável diretamente via terminal
if __name__ == "__main__":
    print("=========================================================")
    print("🛡️ TESTE DO MÓDULO DE DEFESA ATIVA (SOAR - UFW)")
    print("=========================================================\n")

    soar = ActiveDefenseSOAR()
    ip_teste = "185.220.101.5"

    print(f"[*] Testando execução de validação de IP: {ip_teste}")
    res_bloqueio = soar.bloquear_ip_ufw(ip_teste)

    print(f"Status: {res_bloqueio['status']}")
    print(f"Comando Gerado: {res_bloqueio['comando_executado']}")
    
    if res_bloqueio['status'] == 'ERRO':
        print(f"Detalhe/Erro (Esperado no Windows/Sem Sudo): {res_bloqueio.get('erro', res_bloqueio.get('mensagem'))}")
    else:
        print(f"Saída do Sistema: {res_bloqueio.get('saida_sistema')}")

    print("\n" + "=" * 57)