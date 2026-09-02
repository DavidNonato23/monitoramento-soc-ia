import os
import json
import time
import requests
from typing import Dict, Any

# Configurações de execução
OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# Evento telemétrico real de teste
LOG_ATAQUE_REAL = "Failed password for root from 185.220.101.5 port 42110 ssh2"

def carregar_prompt_json(caminho_arquivo: str) -> Dict[str, Any]:
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        return json.load(f)

def testar_agente_avancado(config_prompt: Dict[str, Any]) -> Dict[str, Any]:
    # Montagem do Prompt unificando Role Playing, CoT e Few-Shot
    prompt_estruturado = (
        f"ROLE: {config_prompt['role_playing']}\n"
        f"INSTRUÇÃO: {config_prompt['system_prompt']}\n\n"
        f"CADEIA DE RACIOCÍNIO ESPERADA (Chain-of-Thought):\n" + 
        "\n".join(config_prompt.get("cadeia_de_raciocinio_cot", [])) + "\n\n"
        f"EXEMPLO (Few-Shot):\n"
        f"Input: {json.dumps(config_prompt['few_shot_examples'][0]['input'])}\n"
        f"Output Esperado: {json.dumps(config_prompt['few_shot_examples'][0]['output'])}\n\n"
        f"LOG REAL PARA ANÁLISE: '{LOG_ATAQUE_REAL}'\n\n"
        f"Esquema JSON Obrigatório: {json.dumps(config_prompt['schema_resposta'])}\n"
        "RESPONDA EXCLUSIVAMENTE COM O OBJETO JSON BRUTO:"
    )

    payload = {
        "model": MODELO,
        "prompt": prompt_estruturado,
        "stream": False,
        "options": {
            "temperature": config_prompt["parametros"]["temperatura"],
            "top_p": config_prompt["parametros"]["top_p"]
        }
    }

    inicio = time.time()
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        tempo_total = round(time.time() - inicio, 2)
        
        if response.status_code == 200:
            dados = response.json()
            texto_resposta = dados.get("response", "").strip()
            
            # Validação do JSON retornado
            json_parsed = None
            status_json = "INVÁLIDO"
            try:
                json_parsed = json.loads(texto_resposta)
                status_json = "VÁLIDO"
            except json.JSONDecodeError:
                # Tenta extrair JSON em caso de formatação extra
                if "{" in texto_resposta and "}" in texto_resposta:
                    inicio_j = texto_resposta.find("{")
                    fim_j = texto_resposta.rfind("}") + 1
                    try:
                        json_parsed = json.loads(texto_resposta[inicio_j:fim_j])
                        status_json = "VÁLIDO (EXTRAÍDO)"
                    except Exception:
                        pass

            return {
                "agente": config_prompt["agente"],
                "tempo_segundos": tempo_total,
                "prompt_tokens": dados.get("prompt_eval_count", 0),
                "completion_tokens": dados.get("eval_count", 0),
                "status_json": status_json,
                "resposta_objeto": json_parsed,
                "resposta_raw": texto_resposta
            }
        else:
            return {"agente": config_prompt["agente"], "erro": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"agente": config_prompt["agente"], "erro": str(e)}

if __name__ == "__main__":
    print("=========================================================================")
    print("🧪 BATERIA DE TESTES: ROLE PLAYING, FEW-SHOT & CHAIN-OF-THOUGHT (v3.0)")
    print("=========================================================================\n")

    prompts_para_testar = [
        "prompts/tier1_soc.json",
        "prompts/tier2_compliance.json",
        "prompts/tier3_soar.json"
    ]

    for caminho in prompts_para_testar:
        if not os.path.exists(caminho):
            print(f"⚠️ Arquivo não encontrado: {caminho}")
            continue

        cfg = carregar_prompt_json(caminho)
        print(f"🎯 Testando Agente: {cfg['agente']} (Versão {cfg.get('versao', '1.0')})")
        print(f"   Técnicas: {', '.join(cfg.get('tecnicas_aplicadas', []))}")
        print(f"   Temperatura: {cfg['parametros']['temperatura']} | Top_P: {cfg['parametros']['top_p']}")

        res = testar_agente_avancado(cfg)

        if "erro" not in res:
            print(f"   ⏱️ Latência: {res['tempo_segundos']}s | Validação JSON: [{res['status_json']}]")
            print(f"   📊 Consumo: {res['prompt_tokens']} tokens (In) / {res['completion_tokens']} tokens (Out)")
            
            if res["resposta_objeto"]:
                print("\n   🧠 Cadeia de Raciocínio (Chain-of-Thought):")
                print(f"      {res['resposta_objeto'].get('raciocinio_cot', 'N/A')}")
                print("\n   📦 Saída Estruturada:")
                print(f"      {json.dumps(res['resposta_objeto'], indent=6, ensure_ascii=False)}")
            else:
                print(f"   ⚠️ Raw Output: {res['resposta_raw'][:150]}...")
        else:
            print(f"   ❌ Falha no Teste: {res['erro']}")

        print("\n" + "-" * 73 + "\n")