#cogs/membros_request.py

import discord
from discord.ext import commands
from discord.ui import View, Button
from discord.utils import get
import logging
import os
import aiohttp
import json
from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURAÇÃO DE SEGURANÇA ---
ID_SERVIDOR = int(os.getenv("ID_SERVIDOR"))
CARGO_DEV = int(os.getenv("CARGO_DEV"))
BACKEND_API_URL = os.getenv("BACKEND_API_URL")
BOT_API_KEY = os.getenv("BOT_API_KEY")
CARGO_QA = int(os.getenv("CARGO_QA"))
# -------------------------------

logger = logging.getLogger(__name__)

class Membros_request:
    """Comandos de utilidade geral para todos os membros."""
    
class TermoConsentimentoView(View):
    def __init__(self, bot: commands.Bot, autor: discord.Member):
        super().__init__(timeout=60)
        self.bot = bot
        self.autor = autor
        self.clicado = False #Flag para garantir que só pode ser clicado uma vez

    # --- BOTAO ACEITAR ---
    @discord.ui.button(label="Aceito ✅", style=discord.ButtonStyle.success, custom_id="aceitar_termo_qa")
    async def aceitar_callback(self, interaction: discord.Integration, button: Button):
        if interaction.user.id != self.autor.id:
            await interaction.response.send_message("⚠️ Você não pode interagir com este formulário.", ephemeral=True)
            return
        
        if self.clicado:
            await interaction.response.send_message("⚠️ Você já respondeu a este termo.", ephemeral=True)
            return
        
        self.clicado = True

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        guild = self.bot.get_guild(ID_SERVIDOR)
        if not guild:
            logger.error(f"Não foi possível encontrar o servidor com o ID: {ID_SERVIDOR}")
            return
        
        cargo_qa = guild.get_role(CARGO_QA)
        if not cargo_qa:
            logger.error(f"Não foi possível encontrar o cargo QA com o ID: {CARGO_QA}")
            await interaction.followup.send("❌ Ocorreu um erro interno ao tentar encontrar o cargo. Por favor, avise um administrador.", ephemeral=True)
            return
        
        membro = await guild.fetch_member(self.autor.id)

        await membro.add_roles(cargo_qa)
        logger.info(f"Cargo '{cargo_qa.name}' adicionado ao membro '{membro.name}'.")

        membro_atualizado = await guild.fetch_member(self.autor.id)
        
        payload = {
            "discordId": str(membro_atualizado.id),
            "username": membro_atualizado.name,
            "nickName": membro_atualizado.nick,
            "globalName": membro_atualizado.global_name,
            "avatarUrl": str(membro_atualizado.display_avatar.url),
            "joinedAt": membro_atualizado.joined_at.isoformat() if membro_atualizado.joined_at else None,
            "roles": [str(role.id) for role in membro_atualizado.roles if role.name != "@everyone"]
        }
        headers = {"Content-Type": "application/json", "X-API-KEY": BOT_API_KEY}

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.post(BACKEND_API_URL, data=json.dumps([payload])) as response:
                    if response.status == 200:
                        logger.debug(f"Membro '{membro.name}' sincronizado com sucesso após aceitar termo QA.")
                    else:
                        logger.error(f"Falha na sincronização do membro '{membro.name}' após aceitar termo QA: Status {response.status}")
            except aiohttp.ClientConnectorError:
                logger.error(f"Erro de conexão ao tentar sincronizar membro '{membro.name}' após aceitar termo QA.")

        await interaction.followup.send(f"✅ **Termo aceito!** O cargo `{cargo_qa.name}` foi adicionado a você. Você agora tem acesso total ao Forum de discussões do Projeto Ohara!",
                                        ephemeral=True)
        
        # --- BOTAO RECUSAR --- 
    @discord.ui.button(label="Recusar ❌", style=discord.ButtonStyle.danger, custom_id="recusar_termo_qa")
    async def recusar_callback(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.autor.id:
            await interaction.response.send_message("⚠️ Você não pode interagir com este formulário.", ephemeral=True)
            return
        
        if self.clicado:
            await interaction.response.send_message("⚠️ Você já respondeu a este termo.", ephemeral=True)
            return
            
        self.clicado = True
        
        # Desativa os botões após o clique
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        
        await interaction.followup.send("Tudo bem 😓. Seus dados não foram coletados e o cargo não foi adicionado. Se mudar de ideia, use o comando novamente.", ephemeral=True)

class SolicitarQA(commands.Cog):
    """Inicia o processo para um membro solicitar o cargo de QA."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="projeto")
    async def solicitar_qa(self, ctx):
        embed = discord.Embed(
            title="✍️ Termo de Consentimento para Cargo de QA",
            description=(
                "Para obter o cargo de **QA (Quality Assurance)** e acesso aos canais de teste, "
                "precisamos da sua permissão para coletar e armazenar algumas das suas informações do Discord, "
                "como seu ID, nome de usuário, apelido, cargos e futuramente **email**.\n\n"
                "Esses dados serão enviados e armazenados em nosso banco de dados **propietario** para fins academicos,"
                "gerenciamento e identificação dentro da nossa comunidade em desenvolvimento. Somemte as pessoas com o cargo **@Dev** "
                "terão acesso a esses dados 😉. \n\n"
                "**Ao clicar em 'Aceito ✅', você concorda com a coleta e armazenamento desses dados, recebe acesso aos bastidores de todas as novidades e a possibilidade de enviar sugestões**"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Se você recusar, nenhuma ação será tomada. Esta solicitação expira em **1 minuto.**") 

        await ctx.send(embed=embed, view=TermoConsentimentoView(self.bot, ctx.author), ephemeral=True,
                       delete_after=180)

        await ctx.message.delete()
    
class SolicitarAtt(commands.Cog):
    """Comandos para sincronizar os dados de um membro com a base de dados."""
    def __init__(self, bot):
        self.bot = bot
        self.back_url = os.getenv("BACKEND_API_URL")
        self.back_key = os.getenv("BOT_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.back_key
        }

    @commands.command(name="sync_me")
    async def solicitar_att(self, ctx):
        autor = ctx.author

        feedback_message = await ctx.send(f"⚙️ **Sincronizando** seu perfil com a base de dados", delete_after= 10)
        
        payload = {
            "discordId": str(autor.id),
            "username": autor.name,
            "nickName": autor.nick,
            "globalName": autor.global_name,
            "joinedAt": autor.joined_at.isoformat() if autor.joined_at else None,
            "avatarUrl": str(autor.display_avatar.url),
            "roles": [str(role.id) for role in autor.roles if role.name != "@everyone"]
        }

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(self.back_url, data=json.dumps([payload])) as response:
                    if response.status == 200:
                        await feedback_message.edit(content=f"✅ '{ctx.author.mention}' foi sincronizado com **sucesso**.", delete_after= 10)
                    else:
                        await feedback_message.edit(content=f"❌ **Erro ao sincronizar seu perfil:** Problema interno.", delete_after= 10)
                        logger.error(f"Erro ao sincronizar '{autor.name}'. Status {response.status} - {await response.text()}")
        except aiohttp.ClientConnectionError as e:
            await feedback_message.edit(content="❌ **Erro de Conexão:** Não foi possível conectar ao backend.", delete_after= 10)
            logger.error(f"Erro de conexão ao tentar sincronizar '{autor.name}': {e}")

        await ctx.message.delete()

class Utilidades(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.caminho_arquivo = 'cogs_status.json'

    def _carregar_status(self):
        try:
            with open(self.caminho_arquivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error(f"Arquivo '{self.caminho_arquivo}' não encontrado ou corrompido.")
            return {}
    
    @commands.command(name="status")
    async def cogs_status(self, ctx):
        embed = discord.Embed(
            title="⚙️ Status dos Módulos (Cogs)",
            description="📝 Relatório de todas as minhas funcionalidades",
            color=discord.Color.dark_purple()
        )

        status_data = self._carregar_status()
        if not status_data:
            await ctx.send("❌ Não foi possível carregar o arquivo de status dos cogs.")
            return
        
        for cog_name, data in status_data.items():
            is_loaded = f"cogs.{cog_name}" in self.bot.extensions
            
            description_text = ""
            motivo_text = ""

            if is_loaded:
                status_emoji = "🟢 Ativo"
                # Tenta pegar a descrição (docstring) do Cog carregado
                # Assumimos que o nome da classe é o nome do arquivo capitalizado
                cog_object = self.bot.get_cog(cog_name.capitalize())
                if cog_object and cog_object.__doc__:
                    # Pega a primeira linha da docstring
                    description_text = f"\n*{cog_object.__doc__.strip().splitlines()[0]}*"

            else:
                status_emoji = "🔴 Inativo"
                motivo_text = f'\n*Motivo:* {data.get("motivo", "N/A")}' if data.get("motivo") else ""

            # Monta o valor do campo do embed
            field_value = f"**Estado:** {status_emoji}{description_text}{motivo_text}"
            
            embed.add_field(
                name=cog_name.capitalize(),
                value=field_value,
                inline=False
            )
            
        await ctx.send(embed=embed)
            
async def setup(bot):
    await bot.add_cog(SolicitarQA(bot))
    await bot.add_cog(SolicitarAtt(bot))
    await bot.add_cog(Utilidades(bot))
        