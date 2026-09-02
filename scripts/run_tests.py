import os
import subprocess
import sys

def rodar_bateria_testes():
    print("=========================================================")
    print("🧪 EXECUTANDO SUÍTE DE TESTES DA SOLUÇÃO VANGUARDSEC")
    print("=========================================================\n")

    if os.path.exists("test_prompts.py"):
        print("[*] Rodando testes de benchmark e temperatura de prompts...")
        subprocess.run([sys.executable, "test_prompts.py"])
    else:
        print("[!] Arquivo test_prompts.py não encontrado na raiz.")

if __name__ == "__main__":
    rodar_bateria_testes()