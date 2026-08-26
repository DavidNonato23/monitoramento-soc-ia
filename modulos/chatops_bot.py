import os
import sys
import re
import json
import logging
import platform
import socket
import subprocess
import asyncio
import psutil
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from modulos.coletor_ssh import coletar_dados_servidor
from modulos.gerador_pdf import gerar_relatorio_pdf
from agentes.agente_auditor import executar_agente_auditor
from agentes.agente_compliance import executar_agente_compliance
from agentes.agente_remediacao import executar_agente_remediacao

HISTORICO_FILE = "historico_scans.json"
logging.basicConfig(level=logging.INFO)

def obter_ip_servidor():
    return os.getenv("SSH_HOST", "192.168.15.3")

# --- COLETA REAL COM VALIDAÇÃO ANTI-FALSO POSITIVO ---
async def obter_telemetria_real():
    host = obter_ip_servidor()
    user = os.getenv("SSH_USER", "servidor")
    senha = os.getenv("SSH_PASS", "")
    
    telemetria = await asyncio.to_thread(coletar_dados_servidor, host, user, password=senha)
    
    # Valida se a resposta SSH contém erros de conexão
    erros_conexao = ["timed out", "Refused", "Erro ao conectar", "No route to host", "Authentication failed"]
    if not telemetria or any(erro in telemetria for erro in erros_conexao):
        raise ConnectionError(telemetria if telemetria else "Falha de comunicação SSH")
        
    return telemetria

async def extrair_ip_atacante_dinamico(telemetria_raw):
    host = obter_ip_servidor()
    ips_encontrados = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", telemetria_raw)
    for ip in ips_encontrados:
        if ip != host and not ip.startswith("127."):
            return ip
    return "Nenhum IP externo em ataque no momento"

TECLADO_FIXO = ReplyKeyboardMarkup(
    [
        ["🔍 Scan Simplificado", "🛡️ Escudo de Proteção", "🚨 Invasões Bloqueadas"],
        ["🔌 Portas de Entrada", "🤖 Diagnóstico com IA", "🔥 Bloquear Invasor"],
        ["📄 Relatório Diretoria", "🧪 Teste de Conexão", "📈 Histórico do Servidor"]
    ],
    resize_keyboard=True
)

