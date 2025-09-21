# cogs/registro.py

import discord
from discord.ext import commands
from discord.ui import View, Select
from discord.utils import get
import logging
import traceback
import os
from dotenv import load_dotenv
load_dotenv()
#--- CONFIGURAÇÃO DE SEGURANÇA ---
ID_SERVIDOR = int(os.getenv("ID_SERVIDOR"))
CARGO_DEV = int(os.getenv("CARGO_DEV"))
# -------------------------------

logger = logging.getLogger(__name__)

# --- COG DE DIAGNÓSTICO DE PERMISSÕES ---

class Diagnostico(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="verificar_permissoes")
    @commands.has_permissions(administrator=True) 
    async def verificar_permissoes(self, ctx):
        bot_membro = ctx.guild.me
        if bot_membro.guild_permissions.manage_roles:
            logger.info(f"O bot tem permissão para Gerenciar Cargos no servidor '{ctx.guild.name}'.")
        else:
            logger.critical(f"❌ O bot NÃO tem permissão para Gerenciar Cargos no servidor '{ctx.guild.name}'. <&@{CARGO_DEV}>")

# --- COG PRINCIPAL DE REGISTRO ---

class Registro(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(RegistroView())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        logger.info(f"❗ Novo membro detectado: '{member.name}' (ID: {member.id}) no servidor '{member.guild.name}'.")
        if member.bot:
            logger.info(f"O membro '{member.name}' é um bot. Ignorando.")
            return
        
        mensagem_dm = (
            f"Oii👋 {member.mention}, Seja Bem-vindo(a) ao **{member.guild.name}**!\n\n"
            "Eu sou o 🤖 Robozinho amigo dos ADMs que veio te ajudar a ter acesso completo ao servidor. Por favor, inicie seu registro clicando no botão abaixo. ⬇️"
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
            discord.SelectOption(label="Menor que 18", description="Selecione esta opção se você tiver menos de 18 anos.", value="menor_18"),
            discord.SelectOption(label="Maior que 18", description="Selecione esta opção se você tiver mais de 18 anos.", value="maior_18")
        ]
        super().__init__(placeholder="Nos conte sua idade...", options=options, custom_id="idade_select")
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

# Menu de seleção de genero
class GeneroSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Masculino", value="Homem"),
            discord.SelectOption(label="Feminino", value="Mulher"),
            discord.SelectOption(label="Outro", value="Não-Binário"),
        ]
        super().__init__(placeholder="Como você se identifica?", options=options, custom_id="genero_select")
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()


# View com o Botão de Início

class RegistroView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📝 Iniciar Registro", style=discord.ButtonStyle.success, custom_id="botao_registro")
    async def botao_callback(self, interaction: discord.Interaction, button: discord.Button):
        logger.info(f"Botão 'Iniciar Registro' clicado por {interaction.user.name}")
        await interaction.response.edit_message(
            content="Show! Me responde essas coisinhas pro pessoal do nosso servidor te conhecer melhor?",
            view=FormularioView(membro=interaction.user)
        )

# --- FORMULÁRIO DE REGISTRO ---

class FormularioView(View):
    def __init__(self, membro: discord.Member):
        super().__init__(timeout=None)
        self.membro = membro # Armazena o membro para atribuir os cargos depois

        # Adiciona os menus de seleção à View
        self.idade_select = IdadeSelect()
        self.genero_select = GeneroSelect()
        self.add_item(self.idade_select)
        self.add_item(self.genero_select)

    @discord.ui.button(label="✅ Enviar Respostas", style=discord.ButtonStyle.primary, custom_id="enviar_respostas")
    async def botao_enviar_callback(self, interaction: discord.Interaction, button: discord.Button):
        try:
            logger.info(f"Callback 'enviar_respostas' iniciado por {interaction.user.name}")

            # PASSO 1: Deferir a interação para ganhar tempo
            await interaction.response.defer(ephemeral=True, thinking=True)

            # PASSO 2: Verificar se as opções foram selecionadas
            if not self.idade_select.values or not self.genero_select.values:
                logger.warning(f"⚠️ Usuário {interaction.user} não selecionou todas as opções. Enviando aviso.")
                await interaction.followup.send("Você precisa selecionar uma opção em ambos os menus!", ephemeral=True)
                return

            # PASSO 3: Desativar componentes na mensagem original
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

            # PASSO 4: Obter o servidor (guild) e o membro
            guild = interaction.client.get_guild(ID_SERVIDOR)
            if not guild:
                logger.error(f"\n<&@{CARGO_DEV}>❌ Guild com ID {ID_SERVIDOR} não encontrada.\n")
                await interaction.followup.send("Erro interno: Não encontrei meu servidor. Avise um ADM!", ephemeral=True)
                return

            logger.info(f"Buscando o membro com ID: {interaction.user.id} no servidor '{guild.name}'")
            membro_no_servidor = await guild.fetch_member(interaction.user.id) # <<< Guarda o usuario nessa variavel
            if not membro_no_servidor:
                logger.error(f"\n<&@{CARGO_DEV}>❌ Membro com ID {interaction.user.id} não encontrado no servidor.\n")
                await interaction.followup.send("Erro interno: Não te encontrei no servidor. Avise um ADM!", ephemeral=True)
                return
            

            # PASSO 6: Lógica para buscar os cargos
            idade_selecionada = self.idade_select.values[0]
            genero_selecionado = self.genero_select.values[0]

            nome_cargo_idade = "-18" if idade_selecionada == "menor_18" else "+18"

            cargo_idade = get(guild.roles, name=nome_cargo_idade)
            cargo_genero = get(guild.roles, name=genero_selecionado)
            cargo_verificado = get(guild.roles, name="Kaizoku")
            logger.info(f"Usuario: {interaction.user} Idade: {cargo_idade}, Gênero: {cargo_genero}, Verificado: {cargo_verificado}")

            # PASSO 7: Verificar se todos os cargos foram encontrados
            if not all([cargo_idade, cargo_genero, cargo_verificado]):
                logger.critical(f"\n<&@{CARGO_DEV}> Falha na verificação 'not all'. Um ou mais cargos são 'None'.\n")
                await interaction.followup.send("Ops! Um ou mais cargos não foram encontrados no servidor. Avise um administrador!", ephemeral=True)
                return

            # PASSO 8: Tentar adicionar os cargos ao membro
            await membro_no_servidor.add_roles(cargo_verificado, cargo_idade, cargo_genero)
            logger.info("Cargos adicionados com sucesso!")

            # PASSO 10: Enviar mensagem de sucesso
            await interaction.followup.send("✅ Tudo certo! Seus cargos foram atribuídos com sucesso e você deve conseguir ver todo o servidor agora! 🎊", ephemeral=True)
            logger.info(f"Processo de registro finalizado com sucesso para '{membro_no_servidor.name}'.\n"
                        f"ID: {membro_no_servidor.id}")

        except Exception as e:
            # Este bloco captura qualquer erro inesperado que possa acontecer
            logger.error(f"\n❌ <&@{CARGO_DEV}> Erro inesperado no callback 'enviar_respostas' para '{interaction.user.name}': {e}")
            logger.error(traceback.format_exc()) # Imprime o traceback completo no log
            await interaction.followup.send("Ocorreu um erro crítico ao processar sua solicitação. A equipe de ADMs já foi notificada!", ephemeral=True)

# --- FUNÇÃO SETUP CORRIGIDA ---
async def setup(bot):
    await bot.add_cog(Registro(bot))
    await bot.add_cog(Diagnostico(bot))