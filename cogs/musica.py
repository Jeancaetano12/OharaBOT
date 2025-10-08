# cogs/musica.py

import discord
from discord.ext import commands
import logging
import yt_dlp
import asyncio
from functools import partial

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES ---
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn'
}

# --- CLASSE DA COG ---
class Musica(commands.Cog):
    """Funcionalidade de tocar música"""
    def __init__(self, bot):
        self.bot = bot
        self.filas = {}
        self.tocando_agora = {}
        self.voice_clients = {}
        self.ydl = yt_dlp.YoutubeDL(YDL_OPTIONS)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Verifica se quem mudou de estado foi o próprio bot
        if member.id == self.bot.user.id and before.channel is not None and after.channel is None:
            guild_id = member.guild.id
            logger.info(f"Fui desconectado do canal '{before.channel.name}' no servidor '{member.guild.name}'. Limpando a fila...")

            # Limpa os recursos
            if guild_id in self.voice_clients:
                self.voice_clients.pop(guild_id)
            if guild_id in self.filas:
                self.filas.pop(guild_id)
            if guild_id in self.tocando_agora:
                self.tocando_agora.pop(guild_id, None)

    def get_audio_url(self, info: dict):
        if 'url' in info:
            return info['url']
        for fmt in reversed(info.get('formats', [])):
            if fmt.get('acodec') and fmt.get('acodec') != 'none' and fmt.get('url'):
                return fmt.get('url')
        return None

    async def play_next(self, ctx):
        guild_id = ctx.guild.id
        voice_client = self.voice_clients.get(guild_id)

        if not voice_client or not self.filas.get(guild_id):
            self.tocando_agora.pop(guild_id, None)
            return

        proximo_item = self.filas[guild_id][0]

        try:
            loop = asyncio.get_event_loop()
            extract_func = partial(self.ydl.extract_info, proximo_item['query'], download=False)
            info = await loop.run_in_executor(None, extract_func)

            audio_url = self.get_audio_url(info)
            if not audio_url:
                await ctx.send(f"❌ Não foi possível obter uma URL de áudio para **{proximo_item['title']}**. Pulando.")
                self.filas[guild_id].pop(0)
                return await self.play_next(ctx)

            self.filas[guild_id].pop(0)
            self.tocando_agora[guild_id] = proximo_item

            try:
                audio_source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
            except Exception as e:
                logger.error(f"ERRO CRÍTICO ao criar FFmpegPCMAudio: {e}")
                await ctx.send(f"❌ Erro crítico ao tentar carregar a música com FFmpeg. Veja o console para detalhes.")
                return await self.play_next(ctx)

            def after_callback(error):
                if error:
                    logger.error(f"Ocorreu um erro no player: {error}")
                coro = self.play_next(ctx)
                asyncio.run_coroutine_threadsafe(coro, self.bot.loop)

            voice_client.play(audio_source, after=after_callback)

            await ctx.send(f"▶️ Tocando agora: **{proximo_item['title']}**")

        except Exception as e:
            logger.error(f"Erro ao processar a música {proximo_item['title']}: {e}")
            await ctx.send(f"❌ Ocorreu um erro geral ao tentar tocar **{proximo_item['title']}**. Pulando.")
            if guild_id in self.filas and self.filas[guild_id]:
                self.filas[guild_id].pop(0)
            await self.play_next(ctx)

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("Você precisa estar em um canal de voz!")

        guild_id = ctx.guild.id
        voice_client = self.voice_clients.get(guild_id)
        if not voice_client:
            try:
                voice_client = await ctx.author.voice.channel.connect()
                self.voice_clients[guild_id] = voice_client
            except Exception as e:
                logger.error(f"Erro ao conectar ao canal de voz: {e}")
                return await ctx.send("❌ Não consegui me conectar ao seu canal de voz.")

        if guild_id not in self.filas:
            self.filas[guild_id] = []

        msg = await ctx.send(f"🔎 Procurando por: `{query}`...")
        
        ydl_opts_local = YDL_OPTIONS.copy()

        
        if "list=" in query and ("youtube.com/" in query or "youtu.be/" in query):
            ydl_opts_local['extract_flat'] = 'in_playlist'
            logger.info("Playlist detectada, usando modo de extração rápida.")

        try:
            loop = asyncio.get_event_loop()
            
            with yt_dlp.YoutubeDL(ydl_opts_local) as ydl:
                extract_func = partial(ydl.extract_info, query, download=False)
                info = await loop.run_in_executor(None, extract_func)

        except Exception as e:
            logger.error(f"Erro ao buscar com yt-dlp: {e}")
            return await msg.edit(content=f"❌ Erro ao buscar: Tente novamente ou use outro link.")

        
        if 'entries' in info:
            playlist_title = info.get('title', 'Playlist desconhecida')
            await msg.edit(content=f"🎶 Playlist **{playlist_title}** encontrada! Adicionando músicas à fila...")

            for entry in info['entries']:
                if entry:
                    self.filas[guild_id].append({
                        'title': entry.get('title', 'Desconhecido'),
                        
                        'query': entry.get('url', entry.get('webpage_url'))
                    })
            
            await ctx.send(f"✅ **{len(info['entries'])}** músicas da playlist **{playlist_title}** foram adicionadas à fila!")
        
        
        else:
            self.filas[guild_id].append({
                'title': info.get('title', 'Desconhecido'),
                'query': info.get('webpage_url', query)
            })
            await msg.edit(content=f"✅ Adicionado à fila: **{info.get('title')}**")

        
        if not voice_client.is_playing():
            await self.play_next(ctx)

    @commands.command(name="stop", aliases=["parar", "sair"])
    async def stop(self, ctx):
        guild_id = ctx.guild.id
        voice_client = self.voice_clients.get(guild_id)
        if not voice_client:
            return await ctx.send("Não estou conectado a um canal de voz.")

        self.filas[guild_id] = []
        self.tocando_agora.pop(guild_id, None)
        voice_client.stop()
        await voice_client.disconnect()
        self.voice_clients.pop(guild_id, None)
        await ctx.send("⏹️ Fila limpa e bot desconectado.")

    @commands.command(name="skip", aliases=["pular"])
    async def skip(self, ctx):
        voice_client = self.voice_clients.get(ctx.guild.id)
        if voice_client and voice_client.is_playing():
            voice_client.stop()  # O 'after' da função play() vai chamar a próxima música
            await ctx.send("⏭️ Música pulada!")
        else:
            await ctx.send("Não há nada tocando para pular.")

    @commands.command(name="pause")
    async def pause(self, ctx):
        voice_client = self.voice_clients.get(ctx.guild.id)
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await ctx.send("⏸️ Música pausada.")
        else:
            await ctx.send("Não há música tocando para pausar.")

    @commands.command(name="resume", aliases=["continuar"])
    async def resume(self, ctx):
        voice_client = self.voice_clients.get(ctx.guild.id)
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await ctx.send("▶️ Música retomada.")
        else:
            await ctx.send("A música não está pausada.")

    @commands.command(name="queue", aliases=["fila", "q"])
    async def queue(self, ctx):
        guild_id = ctx.guild.id
        if not self.filas.get(guild_id) and not self.tocando_agora.get(guild_id):
            return await ctx.send("A fila está vazia.")

        embed = discord.Embed(title="🎶 Fila de Músicas", color=discord.Color.blue())

        if self.tocando_agora.get(guild_id):
            embed.add_field(name="Tocando Agora", value=f"**{self.tocando_agora[guild_id]['title']}**", inline=False)

        if self.filas.get(guild_id):
            proximas = "\n".join(f"{i+1}. {item['title']}" for i, item in enumerate(self.filas[guild_id][:10]))
            if len(self.filas[guild_id]) > 10:
                proximas += f"\n... e mais {len(self.filas[guild_id]) - 10}."
            embed.add_field(name="Próximas na Fila", value=proximas, inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Musica(bot))