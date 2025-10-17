import discord
from discord.ext import commands
import logging
import yt_dlp
import asyncio
from functools import partial
import spotipy 
from spotipy.oauth2 import SpotifyClientCredentials 
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")


sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID,
                                                           client_secret=SPOTIPY_CLIENT_SECRET))

# --- CONFIGURAÇÕES YT-DLP ---
YTDL_BASE = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',
    'geo_bypass': True,
    'extract_flat': False,
    'force_generic_extractor': False,
    'skip_unavailable_fragments': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'skip': ['dash', 'hls'],
        }
    },
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

# sem ser playlist
YTDL_OPTIONS = {**YTDL_BASE, 'noplaylist': True}

# quando for playlist arrocha aqui
YTDL_OPTIONS_PLAYLIST = {**YTDL_BASE, 'noplaylist': False, 'extract_flat': 'in_playlist'}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn -user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"'
}


class Musica(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.filas = {}
        self.tocando_agora = {}
        self.voice_clients = {}
        if os.path.exists('cookies.txt'):
            logger.info("Arquivo de cookies 'cookies.txt' encontrado e carregado para yt-dlp.")
        else:
            logger.error("Arquivo de cookies 'cookies.txt' não encontrado. Alguns links podem não funcionar corretamente.")
        self.ydl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Monitora o estado de voz para autodesconexão."""
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
        """Função auxiliar para extrair a URL de áudio e os cabeçalhos HTTP."""
        # Prioriza formatos que já vêm com os cabeçalhos, para maior compatibilidade
        for fmt in reversed(info.get('formats', [])):
            if fmt.get('acodec') and fmt.get('acodec') != 'none' and fmt.get('url') and fmt.get('http_headers'):
                return {'url': fmt['url'], 'headers': fmt['http_headers']}
        
        # Fallback para o método antigo se não encontrar headers (menos provável com yt-dlp atualizado)
        if 'url' in info:
            return {'url': info['url'], 'headers': None}
            
        return None

    
    async def processar_spotify_link(self, ctx, spotify_link: str):
        """
        Extrai informações de um link do Spotify (música ou playlist)
        e retorna uma lista de dicionários pra adicionar na fila.
        """
        try:
            
            if "track" in spotify_link:
                track_id = spotify_link.split('/')[-1].split('?')[0]
                track = await asyncio.to_thread(sp.track, track_id)
                artist_name = track['artists'][0]['name']
                track_name = track['name']
                query_youtube = f"{track_name} {artist_name}"
                return [{'title': f"{track_name} - {artist_name} (Spotify)", 'query': query_youtube}]

           
            elif "playlist" in spotify_link:
                playlist_id = spotify_link.split('/')[-1].split('?')[0]
                
               
                results = await asyncio.to_thread(sp.playlist_items, playlist_id)
                tracks_to_add = []
                
                playlist_title = await asyncio.to_thread(lambda: sp.playlist(playlist_id)['name'])
                await ctx.send(f"🎶 Playlist **{playlist_title}** do Spotify encontrada! Adicionando músicas à fila...")

                for item in results['items']:
                    track = item['track']
                    if track: 
                        artist_name = track['artists'][0]['name']
                        track_name = track['name']
                        query_youtube = f"{track_name} {artist_name}"
                        tracks_to_add.append({'title': f"{track_name} - {artist_name} (Spotify)", 'query': query_youtube})
                
                return tracks_to_add

            
            elif "album" in spotify_link:
                album_id = spotify_link.split('/')[-1].split('?')[0]
                album = await asyncio.to_thread(sp.album, album_id)
                tracks_to_add = []
                
                album_title = album['name']
                artist_name = album['artists'][0]['name']
                await ctx.send(f"💿 Álbum **{album_title}** de **{artist_name}** do Spotify encontrado! Adicionando músicas à fila...")

                for track in album['tracks']['items']:
                    if track:
                        artist_name_track = track['artists'][0]['name']
                        track_name = track['name']
                        query_youtube = f"{track_name} {artist_name_track}"
                        tracks_to_add.append({'title': f"{track_name} - {artist_name_track} (Spotify)", 'query': query_youtube})
                return tracks_to_add

            return [] 

        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro na API do Spotify: {e}")
            await ctx.send(f"❌ Erro ao interagir com o Spotify. Verifique o link e as credenciais.")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao processar link do Spotify: {e}")
            await ctx.send(f"❌ Ocorreu um erro ao processar o link do Spotify. Tente novamente.")
            return []

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

            if 'entries' in info:
                info = info['entries'][0]

            # <-- MUDANÇA INICIA AQUI -->
            audio_data = self.get_audio_url(info)
            if not audio_data or not audio_data.get('url'):
                await ctx.send(f"❌ Não foi possível obter uma URL de áudio para **{proximo_item['title']}**. Pulando.")
                self.filas[guild_id].pop(0)
                return await self.play_next(ctx)

            audio_url = audio_data['url']
            http_headers = audio_data.get('headers')

            self.filas[guild_id].pop(0)
            self.tocando_agora[guild_id] = proximo_item

            # Prepara as opções do FFmpeg com os headers customizados
            ffmpeg_opts = FFMPEG_OPTIONS.copy()
            if http_headers:
                # Formata os headers para a linha de comando do FFmpeg
                headers_str = "".join([f"{key}: {value}\r\n" for key, value in http_headers.items()])
                ffmpeg_opts['before_options'] += f' -headers "{headers_str}"'
                logger.info("Usando cabeçalhos HTTP customizados para o FFmpeg.")
            # <-- MUDANÇA TERMINA AQUI -->

            try:
                # Passa as opções customizadas para a chamada
                audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts)
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

       
        if "spotify.com" in query:
            # Se for um link do Spotify, entra aqui
            items_spotify = await self.processar_spotify_link(ctx, query)
            if not items_spotify:
                return await msg.edit(content=f"❌ Não foi possível processar o link do Spotify ou nenhum item encontrado.")
            
            for item in items_spotify:
                self.filas[guild_id].append(item)

            
            if len(items_spotify) == 1:
                await msg.edit(content=f"✅ Adicionado à fila: **{items_spotify[0]['title']}**")
            else:
                 await msg.edit(content=f"✅ Adicionadas **{len(items_spotify)}** músicas à fila!")

        else:
            
            ydl_opts_local = YTDL_OPTIONS.copy()
            if "list=" in query and ("youtube.com/" in query or "youtu.be/" in query):
                ydl_opts_local = YTDL_OPTIONS_PLAYLIST.copy()
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
            
            await msg.delete()
            return 
        

        ydl_opts_local = YTDL_OPTIONS.copy()
        
        if "list=" in query and ("youtube.com/" in query or "youtu.be/" in query):
            ydl_opts_local = YTDL_OPTIONS_PLAYLIST.copy()
            logger.info("Playlist detectada, usando modo de extração rápida.")
        else:
            ydl_opts_local = YTDL_OPTIONS.copy()
            
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
            voice_client.stop() 
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
