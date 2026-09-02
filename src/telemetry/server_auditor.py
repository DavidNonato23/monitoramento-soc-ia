import subprocess
import json
import datetime
from typing import Dict, Any

class ServerAuditorCollector:
    def __init__(self):
        pass

    def verificar_expiracao_ssl(self, dominio_ou_ip: str, porta: int = 443) -> Dict[str, Any]:
        """Verifica a data de validade de certificados SSL/TLS."""
        comando = f"echo | openssl s_client -connect {dominio_ou_ip}:{porta} 2>/dev/null | openssl x509 -noout -dates"
        try:
            res = subprocess.run(comando, shell=True, capture_output=True, text=True)
            return {"target": dominio_ou_ip, "dados_ssl": res.stdout.strip()}
        except Exception as e:
            return {"target": dominio_ou_ip, "erro": str(e)}

    def verificar_pacotes_pendentes_seguranca(self) -> Dict[str, Any]:
        """Coleta pacotes do SO com atualizações de segurança pendentes (Ubuntu/Debian)."""
        comando = "apt-get --just-print upgrade 2>/dev/null | grep -i security"
        try:
            res = subprocess.run(comando, shell=True, capture_output=True, text=True)
            linhas = [l for l in res.stdout.split("\n") if l.strip()]
            return {"total_pacotes_seguranca_pendentes": len(linhas), "detalhes": linhas[:5]}
        except Exception as e:
            return {"erro": str(e)}

    def verificar_contas_e_chaves_ssh(self) -> Dict[str, Any]:
        """Audita validade de senhas e expiração de contas de usuário no Linux."""
        comando = "sudo chage -l root 2>/dev/null || cut -d: -f1,5 /etc/passwd"
        try:
            res = subprocess.run(comando, shell=True, capture_output=True, text=True)
            return {"status_contas": res.stdout.strip()[:200]}
        except Exception as e:
            return {"erro": str(e)}

    def executar_auditoria_completa(self) -> Dict[str, Any]:
        """Consolida a varredura proativa de conformidade do servidor."""
        return {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "atualizacoes_seguranca": self.verificar_pacotes_pendentes_seguranca(),
            "status_contas_ssh": self.verificar_contas_e_chaves_ssh()
        }