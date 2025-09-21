#cogs/musica.py

import discord
from discord.ext import commands
import logging
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO DE SEGURANÇA ---
CARGO_DEV = int(os.getenv("CARGO_DEV"))
# -------------------------------
#--- CONFIGURAÇÕES DO YDL E FFMPEG ---
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
# --- CLASSE COG ---
class Musica(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fila_musicas = [] # Fila de musicas
        self.tocando_agora = "" # Musica que esta tocando agora
        self.voice_client = None # Cliente de voz
        self.disconnect_task = None # Tarefa de desconexão automática
    #--- TOCA A PROXIMA MUSICA NA FILA ---
    def play_next(self, error=None):
        if error:
            logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao tocar a música: {error}")
            return
        if self.fila_musicas:
            proxima_musica = self.fila_musicas.pop(0)
            self.tocando_agora = proxima_musica['title']
            
            # Fonte de audio
            audio_source = discord.FFmpegPCMAudio(proxima_musica['url'], **FFMPEG_OPTIONS)
            self.voice_client.play(audio_source, after=lambda e: self.play_next(e))
            logger.info(f"Tocando agora: **{self.tocando_agora}**")
        else:
            self.tocando_agora = ""
            logger.info("Fila de músicas vazia.")
            self.disconnect_task = self.bot.loop.create_task(self._auto_disconnect())
            logger.info("Iniciada tarefa de desconexão automática em 60 segundos.")
#---------------------------------
#--- CRONOMETRO PARA DESCONECTAR APOS 1 MINUTOS ---
    async def _auto_disconnect(self):
        await asyncio.sleep(60)
        if self.voice_client and self.voice_client.is_connected() and not self.voice_client.is_playing() and not self.fila_musicas:
            logger.info("Desconectando por inatividade.")
            await self.voice_client.disconnect()
            self.voice_client = None

#--- COMANDO PARA PAUSAR A MUSICA ---
    @commands.command(name="pause", help="Pausa a música que está tocando.")
    async def pause(self, ctx):
        voice_client = ctx.voice_client

        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await ctx.send("⏸️ Música pausada.")
            logger.info(f"Música pausada por '{ctx.author}'")
        else:
            await ctx.send("❌ Não estou tocando nenhuma música.", delete_after=10)
#---------------------------------
#--- COMANDO PARA RETOMAR A MUSICA ---
    @commands.command(name="resume", help="Retoma a música que está pausada.")
    async def resume(self, ctx):
        voice_client = ctx.voice_client

        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await ctx.send("▶️ Música retomada.")
            logger.info(f"Música retomada por '{ctx.author}'")
        else:
            await ctx.send("❌ A música não está pausada.", delete_after=10)
#---------------------------------
#--- ENTRA NO CANAL DE VOZ ---
    @commands.command(name="entrar", help="Faz o bot entrar no canal de voz.")
    async def entrar(self, ctx):
        if ctx.author.voice:
            canal_voz = ctx.author.voice.channel
            if ctx.voice_client is None:
                self.voice_client = await canal_voz.connect()
                await ctx.send(f"✅ Conectado ao canal de voz: {canal_voz.name}")
                logger.info(f"Bot conectado ao canal de voz '{canal_voz.name}' por '{ctx.author}'")
            else:
                await ctx.voice_client.move_to(canal_voz)
                await ctx.send(f"✅ Mudando para o canal de voz: {canal_voz.name}")
                logger.info(f"Bot movido para o canal de voz '{canal_voz.name}' por '{ctx.author}'")
        else:
            await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando.", delete_after=10)
            logger.warning(f"'{ctx.author}' tentou usar o comando 'join' sem estar em um canal de voz.")
#---------------------------------
#--- SAI DO CANAL DE VOZ ---
    @commands.command(name="sair", help="Faz o bot sair do canal de voz.")
    async def sair(self, ctx):
        voice_client = ctx.voice_client

        if ctx.voice_client:
            self.fila_musicas = []
            self.tocando_agora = ""

            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
            self.voice_client = None

            await ctx.send(f"✅ Desconectando do canal de voz: {voice_client.channel.name}", delete_after=10)
            logger.info(f"Bot desconectado do canal de voz: '{ctx.voice_client.channel.name}' por '{ctx.author}'")
            await ctx.voice_client.disconnect()
        else:
            await ctx.send("❌ Não estou conectado a nenhum canal de voz.", delete_after=10)
#---------------------------------
#--- EXIBIR FILA DE MUSICAS ---
    @commands.command(name="fila", help="Mostra a fila de músicas.")
    async def fila(self, ctx):
        if not self.fila_musicas and not self.tocando_agora:
            await ctx.send("❌ A fila de músicas está vazia.", delete_after=10)
            return
        
        embed = discord.Embed(
            title="🔊 Fila de Músicas",
            color=discord.Color.blue()
        )
        if self.tocando_agora:
            embed.description = (f"**Tocando agora:**\n[{self.tocando_agora}]\n\n",)
        else:
            embed.description = (f"**Nenhuma música está tocando no momento.**\n\n")
        
        if self.fila_musicas:
            lista_musicas = ""
            for i, musica in enumerate(self.fila_musicas):
                lista_musicas += f"**{i + 1}.** {musica['title']}\n"
            embed.add_field(name="Próximas na fila:", value=lista_musicas, inline=False)
        await ctx.send(embed=embed)
        logger.info(f"Fila de músicas exibida para '{ctx.author}' no canal'{ctx.channel}' do servidor '🚩 {ctx.guild}'")
#---------------------------------
#--- LIMPA A FILA DE MUSICAS ---
    @commands.command(name="limpar_fila", help="Limpa a fila de músicas.")
    async def limpar_fila(self, ctx):
        if self.fila_musicas:
            self.fila_musicas.clear()
            await ctx.send("🧹 Fila de reprodução limpa!")
            logger.info(f"Fila de músicas limpa por '{ctx.author}'")
        else:
            await ctx.send("🥱 A fila de músicas já está vazia.", delete_after=10)
#---------------------------------
#--- PULA A MUSICA ATUAL ---
    @commands.command(name="pular", aliases=["skip"], help="Pula para a próxima música na fila.")
    async def pular(self, ctx):
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await ctx.send(f"🔊 Tocando agora: **{self.fila_musicas[0]['title']}**" if self.fila_musicas else "Fim da fila!\n"
                           f"⏭️ Música pulada: **{self.tocando_agora}**")
            logger.info(f"Música '{self.tocando_agora}' pulada por '{ctx.author}'")
        else:
            await ctx.send("🥱 Não estou tocando nenhuma música.", delete_after=10)
#--- TOCAR MUSICA ---
    @commands.command(name="p", help="Uso: $play <URL ou nome da música>")
    async def play (self, ctx, *, musica: str):
        if ctx.voice_client is None:
            if ctx.author.voice:
                entrar_cmd = self.bot.get_command('entrar')
                await ctx.invoke(entrar_cmd)
            else:
                await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando.", delete_after=10)
                return
        # Garante a referência mais recente do voice_client
        voice_client = ctx.voice_client
        # Faz a busca da musica
        mensagem_feedback = await ctx.send(f"🔍 Procurando por `{musica}...`")
        logger.info(f"'{ctx.author}' solicitou a música: {musica}")
        is_url = musica.startswith("http://") or musica.startswith("https://")
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                if is_url:
                    info = ydl.extract_info(musica, download=False)
                else:
                    info = ydl.extract_info(f"ytsearch:{musica}", download=False)['entries'][0]
                if 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]
                elif 'entries' in info and len(info['entries']) == 0:
                    raise Exception("Nenhum resultado encontrado.")
            except Exception as e:
                logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao buscar a música (URL: {is_url}): {e}")
                await ctx.send("❌ Não consegui encontrar a música. Tente novamente.", delete_after=10)
                return
        url = info['url']
        titulo = info['title']
        duracao = info.get('duration', 0)
        minutos, segundos = divmod(duracao, 60)
        duracao_formatada = f"{minutos}:{segundos:02d}" if duracao else "Desconhecida"

        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.fila_musicas.append({'title': titulo, 'url': url, 'duration': duracao_formatada})
            await mensagem_feedback.edit(content=f"🔊 `{titulo}` foi adicionada à fila.\n\n"
                                                f"❓ Use `$fila` para ver a lista de reprodução.")
            logger.info(f"Música '{titulo}' adicionada à fila por '{ctx.author}'")
        else:
            if self.disconnect_task:
                self.disconnect_task.cancel()
                self.disconnect_task = None
                logger.info("Tarefa de desconexão automática cancelada devido a nova reprodução.")
            self.tocando_agora = titulo
            audio_source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            self.voice_client.play(audio_source, after=lambda e: self.play_next(e))
            await mensagem_feedback.edit(content=f"▶️ Tocando agora: **{titulo}**")
            logger.info(f"Tocando agora '{titulo}' por '{ctx.author}'")
#---------------------------------
async def setup(bot):
    await bot.add_cog(Musica(bot))