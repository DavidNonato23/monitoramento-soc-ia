import paramiko
import time
from typing import Optional, Generator

class SSHLogCollector:
    def __init__(
        self, 
        host: str, 
        port: int, 
        user: str, 
        key_path: Optional[str] = None, 
        password: Optional[str] = None
    ):
        self.host: str = host
        self.port: int = port
        self.user: str = user
        self.key_path: Optional[str] = key_path
        self.password: Optional[str] = password
        self.client: Optional[paramiko.SSHClient] = None

    def conectar(self) -> None:
        """Estabelece conexão SSH real com o servidor alvo."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if self.key_path:
            client.connect(
                self.host, 
                port=self.port, 
                username=self.user, 
                key_filename=self.key_path, 
                timeout=10
            )
        else:
            client.connect(
                self.host, 
                port=self.port, 
                username=self.user, 
                password=self.password, 
                timeout=10
            )
        
        self.client = client

    def monitorar_logs_em_tempo_real(self, caminho_log: str = "/var/log/auth.log") -> Generator[str, None, None]:
        """
        Executa 'tail -f' no servidor remoto e produz eventos de log reais continuamente.
        """
        if self.client is None:
            self.conectar()

        # Verificação explicita para satisfazer a verificação de tipos do Pylance
        if self.client is None:
            raise RuntimeError("Falha ao estabelecer conexão SSH com o servidor alvo.")

        command = f"sudo tail -n 0 -f {caminho_log}"
        stdin, stdout, stderr = self.client.exec_command(command, get_pty=True)

        for line in iter(stdout.readline, ""):
            log_linha = line.strip()
            if log_linha and ("Failed password" in log_linha or "Invalid user" in log_linha):
                yield log_linha

    def fechar(self) -> None:
        """Encerra a conexão SSH com o servidor."""
        if self.client is not None:
            self.client.close()
            self.client = None