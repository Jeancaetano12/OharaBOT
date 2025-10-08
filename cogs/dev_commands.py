# cogs/dev_commands.py

import discord
from discord.ext import commands
import os
import sys
import json
import aiohttp
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
# --- CONFIGURAÇÃO DE SEGURANÇA ---
CARGO_DEV = int(os.getenv("CARGO_DEV"))
CHAT_LOG = int(os.getenv("CHAT_LOG"))
# -------------------------------

# --- VERIFICA ONDE FOI FEITO O COMANDO ---
async def check_dev_permissions(ctx):
    # Verifica o canal
    if ctx.channel.id != CHAT_LOG:
        chat_log = ctx.guild.get_channel(CHAT_LOG)
        if chat_log:
            await ctx.send(f"❌ Comando permitido apenas no canal {chat_log.mention}.", delete_after=10)
            logger.warning(f"❌ Usuário '{ctx.author}' tentou usar o comando '{ctx.command}' no canal '{ctx.channel}' do servidor '🚩 {ctx.guild}', mas não tem permissão.")
        else:
            await ctx.send("❌ Este comando só pode ser usado em um canal de controle específico.", delete_after=10)
            logger.error(f"<&@{CARGO_DEV}> ❌ Canal de controle com ID '{chat_log.id}' não encontrado no servidor '🚩 {ctx.guild}'.")
        return False
    # Verifica o cargo
    cargo_dev = ctx.guild.get_role(CARGO_DEV)
    # Verifica se o cargo existe no servidor
    if cargo_dev is None:
        await ctx.send("❌ O cargo de desenvolvedor não foi encontrado no servidor.", delete_after=10)
        logger.error(f"<&@{CARGO_DEV}> ❌ Cargo com ID '{CARGO_DEV}' não encontrado no servidor '🚩 {ctx.guild}'.")
        return False
    # Verifica se o autor tem o cargo
    if cargo_dev not in ctx.author.roles:
        await ctx.send("❌ Você não tem permissão para usar este comando.", delete_after=10)
        logger.warning(f"Usuário '{ctx.author}' tentou usar o comando '{ctx.command}' no servidor '🚩 {ctx.guild}', mas não tem o cargo necessário.")
        return False
    # Se passou por todas as verificações, retorna True
    return True
# ---------------------------------------

# --- COMANDOS PARA GERENCIAR O BOT ---
class Gerenciamento(commands.Cog):
    def __init__ (self, bot: commands.Bot):
        self.bot = bot
        self.caminho_arquivo = 'cogs_status.json'
    
    def _carregar_status(self):
        with open(self.caminho_arquivo, 'r', encoding='utf-8') as f:
            logger.info("\nCarregando dados do arquivo cogs_status.json.")
            return json.load(f)
        
    def _salvar_status(self, dados):
        with open(self.caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4)
# -----------------------------------

# --- RECARREGA UM COG ESPECIFICO ---
    @commands.command(name="load")
    @commands.check(check_dev_permissions)
    async def load_cog(self, ctx, cog_name: str):
        cog_name = cog_name.lower()

        status_data = self._carregar_status()

        if cog_name not in status_data:
            await ctx.send(f"❌ Cog `{cog_name}` não encontrado no arquivo de status.")
            return
        
        if status_data[cog_name]["status"] == "ativo":
            await ctx.send(f"⚠️ O Cog `{cog_name}` já está ativo.")
            return

        try:
            await self.bot.load_extension(f"cogs.{cog_name}")

            
            status_data[cog_name]["status"] = "ativo"
            status_data[cog_name]["motivo"] = None 
            self._salvar_status(status_data)

            await ctx.send(f"🟢 Cog `{cog_name}` foi ativado com sucesso!")
        except Exception as e:
            await ctx.send(f"❌ Erro ao carregar o cog `{cog_name}`:\n```py\n{e}\n```")
# ---------------------------------------
# --- DESCARREGA UM COG ESPECIFICO ---
    @commands.command(name="unload")
    @commands.check(check_dev_permissions)
    async def unload_cog(self, ctx, cog_name: str, *, motivo: str = None):
        cog_name = cog_name.lower()

        if cog_name == 'dev_commands':
            await ctx.send("❌ Por segurança, você não pode desativar este Cog")
            return
        
        if not motivo:
            await ctx.send("❌ Você precisa fornecer um motivo para desativar um Cog.")
            return
        
        status_data = self._carregar_status()

        if cog_name not in status_data:
            await ctx.send(f"❌ Cog `{cog_name}` não encontrado no arquivo de status.")
            return
        
        if status_data[cog_name]["status"] == "inativo":
            await ctx.send(f"⚠️ O Cog `{cog_name}` já está desativado.")
            return
            
        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")

            # Atualiza o estado no arquivo JSON
            status_data[cog_name]["status"] = "inativo"
            status_data[cog_name]["motivo"] = motivo
            self._salvar_status(status_data)

            await ctx.send(f"🔴 Cog `{cog_name}` foi desativado com sucesso.\n**Motivo:** {motivo}")
        except Exception as e:
            await ctx.send(f"❌ Erro ao descarregar o cog `{cog_name}`:\n```py\n{e}\n```")
