import discord
from discord.ext import commands # Importa a extensão de comandos
import os  # Importe a biblioteca os
from dotenv import load_dotenv  # Importe a função load_dotenv
import asyncio

load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env
TOKEN = os.getenv("DISCORD_TOKEN")  # Obtém o token do bot

# As "intents" definem quais eventos seu bot irá escutar
intents = discord.Intents.default()
intents.message_content = True  # Permissão para ler o conteúdo das mensagens
intents.members = True # Adicionamos a intent de membros para o porteiro

# Cria o objeto do bot
bot = commands.Bot(command_prefix='$', intents=intents)

# Evento chamado quando o bot está online e pronto
@bot.event
async def on_ready():
    print(f'Login efetuado como {bot.user}')
    print('OharaBot está pronto para uso!')
    print('=================================')

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

# Inicia o bot
if __name__ == "__main__":
    asyncio.run(main())

# Chave de acesso guardada.
bot.run(TOKEN)