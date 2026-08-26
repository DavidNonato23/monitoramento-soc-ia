@echo off
TITLE VanguardSec AI — Boot System
COLOR 0A

echo =======================================================================
echo                 VANGUARDSEC AI - INICIANDO SISTEMA
echo =======================================================================
echo.

:: 1. Verifica se o ambiente virtual existe
if not exist "venv\Scripts\activate.bat" (
    echo [!] Ambiente virtual nao encontrado. Criando venv...
    python -m venv venv
    echo [+] Ambiente virtual criado com sucesso!
    echo.
)

:: 2. Ativa o ambiente virtual
echo [*] Ativando ambiente virtual (venv)...
call venv\Scripts\activate.bat

:: 3. Verifica e instala dependencias do requirements.txt
if exist "requirements.txt" (
    echo [*] Verificando dependencias em requirements.txt...
    pip install -r requirements.txt --quiet
)

echo.
echo =======================================================================
echo              SISTEMA PRONTO - INICIANDO DASHBOARD SOC
echo =======================================================================
echo.

:: 4. Executa a aplicacao Streamlit
streamlit run app.py

pause