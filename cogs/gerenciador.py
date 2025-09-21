# cogs/gerenciador.py

import discord
from discord.ext import commands
import os
import sys
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

# --- CLASSE COG ---
class Gerenciador(commands.Cog):
    def __init__ (self, bot: commands.Bot):
        self.bot = bot

# --- RECARREGA UM COG ESPECIFICO ---
    @commands.command(name="load")
    @commands.check(check_dev_permissions)
    async def load_cog(self, ctx, cog_name: str):
        try:
            await self.bot.load_extension(f"cogs.{cog_name}")
            logger.info(f"Cog '{cog_name}' carregado por '{ctx.author}'")
            await ctx.send(f"✅ Cog '{cog_name}' foi carregado com sucesso.")
        except Exception as e:
            logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao carregar o cog '{cog_name}': {e}. Comando executado por :'{ctx.author}' no servidor '🚩 {ctx.guild}'.\n")
            await ctx.send(f"❌ Erro ao carregar o cog '{cog_name}':\n```py\n{e}\n```")
# ---------------------------------------
# --- DESCARREGA UM COG ESPECIFICO ---
    @commands.command(name="unload")
    @commands.check(check_dev_permissions)
    async def unload_cog(self, ctx, cog_name: str):
        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            await ctx.send(f"⚠️ Cog '{cog_name}' foi descarregado com sucesso.")
        except Exception as e:
            logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao descarregar o cog '{cog_name}': {e}. Comando executado por :'{ctx.author}' no servidor '🚩 {ctx.guild}'.\n")
            await ctx.send(f"❌ Erro ao descarregar o cog '{cog_name}':\n```py\n{e}\n```")
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

        cog_gerenciador = self.__class__.__name__ # Nome do cog atual
        await ctx.send("♻️ Recarregando todos os cogs...")
        logger.info(f"Recarregando todos os cogs por comando de '{ctx.author}' no servidor '🚩 {ctx.guild}'\n")

        # Recarrega todos os cogs, exceto o gerenciador
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                cog_name = filename[:-3]
                if cog_name == "gerenciador":
                    continue  # Pula o cog gerenciador para evitar problemas
                try:
                    await self.bot.reload_extension(f"cogs.{cog_name}")
                    reloaded_cogs.append(cog_name) # Adiciona ao array de recarregados
                except Exception as e:
                    logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao recarregar o cog '{cog_name}': {e}. Comando executado por :'{ctx.author}' no servidor '🚩 {ctx.guild}'.\n")
                    failed_cogs.append(f"`{cog_name}`: `{e}`")
        # Mensagem final
        embed = discord.Embed(
            title="📝 Relatório de Recarregamento das Cogs",
            description="Recarregando o Cog **gerenciador** por último para evitar falhas.",
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
            await self.bot.reload_extension("cogs.gerenciador")
            await ctx.send("✅ Cog `gerenciador` recarregado por último com sucesso.")
        except Exception as e:
            logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao recarregar o cog 'gerenciador': {e}. Comando executado por:'{ctx.author}' no servidor '🚩 {ctx.guild}'.\n")
            await ctx.send(f"❌ Erro ao recarregar o cog `gerenciador`:\n```py\n{e}\n```")
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
# --- SETUP COG ---
async def setup(bot):
    await bot.add_cog(Gerenciador(bot))
# -------------------------------

