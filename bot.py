import discord
import os  # Importe a biblioteca os
from dotenv import load_dotenv  # Importe a função

load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env
TOKEN = os.getenv("DISCORD_TOKEN")  # Obtém o token do bot

# As "intents" definem quais eventos seu bot irá escutar
intents = discord.Intents.default()
intents.message_content = True  # Permissão para ler o conteúdo das mensagens

# Cria o objeto do bot
bot = discord.Client(intents=intents)

# Evento chamado quando o bot está online e pronto
@bot.event
async def on_ready():
    print(f'Login efetuado como {bot.user}')
    print('Bot está pronto para ser usado!')
    print('-----------------------------')

# Evento chamado toda vez que uma mensagem é enviada em um canal
@bot.event
async def on_message(message):
    # Ignora mensagens enviadas pelo próprio bot
    if message.author == bot.user:
        return

    # Verifica se a mensagem começa com '!ping'
    if message.content.startswith('!ping'):
        # Envia 'Pong!' de volta no mesmo canal
        await message.channel.send('Pong!')

# Execute o bot usando o seu token secreto
# Lembre-se de NUNCA compartilhar este token com ninguém!
bot.run(TOKEN)