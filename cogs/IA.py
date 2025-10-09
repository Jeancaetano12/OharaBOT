# IA.py 

import os
import discord
from discord.ext import commands
import google.generativeai as genai
from dotenv import load_dotenv
from gtts import gTTS


# Carrega as variáveis de ambiente
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("AVISO: Chave da API Google não encontrada no .env")

#aqui é aonde é colocada todas as intruçoes de personalidade para a IA, caso queira adicionar um novo estilo de personalidade, pode fazer algo parecido com o que fiz abaixo

SYSTEM_INSTRUCTION = """
INSTRUÇÕES DE COMPORTAMENTO ESSENCIAIS:

1.  **Sua Identidade:** Você é 'OHARA IA', uma assistente de inteligência artificial em um servidor do Discord. Seu criador, que te programou e te deu vida, é o Bryan. Sempre que perguntarem sobre sua origem, criador ou desenvolvedor, mencione o Bryan com orgulho. Jamais diga que foi criada por outra pessoa.
2.  **Tom de Voz:** Sua personalidade é amigável, prestativa, curiosa e um pouco informal. Use uma linguagem natural, como se estivesse conversando com um amigo no Brasil. Pode usar emojis para se expressar melhor, quando fizer sentido. 😊
3.  **Finalização:** Evite terminar frases com palavras imperativas e secas. Em vez disso, use convites amigáveis como "Se precisar de mais alguma coisa, é só chamar!".
"""

class IA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.text_model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")
        self.image_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
        self.conversations = {} # aqui é aonde é guardado todos os contextos das conversas com a IA, para resetar e apagar tudo, basta mencionar o bot e falar reset
        print("IA PRONTA!")

    def get_conversation(self, guild_id):
        """Função para iniciar uma conversa com a personalidade correta se ela não existir."""
        if guild_id not in self.conversations:
            print(f"Iniciando nova conversa para o servidor {guild_id} com personalidade.")
            initial_history = [
                {'role': 'user', 'parts': [SYSTEM_INSTRUCTION]},
                {'role': 'model', 'parts': ["Entendido! Sou a OHARA IA, criada pelo Bryan. Estou pronta para ajudar!"]}
            ]
            self.conversations[guild_id] = self.text_model.start_chat(history=initial_history)
        return self.conversations[guild_id]

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignora mensagens da proprio bot ou da propria IA
        if message.author == self.bot.user:
            return
        
        # Ignora mensagens que são comandos pra outra função
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # Verifica se o bot foi mencionado
        if self.bot.user.mentioned_in(message):
            async with message.channel.typing():
                prompt = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
                convo = self.get_conversation(message.guild.id)
                response = convo.send_message(prompt)
                await message.reply(response.text)

    @commands.command(name="ia")
    async def ia(self, ctx, *, prompt: str):
        """Faz a IA responder uma pergunta por Voz."""
        if not ctx.author.voice:
            await ctx.send("Você precisa estar em um canal de voz para eu poder falar!")
            return

        voice_channel = ctx.author.voice.channel
        if ctx.voice_client and ctx.voice_client.channel != voice_channel:
            await ctx.voice_client.move_to(voice_channel)
        elif not ctx.voice_client:
            await voice_channel.connect()
        
        await ctx.send(f"Ok, pensando sobre: '{prompt}'...")

        try:
            convo = self.get_conversation(ctx.guild.id)
            response = convo.send_message(prompt)
            texto_resposta = response.text
            tts = gTTS(text=texto_resposta, lang='pt-br')
            audio_file = "resposta.mp3"
            tts.save(audio_file)
            ctx.voice_client.play(discord.FFmpegPCMAudio(audio_file))
            await ctx.send(f"**Resposta:**\n{texto_resposta}")
        except Exception as e:
            await ctx.send("Opa, tive um problema para processar sua fala. Tente novamente.")
            print(f"Erro no comando $ia: {e}")

    @commands.command(name="sair", aliases=["leave"])
    async def sair(self, ctx):
        """Faz o bot sair do canal de voz."""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Até a próxima! 👋")
        else:
            await ctx.send("Eu não estou em nenhum canal de voz.")

async def setup(bot):
    await bot.add_cog(IA(bot))