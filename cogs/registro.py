# cogs/registro.py

import discord
from discord.ext import commands
from discord.ui import View, Select
from discord.utils import get
import logging
import traceback
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
# -------------------------------


logger = logging.getLogger(__name__)

# --- COG PRINCIPAL DE REGISTRO ---
class Registro(commands.Cog):
    """Sistema de registro e verificação para novos membros."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(RegistroView())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            logger.info(f"O membro '{member.name}' é um bot. Ignorando.")
            return

        mensagem_dm = (
            f"Oii👋 {member.mention}, Seja Bem-vindo(a) ao **{member.guild.name}**!\n\n"
            "Eu sou o 🤖 Robozinho amigo dos ADMs que veio te ajudar a ter acesso completo ao servidor. "
            "Por favor, nos ajude a te conhecer melhor com o formulario abaixo ⬇️"
        )

        try:
            await member.send(mensagem_dm, view=RegistroView())
            logger.info(f"🔁 DM enviada para '{member.name}'.")
        except discord.Forbidden:
            logger.warning(f"⚠️ Falha ao enviar DM para '{member.name}'. As DMs dele(a) podem estar fechadas.")

# --- DEFINIÇÃO DAS CLASSES DE UI ---

# Menu de seleção de idade
class IdadeSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Menor de idade 👎", description="Selecione esta opção se você tiver menos de 18 anos.", value="menor_18"),
            discord.SelectOption(label="Sou adulto 👍", description="Selecione esta opção se você tiver mais de 18 anos.", value="maior_18")
        ]
        super().__init__(placeholder="🧐 Nos conte sua idade...", options=options, custom_id="idade_select")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

# Menu de seleção de genero
class GeneroSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Masculino", value="Masculino"),
            discord.SelectOption(label="Feminino", value="Feminino"),
            discord.SelectOption(label="Não-Binário", value="Não-Binário"),
            discord.SelectOption(label="Outro... 🏳️‍🌈", value="🏳️‍🌈"),
        ]
        super().__init__(placeholder="🤔 Como você se identifica?", options=options, custom_id="genero_select")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

# View com o Botão de Início
class RegistroView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Iniciar Registro", style=discord.ButtonStyle.success, custom_id="botao_registro")
    async def botao_callback(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.edit_message(
            content="Show!🥰 Me responde essas coisinhas pro pessoal do nosso servidor te conhecer melhor:",
            view=FormularioView(membro=interaction.user)
        )

# --- FORMULÁRIO DE REGISTRO ---
class FormularioView(View):
    def __init__(self, membro: discord.Member):
        super().__init__(timeout=None)
        self.membro = membro
        self.finalizado = False  # <<< Flag de controle para impedir múltiplos usos

        self.idade_select = IdadeSelect()
        self.genero_select = GeneroSelect()
        self.add_item(self.idade_select)
        self.add_item(self.genero_select)

    @discord.ui.button(label="✅ Enviar Respostas", style=discord.ButtonStyle.primary, custom_id="enviar_respostas")
    async def botao_enviar_callback(self, interaction: discord.Interaction, button: discord.Button):
        try:
            # Bloqueio de reuso do callback
            if self.finalizado:
                await interaction.response.send_message("⚠️ Você já finalizou o registro!", ephemeral=True)
                return
            self.finalizado = True

            await interaction.response.defer(ephemeral=True, thinking=True)
            
            # Obter a guild e o membro antes de qualquer outra verificação
            guild = interaction.client.get_guild(ID_SERVIDOR)
            if not guild:
                logger.error(f"<&@{CARGO_DEV}>❌ Guild: '{guild.name}' com ID {ID_SERVIDOR} não encontrada.")
                await interaction.followup.send(f"❌ Erro interno: Não encontrei meu servidor '{guild.name}'. Avise um ADM de lá!", ephemeral=True)
                return
            
            membro_no_servidor = await guild.fetch_member(interaction.user.id)
            if not membro_no_servidor:
                logger.error(f"<&@{CARGO_DEV}>❌ Membro com ID {interaction.user.id} não encontrado no servidor.")
                await interaction.followup.send(f"❌ Erro interno: Não te encontrei no servidor: '{guild.name}'. Avise um ADM de lá!", ephemeral=True)
                return
            # Impede re-registro de quem já possui o cargo de verificação
            if any(role.name == "Kaizoku" for role in membro_no_servidor.roles):
                await interaction.followup.send("⚠️ Você já está registrado no servidor!", ephemeral=True)
                return

            # Verifica se os campos foram preenchidos
            if not self.idade_select.values or not self.genero_select.values:
                await interaction.followup.send("Você precisa selecionar uma opção em ambos os menus!", ephemeral=True)
                return

            # Desativa os componentes na mensagem original
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

            guild = interaction.client.get_guild(ID_SERVIDOR)
            if not guild:
                logger.error(f"<&@{CARGO_DEV}>❌ Guild: '{guild.name}' com ID {ID_SERVIDOR} não encontrada.")
                await interaction.followup.send(f"❌ Erro interno: Não encontrei meu servidor '{guild.name}'. Avise um ADM de lá!", ephemeral=True)
                return

            membro_no_servidor = await guild.fetch_member(interaction.user.id)
            if not membro_no_servidor:
                logger.error(f"<&@{CARGO_DEV}>❌ Membro com ID {interaction.user.id} não encontrado no servidor.")
                await interaction.followup.send(f"❌ Erro interno: Não te encontrei no servidor: '{guild.name}'. Avise um ADM de lá!", ephemeral=True)
                return

            idade_selecionada = self.idade_select.values[0]
            genero_selecionado = self.genero_select.values[0]

            nome_cargo_idade = "-18" if idade_selecionada == "menor_18" else "+18"
            cargo_idade = get(guild.roles, name=nome_cargo_idade)
            cargo_genero = get(guild.roles, name=genero_selecionado)
            cargo_verificado = get(guild.roles, name="Kaizoku")

            if not all([cargo_idade, cargo_genero, cargo_verificado]):
                logger.critical(f"<&@{CARGO_DEV}> Falha na verificação 'not all'. Um ou mais cargos são 'None'.")
                await interaction.followup.send(f"Ops! Um ou mais cargos não foram encontrados no servidor: '{guild.name}'. Avise um administrador!", ephemeral=True)
                return

            await membro_no_servidor.add_roles(cargo_verificado, cargo_idade, cargo_genero)
            
            membro_atualizado = await guild.fetch_member(interaction.user.id)

            payload = {
                "discordId": str(membro_atualizado.id),
                "username": membro_atualizado.name,
                "nickName": membro_atualizado.nick,
                "globalName": membro_atualizado.global_name,
                "avatarUrl": membro_atualizado.display_avatar.url,
                "joinedAt": membro_atualizado.joined_at.isoformat() if membro_atualizado.joined_at else None,
                "roles": [{"id": str(role.id), "name": role.name} for role in membro_atualizado.roles if role.name != "@everyone"]
            }

            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": BOT_API_KEY
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                try:
                    async with session.post(BACKEND_API_URL, data=json.dumps([payload])) as response:
                        if response.status == 200:
                            logger.debug(f"✅ Membro '{membro_atualizado}' sincronizado com sucesso com o backend.")
                        else:
                            logger.error(f"❌ Falha na sincronização do membro '{membro_atualizado}': Status {response.status} - {await response.text()}")
                except aiohttp.ClientConnectorError:
                    logger.error(f"❌ Erro de conexão ao tentar sincronizar membro '{membro_atualizado}' com o backend.")

            # Embed de confirmação bonito
            embed = discord.Embed(
                title="🎉 Registro Concluído!",
                description=f"Bem-vindo(a) ao **{guild.name}**, {interaction.user.mention}!",
                color=discord.Color.green()
            )
            embed.add_field(name="📅 Idade:", value="🔞 +18" if idade_selecionada == "maior_18" else "🍼 -18", inline=True)
            embed.add_field(name="🧍 Identificação:", value=genero_selecionado, inline=True)
            embed.set_footer(text="🎉 Fique a vontade para interagir com o pessoal daqui. Divirta-se no servidor! 🥰")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"✅ Registro concluído com sucesso para '{interaction.user}' no servidor '{guild.name}'.")

            # Remove a view da mensagem original para invalidar qualquer interação futura
            await interaction.delete_original_response()


        except Exception as e:
            logger.error(f"❌ <&@{CARGO_DEV}> Erro no callback 'enviar_respostas' do membro: {e}")
            logger.error(traceback.format_exc())
            await interaction.followup.send("❌ Ocorreu um erro crítico ao processar sua solicitação. A equipe de ADMs já foi notificada!", ephemeral=True)  

# --- FUNÇÃO SETUP ---
async def setup(bot):
    await bot.add_cog(Registro(bot))