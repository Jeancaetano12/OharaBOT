#cogs/musica.py

import discord
from discord.ext import commands
import logging
import yt_dlp
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from functools import partial
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
    'noplaylist': False,
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
        self.tocando_agora = "" # Musica que esta tocando
        self.voice_client = None # Cliente de voz
        self.disconnect_task = None # Tarefa de desconexão automática
        self.manually_stopped = False
        self.ydl = yt_dlp.YoutubeDL(YDL_OPTIONS)

    
    async def buscar_info(self, musica: str, timeout: float = 120.0):
        loop = asyncio.get_event_loop()
        
        
        extract_func = partial(self.ydl.extract_info, musica, download=False)
        
        try:
            
            info = await asyncio.wait_for(loop.run_in_executor(None, extract_func), timeout=timeout)
            return info
        except asyncio.TimeoutError:
            raise Exception("Tempo esgotado ao buscar informações do vídeo.")
        except Exception as e:
            raise Exception(f"Erro ao buscar informações: {e}")
#---------------------------------
#--- EXTRAI URL DE AUDIO ---
    def _get_audio_url_from_info(self, info: dict):
   
        if not info:
            return None

        # Se info tem 'url' direto (muitos casos), usa
        if info.get('url'):
            return info['url']

        # Caso contrário, procura em 'formats' por um formato com audio
        formats = info.get('formats') or []
        # percorre do final pro começo (muitas vezes os melhores formatos ficam no fim)
        for fmt in reversed(formats):
            # pulamos formatos sem audio
            if fmt.get('acodec') and fmt.get('acodec') != 'none':
                if fmt.get('url'):
                    return fmt.get('url')
        return None
#---------------------------------
    #--- TOCA A PROXIMA MUSICA NA FILA ---
    def play_next(self, error=None):
        if error:
            logger.error(f"<&@{CARGO_DEV}> ❌ Erro ao tocar a música: {error}")
            return
        
        if self.manually_stopped:
            self.manually_stopped = False
            logger.warning("⚠️ Player parado manualmente")
            return
        
        if self.fila_musicas:
            proxima_musica = self.fila_musicas.pop(0)
            self.tocando_agora = proxima_musica['title']
            
            # Fonte de audio
            audio_source = discord.FFmpegPCMAudio(proxima_musica['url'], **FFMPEG_OPTIONS)
            self.voice_client.play(audio_source, after=lambda e: self.play_next(e))
            logger.info(f"🔊 Tocando agora: **{self.tocando_agora}**")
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
                logger.info(f"Bot conectado ao canal de voz '{canal_voz.name}' por '{ctx.author}' no servidor '🚩 {ctx.guild}'")
            else:
                await ctx.voice_client.move_to(canal_voz)
                await ctx.send(f"✅ Mudando para o canal de voz: {canal_voz.name}")
                logger.info(f"Bot movido para o canal de voz '{canal_voz.name}' por '{ctx.author}' no servidor '🚩 {ctx.guild}'")
        else:
            await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando.", delete_after=10)
            logger.warning(f"'{ctx.author}' tentou usar o comando 'join' sem estar em um canal de voz.")
#---------------------------------
#--- SAI DO CANAL DE VOZ ---
    @commands.command(name="sair", help="Faz o bot sair do canal de voz.")
    async def sair(self, ctx):
        if self.voice_client and self.voice_client.is_connected():
            canal = self.voice_client.channel.name

            # Limpa o estado interno do bot
            self.fila_musicas = []
            self.tocando_agora = ""

            if self.disconnect_task:
                self.disconnect_task.cancel()
                self.disconnect_task = None

            if self.voice_client.is_playing() or self.voice_client.is_paused():
                self.manually_stopped = True
                self.voice_client.stop()

            await self.voice_client.disconnect()
            # Por último, limpa a variável de estado
            self.voice_client = None

            await ctx.send(f"✅ Desconectado do canal de voz: `{canal}`", delete_after=10)
            logger.info(f"Bot desconectado do canal de voz '{canal}' por '{ctx.author}' no servidor '🚩 {ctx.guild}'")
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
            color=discord.Color.dark_purple()
        )
        if self.tocando_agora:
            embed.description = (f"▶️ **Tocando agora:**\n[{self.tocando_agora}]\n\n")
        else:
            embed.description = ("**Nenhuma música está tocando no momento.**\n\n")
        
        if self.fila_musicas:
            lista_musicas = ""
            for i, musica in enumerate(self.fila_musicas):
                lista_musicas += f"**{i + 1}.** {musica['title']}\n"
            embed.add_field(name="⏭️ Próximas na fila:", value=lista_musicas, inline=False)
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
            self.manually_stopped = False
            voice_client.stop()
            await ctx.send(f"⏭️ Música pulada: **{self.tocando_agora}**")
            logger.info(f"Música '{self.tocando_agora}' pulada por '{ctx.author}'")
        else:
            await ctx.send("🥱 Não estou tocando nenhuma música.", delete_after=10)
