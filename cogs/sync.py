# cogs/sync.py
import discord
from discord.ext import commands
from discord import app_commands
import requests
import os
import logging

# Pega o logger para este arquivo específico
log = logging.getLogger(__name__)

# --- FUNÇÃO HELPER PARA ENVIAR DADOS PARA A API ---
def sync_member_to_api(member: discord.Member):
    """Envia os dados de um membro para o backend NestJS."""
    
    api_url = f"{os.getenv('API_BASE_URL')}/members/sync"
    api_key = os.getenv('API_SECRET_KEY')

    if not api_url or not api_key:
        log.error("Variáveis de ambiente API_BASE_URL ou API_SECRET_KEY não definidas.")
        return

    if member.bot:
        return

    payload = {
        "discordId": str(member.id),
        "username": member.name,
        "globalName": member.global_name,
        "avatarUrl": member.display_avatar.url,
        "joinedAt": member.joined_at.isoformat() if member.joined_at else None,
        "roles": [str(role.id) for role in member.roles]
    }

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    try:
        log.info(f"Sincronizando membro: {member.name} ({member.id})")
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status() 
        log.info(f"Membro {member.name} sincronizado com sucesso.")
    except requests.exceptions.RequestException as e:
        log.error(f"Falha ao sincronizar {member.name}: {e}")
        if e.response:
            log.error(f"Detalhes do erro da API: {e.response.text}")

# --- CLASSE DO COG ---
class SyncCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("Cog 'SyncCog' carregado.")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        log.info(f"Novo membro detectado: {member.name}")
        sync_member_to_api(member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        log.info(f"Membro atualizado: {after.name}")
        sync_member_to_api(after)

    @app_commands.command(name="sync-members", description="Sincroniza todos os membros com o banco de dados.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_members(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("Comando não utilizável em DMs.")
            return

        log.info("Iniciando sincronização em massa a pedido de um administrador.")
        
        all_members = await guild.fetch_members(limit=None).flatten()
        count = len(all_members)
        
        for member in all_members:
            sync_member_to_api(member)

        log.info(f"Sincronização em massa finalizada. {count} membros processados.")
        await interaction.followup.send(f"Sincronização concluída! {count} membros foram processados e enviados para a API.")

async def setup(bot: commands.Bot):
    await bot.add_cog(SyncCog(bot))
    await bot.tree.sync()