# ---------------------------------------
# --- RECARREGA UM COG ESPECIFICO ---
    @commands.command(name="reload")
    @commands.check(check_dev_permissions)
    async def reload_cog(self, ctx, cog_name: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"✅ Cog '{cog_name}' foi recarregado com sucesso.")
        except Exception as e:
            logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao recarregar o cog '{cog_name}': {e}. Comando executado por :'{ctx.author}' no servidor '🚩 {ctx.guild}'.\n")
            await ctx.send(f"❌ Erro ao recarregar o cog '{cog_name}':\n```py\n{e}\n```")
# ---------------------------------------
# --- RECARREGA TODOS OS COGS ---
    @commands.command(name="hard_reload")
    @commands.check(check_dev_permissions)
    async def reload_all_cogs(self, ctx):
        # Guarda em um Array pra evitar spam
        reloaded_cogs = []
        failed_cogs = []

        cog_dev_commands = self.__class__.__name__ # Nome do cog atual
        await ctx.send("♻️ Recarregando todos os cogs...")

        # Recarrega todos os cogs, exceto o dev_commands
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                cog_name = filename[:-3]
                if cog_name == "dev_commands":
                    continue  # Pula o cog gerenciador para evitar problemas
                try:
                    await self.bot.reload_extension(f"cogs.{cog_name}")
                    reloaded_cogs.append(cog_name) # Adiciona ao array de recarregados
                except Exception as e:
                    failed_cogs.append(f"`{cog_name}`: `{e}`")
        # Mensagem final
        embed = discord.Embed(
            title="📝 Relatório de Recarregamento das Cogs",
            description="Recarregando o Cog **dev_commands** por último para evitar falhas.",
            color=discord.Color.orange()
        )

        if reloaded_cogs:
            embed.add_field(name="⚠️ Cogs recarregados:", value="\n".join(f"- `{cog}`" for cog in reloaded_cogs), inline=False)
        if failed_cogs:
            embed.add_field(name="❌ Cogs com Falha:", value="\n".join(failed_cogs), inline=False)
        await ctx.send(embed=embed)

        if not failed_cogs and reloaded_cogs:
            embed.color = discord.Color.green()
        elif failed_cogs:
            embed.color = discord.Color.red()

        await ctx.send(embed=embed) 
        
        # Recarrega o cog gerenciador por último
        try:
            await self.bot.reload_extension("cogs.dev_commands")
            await ctx.send("✅ Cog `dev_commands` recarregado por último com sucesso.")
        except Exception as e:
            logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao recarregar o cog 'dev_commands': {e}. Comando executado por:'{ctx.author}' no servidor '🚩 {ctx.guild}'.\n")
            await ctx.send(f"❌ Erro ao recarregar o cog `dev_commands`:\n```py\n{e}\n```")
# ---------------------------------------
# --- REINICIA O BOT ---
    @commands.command(name="restart")
    @commands.check(check_dev_permissions)
    async def restart_bot(self, ctx):
        try:
            logger.warning(f"Reiniciando o bot por comando de '{ctx.author}'\n")
            await ctx.send("♻️ Reiniciando o bot...")
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao reiniciar o bot: {e}. Comando executado por:'{ctx.author}' no servidor '🚩 {ctx.guild}'.\n")
            await ctx.send(f"❌ Erro ao reiniciar o bot:\n```py\n{e}\n```")
# ---------------------------------------

# --- COMANDOS PARA SINCRONIZAR BASE DE DADOS ---
class Syncronizacao(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.back_url = os.getenv("BACKEND_API_URL")
        self.back_key = os.getenv("BOT_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.back_key
        }

    @commands.command(name='sync_all')
    @commands.check(check_dev_permissions)
    async def sync_all_members(self, ctx):
        
        
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
                    "nickName": member.nick,
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

    @commands.command(name='sync_member')
    @commands.check(check_dev_permissions)
    async def sync_member(self, ctx, membro: discord.Member):
        """Uso: $sync <@menção do membro> ou $sync <ID do membro>"""

        feedback_message = await ctx.send(f"⚙️ Sincronizando dados para **{membro.display_name}**...", ephemeral=True)

        payload = {
            "discordId": str(membro.id),
            "username": membro.name,
            "nickName": membro.nick,
            "globalName": membro.global_name,
            "joinedAt": membro.joined_at.isoformat() if membro.joined_at else None,
            "avatarUrl": str(membro.display_avatar.url),
            "roles": [str(role.id) for role in membro.roles if role.name != "@everyone"]
        }

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(self.back_url, data=json.dumps([payload])) as response:
                    if response.status == 200:
                        await feedback_message.edit(content=f"✅ Dados de **{membro.display_name}** sincronizados com sucesso!")
                    else:
                        await feedback_message.edit(content=f"❌ **Erro ao sincronizar:** Problema interno.")
                        logger.error(f"Erro ao sincronizar '{membro.name}'. Status {response.status} - {await response.text()}")
        
        except aiohttp.ClientConnectionError as e:
            await feedback_message.edit(content="❌ **Erro de Conexão:** Não foi possível conectar ao backend.")
            logger.error(f"Erro de conexão ao tentar sincronizar '{membro.name}': {e}")
# ---------------------------------------

# --- SETUP COG ---
async def setup(bot):
    await bot.add_cog(Gerenciamento(bot))
    await bot.add_cog(Syncronizacao(bot))
# -------------------------------

