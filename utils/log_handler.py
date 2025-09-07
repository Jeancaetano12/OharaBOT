import logging
import discord

class DiscordLogHandler(logging.Handler):
    def __init__(self, bot: discord.Client, channel_id: int):
        super().__init__()
        self.bot = bot
        self.channel_id = 1410316318917394433 # <<< Id do canal botlog
    def emit(self, record):
        # Evita do bot enviar logs antes de iniciar
        if not self.bot.is_ready():
            return
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            print(f"Canal com ID {self.channel_id} não encontrado.")
            return
        log_entry = self.format(record)
        self.bot.loop.create_task(self.send_log_message(channel, log_entry))
    
    async def send_log_message(self, channel: discord.TextChannel, message: str):
        if len(message) > 1990:
            message = message[:1990]
        await channel.send(f"```{message}```")