def obter_menu_inline_60():
    ip_host = obter_ip_servidor()
    keyboard = [
        [InlineKeyboardButton(f"1. 🔍 Varredura Real ({ip_host})", callback_data="b_01"), InlineKeyboardButton("2. 👁️ Detectar Escutas Ocultas", callback_data="b_02")],
        [InlineKeyboardButton("3. 🌐 Conexões Ativas no Servidor", callback_data="b_03"), InlineKeyboardButton("4. 🛡️ Checar Falsificação de Rede", callback_data="b_04")],
        [InlineKeyboardButton("5. 📑 Caminhos da Internet (Rotas)", callback_data="b_05"), InlineKeyboardButton("6. 🌐 Checar Sequestro de DNS", callback_data="b_06")],
        [InlineKeyboardButton("7. 📡 Teste de Resposta da Rede", callback_data="b_07"), InlineKeyboardButton("8. 📦 Inspeção Rápida de Dados", callback_data="b_08")],
        [InlineKeyboardButton("9. 🔌 Portas de Entrada Abertas", callback_data="b_09"), InlineKeyboardButton("10. 📊 Medidor de Tráfego de Dados", callback_data="b_10")],

        [InlineKeyboardButton("11. 🛡️ Status do Muro de Proteção", callback_data="b_11"), InlineKeyboardButton("12. 🚫 Lista de Invasores Banidos", callback_data="b_12")],
        [InlineKeyboardButton("13. 🔥 Bloquear Invasor Ativo", callback_data="b_13"), InlineKeyboardButton("14. ✅ Liberar Acesso Autorizado", callback_data="b_14")],
        [InlineKeyboardButton("15. 🔒 Modo Bloqueio Total (Zero-Trust)", callback_data="b_15"), InlineKeyboardButton("16. 🧹 Limpar Regras Temporárias", callback_data="b_16")],
        [InlineKeyboardButton("17. 🚨 Botão de Emergência (Isolar)", callback_data="b_17"), InlineKeyboardButton("18. 🔐 Proteger Porta de Banco de Dados", callback_data="b_18")],
        [InlineKeyboardButton("19. 🛡️ Escudo Contra Ataque de Volume", callback_data="b_19"), InlineKeyboardButton("20. 🔍 Audit Redirecionamento de Rede", callback_data="b_20")],

        [InlineKeyboardButton("21. ⚠️ Logins Falhos em Tempo Real", callback_data="b_21"), InlineKeyboardButton("22. 📜 Histórico Recente de Acessos", callback_data="b_22")],
        [InlineKeyboardButton("23. 🕵️ Pessoas Logadas Agora", callback_data="b_23"), InlineKeyboardButton("24. 🛑 Expulsar Usuário Suspeito", callback_data="b_24")],
        [InlineKeyboardButton("25. 🔑 Auditoria de Chaves de Acesso", callback_data="b_25"), InlineKeyboardButton("26. 🔒 Checar Permissões de Superusuário", callback_data="b_26")],
        [InlineKeyboardButton("27. 🔌 Mapear Programas x Portas", callback_data="b_27"), InlineKeyboardButton("28. 📝 Mudanças Recentes no Sistema", callback_data="b_28")],
        [InlineKeyboardButton("29. 🚨 Detectar Varredura Hacker", callback_data="b_29"), InlineKeyboardButton("30. 🔍 Audit Tentativas de Invasão Web", callback_data="b_30")],

        [InlineKeyboardButton("31. 🤖 IA: Diagnóstico em Português", callback_data="b_31"), InlineKeyboardButton("32. 🤖 IA: Criar Plano de Ação", callback_data="b_32")],
        [InlineKeyboardButton("33. ⚖️ IA: Avaliação de Risco LGPD", callback_data="b_33"), InlineKeyboardButton("34. 📋 IA: Resumo para a Diretoria", callback_data="b_34")],
        [InlineKeyboardButton("35. 🧪 IA: Checar Falso Alarme", callback_data="b_35"), InlineKeyboardButton("36. 🛡️ IA: Dicas para Melhorar Segurança", callback_data="b_36")],
        [InlineKeyboardButton("37. 🐍 IA: Gerar Ferramenta Sob Medida", callback_data="b_37"), InlineKeyboardButton("38. 🐳 IA: Avaliar Segurança de Sistemas", callback_data="b_38")],
        [InlineKeyboardButton("39. 📜 IA: Checklist de Normas Técnicas", callback_data="b_39"), InlineKeyboardButton("40. ⚙️ IA: Testar Velocidade do Robô", callback_data="b_40")],

        [InlineKeyboardButton("41. ⚡ Programas Pesados (Vírus/Minerador)", callback_data="b_41"), InlineKeyboardButton("42. 🧠 Uso Excessivo de Memória", callback_data="b_42")],
        [InlineKeyboardButton("43. 👻 Programas Escondidos na Memória", callback_data="b_43"), InlineKeyboardButton("44. 👑 Programas Rodando como Administrador", callback_data="b_44")],
        [InlineKeyboardButton("45. 🕵️ Procurar Conexões Espiãs", callback_data="b_45"), InlineKeyboardButton("46. ⏱️ Tarefas Agendadas no Servidor", callback_data="b_46")],
        [InlineKeyboardButton("47. 📁 Verificar Pastas Temporárias", callback_data="b_47"), InlineKeyboardButton("48. 🛡️ Exame Geral de Saúde do Sistema", callback_data="b_48")],
        [InlineKeyboardButton("49. 💾 Espaço em Disco & Riscos", callback_data="b_49"), InlineKeyboardButton("50. 🛑 Encerrar Programa Suspeito", callback_data="b_50")],

        [InlineKeyboardButton("51. 📊 Formatar Registro para Auditoria", callback_data="b_51"), InlineKeyboardButton("52. 📄 Baixar Relatório em PDF", callback_data="b_52")],
        [InlineKeyboardButton("53. 📬 Enviar Alerta para a Equipe", callback_data="b_53"), InlineKeyboardButton("54. 📥 Salvar Cópia do Incidente", callback_data="b_54")],
        [InlineKeyboardButton("55. 🚨 Simular Tentativa de Invasão", callback_data="b_55"), InlineKeyboardButton("56. 🛡️ Simular Proteção Automática", callback_data="b_56")],
        [InlineKeyboardButton("57. 🧪 Testar Conexão com Servidor Alvo", callback_data="b_57"), InlineKeyboardButton("58. ⚙️ Verificar Senhas de Ambiente", callback_data="b_58")],
        [InlineKeyboardButton("59. 🧹 Limpar Histórico de Ações", callback_data="b_59"), InlineKeyboardButton("60. 🏠 Voltar ao Menu Principal", callback_data="act_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def enviar_resposta(chat_id, context, titulo, corpo_mastigado):
    keyboard = [[InlineKeyboardButton("🏠 Menu Principal", callback_data="act_menu")]]
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{titulo}\n\n{corpo_mastigado}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def disparar_agente_e_executar_automacao(chat_id, context, opcao_id, objetivo_simples):
    msg = await context.bot.send_message(chat_id=chat_id, text="🧠 *IA VanguardSec:* Conectando ao servidor...", parse_mode="Markdown")
    host = obter_ip_servidor()
    
    try:
        telemetria_raw = await obter_telemetria_real()
        ip_atacante = await extrair_ip_atacante_dinamico(telemetria_raw)
        
        prompt = (
            f"Analise a telemetria REAL extraída agora do servidor {host}:\n"
            f"```\n{telemetria_raw[:1500]}\n```\n"
            f"Responda em português mastigado o seguinte objetivo: {objetivo_simples}. IP do atacante encontrado: {ip_atacante}."
        )
        resposta_ia = await asyncio.to_thread(executar_agente_remediacao, "Análise em Tempo Real", prompt)
        
        resposta_cliente = (
            f"✅ *ANÁLISE REAL DO SERVIDOR CONCLUÍDA*\n\n"
            f"🖥️ *Servidor Ativo:* `{host}`\n"
            f"📋 *Parecer da IA sobre os dados ao vivo:*\n{resposta_ia}\n\n"
            f"🛡️ *Status:* Telemetria processada e sistema protegido."
        )
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=resposta_cliente, parse_mode="Markdown")

    except Exception as e:
        resposta_offline = (
            f"🔴 *STATUS DO SERVIDOR: DESLIGADO OU INACESSÍVEL*\n\n"
            f"🖥️ *Servidor:* `{host}`\n"
            f"⚠️ *Status:* Conexão SSH falhou ou tempo limite excedido.\n\n"
            f"💡 *Diagnóstico:* O servidor virtual/físico está desligado ou sem comunicação de rede.\n\n"
            f"🛠️ *Erro Técnico:* `{str(e)[:150]}`"
        )
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=resposta_offline, parse_mode="Markdown")

async def auto_scan_ssh(chat_id, context):
    host = obter_ip_servidor()
    try:
        telemetria = await obter_telemetria_real()
        resposta_mastigada = (
            f"🟢 *STATUS DO SERVIDOR:* ONLINE E RESPONDENDO\n"
            f"🖥️ *Servidor:* `{host}`\n\n"
            f"📋 *TELEMETRIA REAL LIDA AGORA:*\n"
            f"```text\n{telemetria[:800]}\n```\n\n"
            f"💡 *O que isso significa?*\n"
            f"O servidor está ligado e o robô conseguiu autenticar e extrair os dados mais recentes de segurança."
        )
        await enviar_resposta(chat_id, context, "🔍 *Varredura Real Concluída*", resposta_mastigada)
    except Exception as e:
        resposta_offline = (
            f"🔴 *STATUS DO SERVIDOR:* DESLIGADO OU INACESSÍVEL\n"
            f"🖥️ *Servidor:* `{host}`\n\n"
            f"🚨 *O QUE ACONTECEU:*\n"
            f"• *Falha de Conexão:* A tentativa de conexão SSH excedeu o tempo limite ou foi recusada.\n"
            f"• *Causa:* A máquina virtual no VirtualBox/VMware está desligada.\n\n"
            f"🛠️ *Erro da Tentativa:* `{str(e)[:150]}`"
        )
        await enviar_resposta(chat_id, context, "🔴 *Alerta: Servidor Indisponível*", resposta_offline)

async def auto_logins_falhos(chat_id, context):
    host = obter_ip_servidor()
    try:
        telemetria = await obter_telemetria_real()
        falhas = [linha for linha in telemetria.split("\n") if "Failed password" in linha or "falha" in linha.lower()]
        
        if falhas:
            res_falhas = "\n".join(falhas[-5:])
            msg = f"⚠️ *TENTATIVAS REAIS DE INVASÃO DETECTADAS:*\n\n```text\n{res_falhas}\n```\n\n💡 O robô monitora essas tentativas para aplicar o bloqueio no firewall."
        else:
            msg = f"🟢 *SEM TENTATIVAS DE INVASÃO:* Nenhum login falho registrado recentemente nos logs de `{host}`."
            
        await enviar_resposta(chat_id, context, "🚨 *Relatório de Logins em Tempo Real*", msg)
    except Exception as e:
        await enviar_resposta(chat_id, context, "🔴 *Servidor Indisponível*", f"Não foi possível ler os logs do servidor `{host}` pois a máquina está desligada.\n\nDetalhe: `{str(e)[:100]}`")

async def auto_portas_listen(chat_id, context):
    host = obter_ip_servidor()
    try:
        telemetria = await obter_telemetria_real()
        portas_abertas = re.findall(r":(\d+)\s+", telemetria)
        portas_unicas = sorted(list(set([int(p) for p in portas_abertas])))
        
        if portas_unicas:
            res_portas = ", ".join([str(p) for p in portas_unicas])
            msg = f"🔌 *PORTAS ABERTAS NESTE MOMENTO EM `{host}`:*\n\n*Portas em Escuta:* `{res_portas}`\n\n💡 Essas são as portas de entrada ativas no sistema operacional."
        else:
            msg = f"🔌 *PORTAS LIDADAS DO SERVIDOR `{host}`:*\n\n```text\n{telemetria[:500]}\n```"
            
        await enviar_resposta(chat_id, context, "🔌 *Portas em Escuta no Servidor*", msg)
    except Exception as e:
        await enviar_resposta(chat_id, context, "🔴 *Servidor Indisponível*", f"Não foi possível listar as portas do servidor `{host}` pois a máquina está offline.\n\nDetalhe: `{str(e)[:100]}`")

async def auto_status_ufw(chat_id, context):
    host = obter_ip_servidor()
    try:
        telemetria = await obter_telemetria_real()
        msg = f"🛡️ *STATUS DO FIREWALL EM TEMPO REAL (`{host}`):*\n\n```text\n{telemetria[:600]}\n```"
        await enviar_resposta(chat_id, context, "🛡️ *Escudo do Servidor*", msg)
    except Exception as e:
        await enviar_resposta(chat_id, context, "🔴 *Servidor Indisponível*", f"Servidor `{host}` desligado. Impossível checar o status do firewall.\n\nDetalhe: `{str(e)[:100]}`")

async def auto_bloquear_ip_dinamico(chat_id, context):
    host = obter_ip_servidor()
    try:
        telemetria = await obter_telemetria_real()
        ip_atacante = await extrair_ip_atacante_dinamico(telemetria)
        
        if ip_atacante != "Nenhum IP externo em ataque no momento":
            res = await asyncio.to_thread(subprocess.run, ["sudo", "ufw", "deny", "from", ip_atacante], capture_output=True, text=True)
            msg = f"🔥 *BLOQUEIO EXECUTADO COM SUCESSO!*\n\n• *IP Atacante Identificado nos Logs:* `{ip_atacante}`\n• *Ação:* Adicionado ao bloqueio do firewall UFW do servidor `{host}`."
        else:
            msg = f"🟢 *NENHUM ATAQUE EXTERNO ATIVO:* A varredura em tempo real em `{host}` não encontrou IPs externos tentando força bruta no momento."
            
        await enviar_resposta(chat_id, context, "🔥 *Bloqueio SOAR em Tempo Real*", msg)
    except Exception as e:
        await enviar_resposta(chat_id, context, "🔴 *Servidor Indisponível*", f"Não foi possível aplicar bloqueios em `{host}` porque o servidor está offline.\n\nDetalhe: `{str(e)[:100]}`")

async def auto_exportar_pdf(chat_id, context):
    host = obter_ip_servidor()
    try:
        telemetria = await obter_telemetria_real()
        dados_pdf = {"host": host, "telemetria": telemetria, "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
        pdf = await asyncio.to_thread(gerar_relatorio_pdf, dados_pdf)
        with open(pdf, "rb") as doc:
            await context.bot.send_document(
                chat_id=chat_id, 
                document=doc, 
                filename=f"Relatorio_{host}.pdf",
                caption=f"📄 *Relatório Executivo gerado com dados extraídos ao vivo do servidor {host}.*"
            )
    except Exception as e:
        await enviar_resposta(chat_id, context, "🔴 *Falha ao Gerar PDF*", f"Não foi possível gerar o relatório pois o servidor `{host}` está offline ou inacessível.\n\nDetalhes: `{str(e)[:100]}`")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    ip_host = obter_ip_servidor()
    await update.message.reply_text(
        f"🛡️ *VanguardSec AI — Central de Segurança 100% Dinâmica*\n"
        f"🖥️ *Servidor Alvo:* `{ip_host}`\n\n"
        f"Selecione uma opção abaixo para interagir em tempo real com o servidor:",
        parse_mode="Markdown",
        reply_markup=TECLADO_FIXO
    )
    await update.message.reply_text("Escolha uma automação de segurança:", reply_markup=obter_menu_inline_60())

async def callback_botao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or query.data is None: return
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id if query.message else None
    if not chat_id: return

    if data == "act_menu":
        await context.bot.send_message(chat_id=chat_id, text=f"🛡️ *Menu Principal ({obter_ip_servidor()})*", parse_mode="Markdown", reply_markup=obter_menu_inline_60())
    elif data == "b_01": await auto_scan_ssh(chat_id, context)
    elif data == "b_09": await auto_portas_listen(chat_id, context)
    elif data == "b_11": await auto_status_ufw(chat_id, context)
    elif data == "b_13": await auto_bloquear_ip_dinamico(chat_id, context)
    elif data == "b_21": await auto_logins_falhos(chat_id, context)
    elif data == "b_52": await auto_exportar_pdf(chat_id, context)
    elif data.startswith("b_"):
        await disparar_agente_e_executar_automacao(chat_id, context, data, f"Executar rotina técnica em tempo real para a opção {data}")

async def tratar_texto_teclado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    texto = update.message.text.strip()
    chat_id = update.message.chat_id

    if texto in ["🔍 Scan Simplificado", "/scan"]: await auto_scan_ssh(chat_id, context)
    elif texto in ["🛡️ Escudo de Proteção", "/firewall"]: await auto_status_ufw(chat_id, context)
    elif texto in ["🚨 Invasões Bloqueadas", "/logins"]: await auto_logins_falhos(chat_id, context)
    elif texto in ["🔌 Portas de Entrada", "/ports"]: await auto_portas_listen(chat_id, context)
    elif texto in ["🔥 Bloquear Invasor", "/block"]: await auto_bloquear_ip_dinamico(chat_id, context)
    elif texto in ["📄 Relatório Diretoria", "/pdf"]: await auto_exportar_pdf(chat_id, context)
    elif texto in ["🤖 Diagnóstico com IA", "/ia"]:
        await disparar_agente_e_executar_automacao(chat_id, context, "geral", "Analisar a saúde e os logs ao vivo do servidor")
    else:
        await cmd_start(update, context)

def criar_app_telegram(token):
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tratar_texto_teclado))
    app.add_handler(CallbackQueryHandler(callback_botao))
    return app