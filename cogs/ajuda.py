# cgos/ajuda.py

import discord
from discord.ext import commands
import logging
from discord.ui import Button, View
from cogs.diversao import SRSILKSONG_ID

logger = logging.getLogger(__name__)
class Ajuda(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
# --- Comando ---
    @commands.command(name='ajuda')
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="🤖 Ajuda do OharaBot",
            description=(
                f"Olá {ctx.author.mention}! Estou em desenvolvimento e por enquanto posso te ajudar com essas informações:\n\n"
                f"• **Silksong** → Use `$silksong` para ver as estatísticas da jornada do <@{SRSILKSONG_ID}> no Hollow Knight Silksong.\n"
                f"• **Música** → Use `$musica` para ver os comandos relacionados à minha funcionalidade de tocar músicas.\n"
                f"• **Dev** → Use `$dev` para ver comandos voltados ao desenvolvimento.\n\n"
                f"Se a informação que você procura não está aqui, clique no botão abaixo para acessar a minha documentação!"
            ),
            color=discord.Color.dark_purple()  
        )

        view = View()
        view.add_item(Button(
            label="📚 Abrir Documentação",
            url="https://www.notion.so/Documenta-o-OharaBOT-28c068525a6e481ab511143eb1271055"
        ))

        await ctx.send(embed=embed, view=view)
        logger.info(f"Comando de ajuda solicitado por '{ctx.author}' no canal '{ctx.channel}' do servidor '🚩 {ctx.guild}'")

class AjudaMusica(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
#--- Comando ---
    @commands.command(name='musica')
    async def musica_help(self, ctx):
        embed = discord.Embed(
            title="🎵 Comandos de Música",
            description=(
                "Aqui está a lista de comandos disponíveis para controlar suas músicas.\n"
                "Certifique-se de estar em um **canal de voz** para usar os comandos de reprodução!"
            ),
            color=discord.Color.dark_purple()
        )

        embed.add_field(
            name="▶️ `$p <nome ou URL>`",
            value="Toca a música informada. Se já estiver tocando algo, adiciona à fila.",
            inline=False
        )
        embed.add_field(
            name="⏸️ `$pause`",
            value="Pausa a música que está tocando.",
            inline=False
        )
        embed.add_field(
            name="▶️ `$resume`",
            value="Retoma a música pausada.",
            inline=False
        )
        embed.add_field(
            name="⏭️ `$pular` ou `$skip`",
            value="Pula a música atual e toca a próxima da fila.",
            inline=False
        )
        embed.add_field(
            name="📜 `$fila`",
            value="Mostra a música que está tocando e as próximas da fila.",
            inline=False
        )
        embed.add_field(
            name="🧹 `$limpar_fila`",
            value="Esvazia completamente a fila de músicas.",
            inline=False
        )
        embed.add_field(
            name="🔊 `$entrar`",
            value="Faz o bot entrar no canal de voz em que você está.",
            inline=False
        )
        embed.add_field(
            name="🚪 `$sair`",
            value="Faz o bot sair do canal de voz e limpa a fila.",
            inline=False
        )

        embed.set_footer(text="Dica: Você pode usar links do YouTube ou apenas digitar o nome da música!")
        await ctx.send(embed=embed)
        logger.info(f"Comando de ajuda de música solicitado por '{ctx.author}' no canal '{ctx.channel}' do servidor '🚩 {ctx.guild}'")

class AjudaGerenciador(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
#--- Comando ---
    @commands.command(name="dev")
    async def gerenciador_help(self, ctx):
        embed = discord.Embed(
            title="🛠️ Comandos de Gerenciamento",
            description=(
                "Estes comandos são **restritos a desenvolvedores** e devem ser usados "
                f"no canal de controle configurado.\n\n"
                "Eles servem para carregar, descarregar, recarregar cogs e reiniciar o bot."
            ),
            color=discord.Color.orange()
        )

        embed.add_field(
            name="📥 `$load <nome>`",
            value="Carrega um cog específico. Exemplo: `$load musica`",
            inline=False
        )
        embed.add_field(
            name="📤 `$unload <nome>`",
            value="Descarrega um cog específico. Útil para testes.",
            inline=False
        )
        embed.add_field(
            name="♻️ `$reload <nome>`",
            value="Recarrega um cog específico sem precisar reiniciar o bot.",
            inline=False
        )
        embed.add_field(
            name="🔄 `$hard_reload`",
            value="Recarrega **todos os cogs** (exceto o gerenciador, que é recarregado por último).",
            inline=False
        )
        embed.add_field(
            name="🚀 `$restart`",
            value="Reinicia o bot completamente. Útil para aplicar mudanças maiores.",
            inline=False
        )

        embed.set_footer(text="Atenção: Use esses comandos apenas se você for autorizado!")
        await ctx.send(embed=embed)
        logger.info(f"Comando de ajuda de gerenciamento solicitado por '{ctx.author}' no canal '{ctx.channel}' do servidor '🚩 {ctx.guild}'")

async def setup(bot):
    await bot.add_cog(Ajuda(bot))
    await bot.add_cog(AjudaMusica(bot))
    await bot.add_cog(AjudaGerenciador(bot))
