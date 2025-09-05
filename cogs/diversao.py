# cogs/diversao.py
from discord.ext import commands
import json
import os

# Todo Cog é uma classe que herda de commands.Cog
class Diversao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.caminho_arquivo = 'contagem.json'  # Caminho para o arquivo JSON

    # --- Funções Auxiliares para ler/escrever no arquivo ---
    def _carregar_dados(self):
        if not os.path.exists(self.caminho_arquivo):
            print("[DEBUG] Arquivo contagem.json não encontrado. Criando um novo arquivo com dados padrão.\n")
            dados_padrao = {
                "silksong_deaths": 0,
                "silksong_bosses": 0 
            }
            with open(self.caminho_arquivo, 'w') as f:
                print("[DEBUG] Criando novo arquivo contagem.json com dados padrão.")
                json.dump(dados_padrao, f, indent=4)
                print("[DEBUG] Arquivo contagem.json criado com sucesso.\n")
            return dados_padrao
        with open(self.caminho_arquivo, 'r') as f:
            print("\n[DEBUG] Carregando dados do arquivo contagem.json.")
            return json.load(f)

    def _salvar_dados(self, dados):
        with open(self.caminho_arquivo, 'w') as f:
            print("[DEBUG] Salvando dados no arquivo contagem.json.")
            json.dump(dados, f, indent=4)

    # --- Comandos ---

    @commands.command()
    async def ping(self, ctx):
        # ctx (contexto) contém informações como o canal, autor, etc.
        await ctx.send('Pong!')
    
    @commands.command(name="silksong")
    async def _silksong(self, ctx, acao: str = None):
        dados = self._carregar_dados()
        print(f"[DEBUG] Dados carregados: {dados}")
    
        if acao and acao.lower() == "+m":
            dados["silksong_deaths"] += 1
            self._salvar_dados(dados)
            contagem_bosses = dados["silksong_deaths"]
            await ctx.send(f"Vish, parece que o Sr. Silksong pereceu mais uma vez... \n"
                           f"Ele morreu um total de: **{contagem_bosses}** 💀\n "
                           f"Vai me avisando kkjkkjk")
            print(f"[ACAO] Contagem de mortes atualizada: {contagem_bosses}")
        elif acao and acao.lower() == "+b":
            dados["silksong_bosses"] += 1
            self._salvar_dados(dados)
            contagem_bosses = dados["silksong_bosses"]
            await ctx.send(f"Eita? Parece que o nosso jogador aposentou mais um kkkjkjkjkkj\n"
                           f"Bosses derrotados: **{contagem_bosses}** 👑\n"
                           f"Vai me avisando kkjkkjk")
            print(f"[ACAO] Contagem de bosses atualizada: {contagem_bosses}")
        else:
            contagem_mortes = dados["silksong_deaths"]
            contagem_bosses = dados["silksong_bosses"]

            mensagem = (
                        f"Até agora, o Sr. Silksong acumulou:\n"
                        f"💀 Mortes: **{contagem_mortes}**\n"
                        f"👑 Bosses Derrotados: **{contagem_bosses}**\n"
                        f"Provavelmente mais mortes que bosses né? kkkjkjkjk\n"
                        f"\nUse `$silksong +m` para adicionar uma morte ou `$silksong +b` para adicionar um boss derrotado."
                    )
            await ctx.send(mensagem)
            print(f"[ACAO] Exibindo contagens - Mortes: {contagem_mortes}, Bosses: {contagem_bosses}")

# Esta função setup é essencial. O bot.py a usará para carregar o Cog.
async def setup(bot):
    await bot.add_cog(Diversao(bot))
