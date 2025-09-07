import discord
from discord.ext import commands
import os
import sys
import logging

logger = logging.getLogger(__name__)
# --- CONFIGURAÇÃO DE SEGURANÇA ---
ID_CANAL_BOTLOG = 1410316318917394433 # <<< ID do Canal botlog
ID_CARGO_PERMITIDO = 1410347600602726430 # <<< Somente Devs tem acesso a esse comando
# -------------------------------

# --- VERIFICA ONDE FOI FEITO O COMANDO ---
async def check_dev_permissions(ctx):
    # Verifica o canal
    if ctx.channel.id != ID_CANAL_BOTLOG:
        canal_botlog = ctx.guild.get_channel(ID_CANAL_BOTLOG)
        if canal_botlog:
            await ctx.send(f"❌ Comando permitido apenas no canal {canal_botlog.mention}.", delete_after=10)
            logger.warning(f"Usuário '{ctx.author}' tentou usar o comando '{ctx.command}' no canal '{ctx.channel}', mas não tem permissão.")
        else:
            await ctx.send("❌ Este comando só pode ser usado em um canal de controle específico.", delete_after=10)
            logger.error(f"Canal de controle com ID '{ID_CANAL_BOTLOG}' não encontrado no servidor.")
        return False
    # Verifica o cargo
    cargo_dev = ctx.guild.get_role(ID_CARGO_PERMITIDO)
    # Verifica se o cargo existe no servidor
    if cargo_dev is None:
        await ctx.send("❌ O cargo de desenvolvedor não foi encontrado no servidor.", delete_after=10)
        logger.error(f"Cargo com ID '{ID_CARGO_PERMITIDO}' não encontrado no servidor.")
        return False
    # Verifica se o autor tem o cargo
    if cargo_dev not in ctx.author.roles:
        await ctx.send("❌ Você não tem permissão para usar este comando.", delete_after=10)
        logger.warning(f"Usuário '{ctx.author}' tentou usar o comando '{ctx.command}', mas não tem o cargo necessário.")
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
            logger.error(f"\n Erro ao carregar o cog '{cog_name}': {e}. Comando executado por :'{ctx.author}'.\n")
            await ctx.send(f"❌ Erro ao carregar o cog '{cog_name}':\n```py\n{e}\n```")
# ---------------------------------------
# --- DESCARREGA UM COG ESPECIFICO ---
    @commands.command(name="unload")
    @commands.check(check_dev_permissions)
    async def unload_cog(self, ctx, cog_name: str):
        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            logger.info(f"\n Cog '{cog_name}' descarregado por '{ctx.author}'\n")
            await ctx.send(f"⚠️ Cog '{cog_name}' foi descarregado com sucesso.")
        except Exception as e:
            logger.error(f"\n Erro ao descarregar o cog '{cog_name}': {e}. Comando executado por :'{ctx.author}'.\n")
            await ctx.send(f"❌ Erro ao descarregar o cog '{cog_name}':\n```py\n{e}\n```")
# ---------------------------------------
# --- RECARREGA UM COG ESPECIFICO ---
    @commands.command(name="reload")
    @commands.check(check_dev_permissions)
    async def reload_cog(self, ctx, cog_name: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            logger.info(f"Cog '{cog_name}' recarregado por '{ctx.author}'")
            await ctx.send(f"✅ Cog '{cog_name}' foi recarregado com sucesso.")
        except Exception as e:
            logger.error(f"\n Erro ao recarregar o cog '{cog_name}': {e}. Comando executado por :'{ctx.author}'.\n")
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
        logger.info(f"\n Recarregando todos os cogs por comando de '{ctx.author}'\n")

        # Recarrega todos os cogs, exceto o gerenciador
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                cog_name = filename[:-3]
                if cog_name == "gerenciador":
                    continue  # Pula o cog gerenciador para evitar problemas
                try:
                    await self.bot.reload_extension(f"cogs.{cog_name}")
                    logger.info(f"Cog '{cog_name}' recarregado por '{ctx.author}'")
                    reloaded_cogs.append(cog_name) # Adiciona ao array de recarregados
                except Exception as e:
                    logger.error(f"\n Erro ao recarregar o cog '{cog_name}': {e}. Comando executado por :'{ctx.author}'.\n")
                    failed_cogs.append(f"`{cog_name}`: `{e}`")
        # Mensagem final
        embed = discord.Embed(
            title="📝 Relatório de Recarregamento das Cogs",
            description="Recarregando o Cog **gerenciador** por último para evitar falhas.",
            color=discord.Color.orange()
        )

        if reloaded_cogs:
            embed.add_field(name="⚠️ Cogs Sendo recarregaods:", value="\n".join(f"- `{cog}`" for cog in reloaded_cogs), inline=False)
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
            logger.info("Cog 'gerenciador' recarregado com sucesso.")
            await ctx.send("✅ Cog `gerenciador` recarregado com sucesso.")
        except Exception as e:
            logger.error(f"\n Erro ao recarregar o cog 'gerenciador': {e}. Comando executado por :'{ctx.author}'.\n")
            await ctx.send(f"❌ Erro ao recarregar o cog `gerenciador`:\n```py\n{e}\n```")
# ---------------------------------------
# --- REINICIA O BOT ---
    @commands.command(name="restart")
    @commands.check(check_dev_permissions)
    async def restart_bot(self, ctx):
        try:
            logger.warning(f"\n Reiniciando o bot por comando de '{ctx.author}'\n")
            await ctx.send("♻️ Reiniciando o bot...")
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            logger.error(f"\n Erro ao reiniciar o bot: {e}. Comando executado por :'{ctx.author}'.\n")
            await ctx.send(f"❌ Erro ao reiniciar o bot:\n```py\n{e}\n```")
# ---------------------------------------
# --- SETUP COG ---
async def setup(bot):
    await bot.add_cog(Gerenciador(bot))
# -------------------------------

