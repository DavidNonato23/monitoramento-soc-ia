import os
import sqlite3

DATA_DIR = "./data"
DB_PATH = os.path.join(DATA_DIR, "vanguard_sec.db")

def inicializar_banco():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            severidade TEXT,
            tipo_evento TEXT,
            status_sistema TEXT,
            ip_origem TEXT,
            parecer_soc TEXT,
            compliance_lgpd TEXT,
            acao_soar_gerada TEXT,
            analise_trafego TEXT,
            modelo_ia_utilizado TEXT,
            relatorio_normativo TEXT,
            log_raw TEXT,
            origem TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"[✓] Banco de dados inicializado com sucesso em: {DB_PATH}")

if __name__ == "__main__":
    inicializar_banco()