#---------------------------------
#--- TOCAR MUSICA ---
    @commands.command(name="p", aliases=["play"], help="Uso: $p <URL da playlist/música ou nome da música>")
    async def play (self, ctx, *, musica: str):
        if not self.voice_client or not self.voice_client.is_connected():
            if ctx.author.voice:
                await ctx.invoke(self.bot.get_command('entrar'))
            else:
                await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando.", delete_after=10)
                return
        
        self.voice_client = ctx.voice_client
        mensagem_feedback = await ctx.send(f"🔍 Procurando por `{musica}`...")

        try:
            logger.info(f"Buscando informações para: {musica}")
            info = await self.buscar_info(musica)
            logger.info(f"Informações obtidas com sucesso para: {musica}")
        except Exception as e:
            logger.error(f"<@&{CARGO_DEV}> ❌ Erro ao buscar o conteúdo: {e}")
            await mensagem_feedback.edit(content="❌ Não consegui encontrar o conteúdo solicitado.")
            return
        
        # Se for uma playlist (tem a chave 'entries')
        if 'entries' in info:
            entries = [e for e in info['entries'] if e]
            
            # Se a "playlist" tem apenas um item, trata como música única
            if len(entries) == 1:
                info = entries[0]
            else:
                playlist_titulo = info.get('title', 'Playlist')
                musicas_adicionadas = 0
                for entry in entries:
                    titulo = entry.get('title', 'Música sem título')
                    url = self._get_audio_url_from_info(entry)
                    if not url:
                        logger.warning(f"⚠️ URL de áudio não encontrada para a música '{titulo}'. Pulando.")
                        continue
                    self.fila_musicas.append({'title': titulo, 'url': url})
                    musicas_adicionadas += 1
                
                await mensagem_feedback.edit(content=f"🎶 Playlist `{playlist_titulo}` com **{musicas_adicionadas}** músicas adicionada à fila.")
                logger.info(f"✅ Adicionadas {musicas_adicionadas} músicas da playlist '{playlist_titulo}' à fila.")

                if not self.voice_client.is_playing() and not self.voice_client.is_paused():
                    self.play_next()
                return
        
        titulo = info.get('title', 'Música sem título')
        url = self._get_audio_url_from_info(info)
        if not url:
            logger.error(f"<@&{CARGO_DEV}> ❌ URL de áudio não encontrada para a música '{titulo}'.")
            await mensagem_feedback.edit(content="❌ Não consegui extrair o áudio da música solicitada")
            return
        
        song_info = {'title': titulo, 'url': url}

        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.fila_musicas.append(song_info)
            await mensagem_feedback.edit(content=f"🔊 `{titulo}` foi adicionada à fila.")
            logger.info(f"✅ '{titulo}' adicionada à fila por '{ctx.author}'")
            return
        else:
            if self.disconnect_task:
                self.disconnect_task.cancel()
                self.disconnect_task = None
        
        self.tocando_agora = titulo
        audio_source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        self.voice_client.play(audio_source, after=lambda e: self.play_next(e))
        await mensagem_feedback.edit(content=f"▶️ Tocando agora: **{titulo}**")
        logger.info(f"✅ Tocando agora '{titulo}' por '{ctx.author}'")
#---------------------------------
async def setup(bot):
    await bot.add_cog(Musica(bot))