# cogs/diversao.py

from discord.ext import commands
import json
import os
import logging

logger = logging.getLogger(__name__)

SRSILKSONG_ID = 402082403268427778
# Todo Cog é uma classe que herda de commands.Cog
class Diversao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.caminho_arquivo = 'contagem.json'  # Caminho para o arquivo JSON

    # --- Funções Auxiliares para ler/escrever no arquivo ---
    def _carregar_dados(self):
        if not os.path.exists(self.caminho_arquivo):
            logger.warning("Arquivo contagem.json não encontrado. Criando um novo arquivo com dados padrão.\n")
            dados_padrao = {
                "silksong_deaths": 0,
                "silksong_bosses": 0 
            }
            with open(self.caminho_arquivo, 'w') as f:
                logger.info("Criando novo arquivo contagem.json com dados padrão.")
                json.dump(dados_padrao, f, indent=4)
                logger.info("Arquivo contagem.json criado com sucesso.\n")
            return dados_padrao
        with open(self.caminho_arquivo, 'r') as f:
            logger.info("\nCarregando dados do arquivo contagem.json.")
            return json.load(f)

    def _salvar_dados(self, dados):
        with open(self.caminho_arquivo, 'w') as f:
            logger.info("Salvando dados no arquivo contagem.json.")
            json.dump(dados, f, indent=4)

    # --- Comandos ---

    @commands.command()
    async def ping(self, ctx):
        # ctx (contexto) contém informações como o canal, autor, etc.
        await ctx.send('Pong!')
    
    @commands.command(name="silksong")
    async def _silksong(self, ctx, acao: str = None):
        dados = self._carregar_dados()
    
        contagem_mortes = dados["silksong_deaths"]
        contagem_bosses = dados["silksong_bosses"]

        mensagem = (
                    f"Até agora, o <@{SRSILKSONG_ID}> acumulou:\n"
                    f"💀 Mortes: **{contagem_mortes}**\n"
                    f"👑 Bosses Derrotados: **{contagem_bosses}**\n"
                    f"Provavelmente mais mortes que bosses né? kkkjkjkjk\n"
                    f"\n⚠️ Não é mais possível registrar mortes ou bosses. A jornada do Sr.Silksong acabou!\n"
                )
        await ctx.send(mensagem)
        logger.info(f"Comando silksong solicitado por '{ctx.author}' no canal '{ctx.channel}' do servidor '🚩 {ctx.guild}'")

async def setup(bot):
    await bot.add_cog(Diversao(bot))
