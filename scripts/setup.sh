#!/bin/bash
# =========================================================
# 🛡️ VanguardSec AI — Script de Instalação no Cliente
# =========================================================

echo "[*] Atualizando pacotes do sistema..."
sudo apt-get update -y && sudo apt-get upgrade -y

echo "[*] Verificando instalação do Python 3 e dependências..."
sudo apt-get install -y python3 python3-pip python3-venv ufw

echo "[*] Configurando ambiente virtual Python..."
python3 -m venv venv
source venv/bin/activate

echo "[*] Instalando dependências do projeto..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[*] Inicializando banco de dados local..."
python3 scripts/init_db.py

echo "[✓] Instalação concluída com sucesso! Para rodar a solução, ative o venv e execute o orquestrador."