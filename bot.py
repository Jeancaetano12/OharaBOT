import discord
from discord.ext import commands 
import os  
from dotenv import load_dotenv  
import asyncio
import logging
from utils.log_handler import DiscordLogHandler

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

log_root = logging.getLogger()

load_dotenv() 
TOKEN = os.getenv("DISCORD_TOKEN") 
CHAT_LOG = int(os.getenv("CHAT_LOG"))
# As "intents" definem quais eventos seu bot irá escutar
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 


bot = commands.Bot(command_prefix='$', intents=intents)

# Evento chamado quando o bot está online e pronto
@bot.event
async def on_ready():
    print(f'\nLogin efetuado como {bot.user}')
    print('LEIA O README ANTES DE USAR O BOT!')
    print('=================================\n')
    if not any(isinstance(h, DiscordLogHandler) for h in log_root.handlers):
        discord_handler = DiscordLogHandler(bot, CHAT_LOG)

        discord_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        discord_handler.setFormatter(formatter)

        log_root.addHandler(discord_handler)
        logging.getLogger("bot.py").info("Handler de log do Discord conectado.\n"
                                                  "OharaBOT pronto para uso!")

async def load_cogs():
    # Carrega todos os Cogs da pasta cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            #remove o .py do nome do arquivo
            cog_name = f'cogs.{filename[:-3]}'
            try:
                await bot.load_extension(cog_name)
                print(f'Cog {cog_name} carregado com sucesso.')
            except Exception as e:
                print(f'Falha em carregar o cog {cog_name}: {e}')

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

bot.run(TOKEN)