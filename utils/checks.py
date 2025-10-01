#utils/checks.py

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()
# --- CONFIGURAÇÃO DE SEGURANÇA ---
CARGO_DEV = int(os.getenv("CARGO_DEV"))
CHAT_LOG = int(os.getenv("CHAT_LOG"))
# -------------------------------

async def check_dev_permissions(ctx: commands.Context) -> bool:
    # Verifica o canal
    if ctx.channel.id != CHAT_LOG:
        chat_log = ctx.guild.get_channel(CHAT_LOG)
        if chat_log:
            await ctx.send(f"❌ Comando permitido apenas no canal {chat_log.mention}.", delete_after=10)
            logger.warning(f"Usuário '{ctx.author}' tentou usar '{ctx.command}' no canal errado.")
        else:
            await ctx.send("❌ Canal de controle não encontrado.", delete_after=10)
            logger.error(f"Canal de controle com ID '{CHAT_LOG}' não encontrado.")
        return False

    # Verifica o cargo
    cargo_dev = ctx.guild.get_role(CARGO_DEV)
    if not cargo_dev:
        await ctx.send("❌ O cargo de desenvolvedor não foi encontrado.", delete_after=10)
        logger.error(f"Cargo DEV com ID '{CARGO_DEV}' não encontrado.")
        return False
    
    if cargo_dev not in ctx.author.roles:
        await ctx.send("❌ Você não tem permissão para usar este comando.", delete_after=10)
        logger.warning(f"Usuário '{ctx.author}' sem cargo DEV tentou usar '{ctx.command}'.")
        return False
        
    return True