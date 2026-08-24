import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ContextTypes
from modulos.coletor_ssh import aplicar_remediacao_linux

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "8457053029"))
SSH_USER = os.getenv("SSH_TARGET_USER", "servidor")
SSH_PASS = os.getenv("SSH_TARGET_PASS", "")

async def enviar_alerta_incidente(bot_token: str, chat_id: str, servidor: str, ip_atacante: str, tipo_ataque: str):
    """Dispara a mensagem interativa com botões de ação para o Telegram."""
    if not bot_token:
        return

    app = Application.builder().token(bot_token).build()

    mensagem = (
        f"🚨 *VANGUARDSEC AI — ALERTA CRÍTICO DE SOC*\n\n"
        f"🖥️ *Servidor Alvo:* `{servidor}`\n"
        f"⚠️ *Anomalia Detectada:* {tipo_ataque}\n"
        f"🌐 *IP Origem:* `{ip_atacante}`\n\n"
        f"Seleção de resposta rápida via Playbook SOAR:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🚫 Bloquear IP (UFW)", callback_data=f"BLOCK_IP|{servidor}|{ip_atacante}"),
            InlineKeyboardButton("⚡ Encerrar Processo", callback_data=f"KILL_PROC|{servidor}|kswapd0"),
        ],
        [
            InlineKeyboardButton("🚨 Isolar Servidor", callback_data=f"QUARANTINE|{servidor}|all"),
            InlineKeyboardButton("👁️ Ignorar / Arquivar", callback_data=f"DISMISS|{servidor}|none"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    async with app:
        await app.bot.send_message(
            chat_id=chat_id,
            text=mensagem,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com o clique no botão do Telegram e executa o comando no servidor."""
    query = update.callback_query

    # Guard Clause para o Pylance: Garante que 'query' e 'query.from_user' não são None
    if not query or not query.from_user:
        return

    user_id = query.from_user.id

    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        await query.answer("❌ Acesso Negado! Usuário não autorizado no SOC.", show_alert=True)
        return

    await query.answer("⚡ Executando ação de remediação...")

    data_text = query.data or ""
    dados = data_text.split("|")
    acao = dados[0] if len(dados) > 0 else ""
    servidor_raw = dados[1] if len(dados) > 1 else ""
    parametro = dados[2] if len(dados) > 2 else ""

    ip_alvo = servidor_raw.split(" ")[0]
    usuario_nome = query.from_user.username or query.from_user.first_name

    if acao == "BLOCK_IP":
        comando = f"sudo ufw deny from {parametro} to any"
        status_msg = f"🚫 *Bloqueio do IP {parametro} no UFW*"
    elif acao == "KILL_PROC":
        comando = f"sudo killall -9 {parametro}"
        status_msg = f"⚡ *Encerramento do Processo {parametro}*"
    elif acao == "QUARANTINE":
        comando = "sudo ufw default deny incoming"
        status_msg = f"🚨 *Quarentena Ativada no Servidor {ip_alvo}*"
    elif acao == "DISMISS":
        await query.edit_message_text(f"ℹ️ *Alerta marcado como analisado por @{usuario_nome}.*")
        return
    else:
        comando = ""
        status_msg = "⚠️ Ação desconhecida."

    if comando and SSH_PASS:
        sucesso, log_out = aplicar_remediacao_linux(
            hostname=ip_alvo,
            username=SSH_USER,
            password=SSH_PASS,
            key_file=None,
            script=comando
        )
        
        if sucesso:
            resposta_final = (
                f"{status_msg}\n\n"
                f"✅ *Ação Executada no Servidor Remoto!*\n"
                f"🖥️ *Host:* `{ip_alvo}`\n"
                f"👤 *Autorizado por:* @{usuario_nome}\n"
                f"💻 *Comando Enviado:* `{comando}`"
            )
        else:
            resposta_final = f"❌ *Falha na Execução SSH:* {log_out}"
    else:
        resposta_final = (
            f"{status_msg}\n\n"
            f"✅ *Ação Mapeada em Modo Simulação!*\n"
            f"👤 *Autorizado por:* @{usuario_nome}\n"
            f"⚙️ *Comando:* `{comando}`"
        )

    await query.edit_message_text(text=resposta_final, parse_mode="Markdown")