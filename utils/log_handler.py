import logging
import discord
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÃO DE SEGURANÇA ---
CHAT_LOG = int(os.getenv("CHAT_LOG"))
CARGO_DEV = int(os.getenv("CARGO_DEV"))
# -------------------------------

class DiscordLogHandler(logging.Handler):
    def __init__(self, bot: discord.Client, channel_id: int = CHAT_LOG):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id
        self.dev_role_id = CARGO_DEV

    def emit(self, record: logging.LogRecord):
        # Evita do bot enviar logs antes de iniciar
        if not self.bot.is_ready():
            return
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            print(f"Canal com ID {self.channel_id} não encontrado.")
            return

        log_entry = self.format(record)
        # Usa create_task para não bloquear o loop do Discord
        self.bot.loop.create_task(self.send_log_message(channel, log_entry, record.levelno))

    async def send_log_message(self, channel: discord.TextChannel, message: str, level: int):
        try:
            # Menciona o cargo Dev automaticamente para logs de nível ERROR ou superior
            mention = f"<@&{self.dev_role_id}> " if self.dev_role_id and level >= logging.ERROR else ""

            if len(message) > 1990:
                message = message[:1990]  # Evita estourar limite de 2000 caracteres do Discord

            await channel.send(f"{mention}```{message}```")
        except Exception as e:
            print(f"[DiscordLogHandler] Falha ao enviar log para o canal {self.channel_id}: {e}")
