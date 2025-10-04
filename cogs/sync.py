# cogs/sync.py
import discord
from discord.ext import commands
import aiohttp
import requests
import os
import json
from dotenv import load_dotenv
import logging
from utils.checks import check_dev_permissions
# Pega o logger para este arquivo específico
logger = logging.getLogger(__name__)

load_dotenv()

class Sync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.back_url = os.getenv("BACKEND_API_URL")
        self.back_key = os.getenv("BOT_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.back_key
        }

    @commands.command(name='sync all')
    async def sync_all_members(self, ctx):
        if not await check_dev_permissions(ctx):
            return
        
        all_members = [m for m in ctx.guild.members if not m.bot]
        total_members = len(all_members)
        
        feedback_message = await ctx.send(f"⚙️ **Iniciando sincronização...** `0 de {total_members}` membros processados.")

        members_to_sync = ctx.guild.members
        batch = []
        batch_size = 50 # Enviando lotes de 50
        total_synced = 0
        total_failed = 0

        async with aiohttp.ClientSession(headers=self.headers) as session:
            for member in members_to_sync:
                if member.bot:
                    continue

                payload = {
                    "discordId": str(member.id),
                    "username": member.name,
                    "globalName": member.global_name,
                    "avatarUrl": str(member.display_avatar.url),
                    "joinedAt": member.joined_at.isoformat() if member.joined_at else None,
                    "roles": [str(role.id) for role in member.roles if role.name != "@everyone"]
                }
                batch.append(payload)

                if len(batch) >= batch_size:
                    try:
                        async with session.post(self.back_url, data=json.dumps(batch)) as response:
                            if response.status == 200:
                                total_synced += len(batch)
                                await feedback_message.edit(content=f"⚙️ **Sincronizando...** `{total_synced} de {total_members}` membros processados.")
                            else:
                                total_failed += len(batch)
                                logger.warning(f"❌ Erro ao enviar lote: Status {response.status} - {await response.text()}")
                        batch = [] # Limpa o lote para o proximo ciclo
                    except aiohttp.ClientConnectorError:
                        return await ctx.send("❌ **Erro de Conexão:** Não foi possível conectar ao backend. A sincronização foi cancelada.")
            if batch:
                try:
                    async with session.post(self.back_url, data=json.dumps(batch)) as response:
                        if response.status == 200:
                            total_synced += len(batch)
                        else:
                            total_failed += len(batch)
                            logger.warning(f"❌ Erro ao enviar último lote: Status {response.status} - {await response.text()}")
                except aiohttp.ClientConnectionError:
                    return await ctx.send("❌ **Erro de Conexão:** Falha ao enviar o último lote.")
                
        await feedback_message.edit(content=f"✅ **Sincronização concluída!**\n- Membros sincronizados: `{total_synced}`\n- Lotes com falha: `{total_failed}`")

async def setup(bot):
    await bot.add_cog(Sync(bot))