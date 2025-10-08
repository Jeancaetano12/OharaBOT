import discord
from discord.ext import commands 
import os  
from dotenv import load_dotenv  
import asyncio
import logging
import json
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
    # Verifica e carrega os cogs ativados
    with open("cogs_status.json", "r") as f:
        status_data = json.load(f)

    for cog_name, data in status_data.items():
        if data["status"] == "ativo":
            try:
                await bot.load_extension(f"cogs.{cog_name}")
                logging.getLogger("bot.py").info(f"Cog '{cog_name}' carregado (status: ativo).")
            except Exception as e:
                logging.getLogger("bot.py").error(f"Falha ao carregar o cog '{cog_name}': {e}")
        else:
            logging.getLogger("bot.py").warning(f"Cog '{cog_name}' não carregado (status: inativo).")
    

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

bot.run(TOKEN)