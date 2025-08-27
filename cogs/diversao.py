# cogs/diversao.py
from discord.ext import commands

# Todo Cog é uma classe que herda de commands.Cog
class Diversao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # O decorator @commands.command() cria um comando
    @commands.command()
    async def ping(self, ctx):
        # ctx (contexto) contém informações como o canal, autor, etc.
        await ctx.send('$Pong!')

# Esta função setup é essencial. O bot.py a usará para carregar o Cog.
async def setup(bot):
    await bot.add_cog(Diversao(bot))
