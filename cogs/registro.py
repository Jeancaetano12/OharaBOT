# cogs/registro.py

import discord
from discord.ext import commands
from discord.ui import View, Select
from discord.utils import get

# --- PASSO 1: DEFINIÇÃO DAS CLASSES DE UI (A PARTE QUE FALTAVA) ---

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

# Formulario modal
class FormularioView(View):
    def __init__(self, membro: discord.Member):
        super().__init__(timeout=300) # Timeout de 5 minutos para o usuário responder
        print(f"\n[DEBUG] Registro iniciado por {membro.name}")
        self.membro = membro # Armazena o membro para atribuir os cargos depois

        # Adiciona os menus de seleção à View
        self.idade_select = IdadeSelect()
        self.genero_select = GeneroSelect()
        self.add_item(self.idade_select)
        self.add_item(self.genero_select)

    @discord.ui.button(label="✅ Enviar Respostas", style=discord.ButtonStyle.primary, custom_id="enviar_respostas")
    async def botao_enviar_callback(self, interaction: discord.Interaction, button: discord.Button):
        try:
            print("\n--- INICIANDO CALLBACK 'ENVIAR RESPOSTAS' ---")
        
            # PASSO 1: Deferir a interação para ganhar tempo
            await interaction.response.defer(ephemeral=True, thinking=True)
            print("[DEBUG] Passo 1: Interação deferida com sucesso.")

            # PASSO 2: Verificar se as opções foram selecionadas
            print("[DEBUG] Passo 2: Verificando se as opções foram selecionadas...")
            if not self.idade_select.values or not self.genero_select.values:
                print("[AVISO] Usuário não selecionou todas as opções. Enviando aviso.")
                await interaction.followup.send("Você precisa selecionar uma opção em ambos os menus!", ephemeral=True)
                return
            print("[DEBUG] Opções selecionadas com sucesso.")

            # PASSO 3: Desativar componentes na mensagem original
            print("[DEBUG] Passo 3: Desativando componentes da View...")
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)
            print("[DEBUG] Componentes desativados.")

            # PASSO 4: Obter o servidor (guild) e o membro
            ID_DO_SERVIDOR = 842832283614052421 # <<< VERIFIQUE SE SEU ID DO SERVIDOR ESTÁ CORRETO AQUI
            print(f"[DEBUG] Passo 4: Buscando Guild com ID: {ID_DO_SERVIDOR}")
            guild = interaction.client.get_guild(ID_DO_SERVIDOR)
            if not guild:
                print(f"[ERRO CRÍTICO] Guild com ID {ID_DO_SERVIDOR} não encontrada.")
                await interaction.followup.send("Erro interno: Não encontrei meu servidor. Avise um ADM!", ephemeral=True)
                return
            print(f"[DEBUG] Guild encontrada: '{guild.name}'")
        
            print(f"[DEBUG] Passo 5: Buscando o membro com ID: {interaction.user.id} no servidor '{guild.name}'")
            membro_no_servidor = await guild.fetch_member(interaction.user.id) # <<< Guarda o usuario nessa variavel
            if not membro_no_servidor:
                print(f"[ERRO CRÍTICO] Membro com ID {interaction.user.id} não encontrado no servidor.")
                await interaction.followup.send("Erro interno: Não te encontrei no servidor. Avise um ADM!", ephemeral=True)
                return
            print(f"[DEBUG] Membro encontrado: '{membro_no_servidor.name}'")

            # PASSO 6: Lógica para buscar os cargos
            print("[DEBUG] Passo 6: Definindo e buscando cargos...")
            idade_selecionada = self.idade_select.values[0]
            genero_selecionado = self.genero_select.values[0]
            print(f"[DEBUG] Valores recebidos -> Idade: '{idade_selecionada}', Gênero: '{genero_selecionado}'")

            nome_cargo_idade = "-18" if idade_selecionada == "menor_18" else "+18"
            print(f"[DEBUG] Nome do cargo de idade a ser buscado: '{nome_cargo_idade}'")
        
            cargo_idade = get(guild.roles, name=nome_cargo_idade)
            cargo_genero = get(guild.roles, name=genero_selecionado)
            cargo_verificado = get(guild.roles, name="Kaizoku")
            print(f"[DEBUG] Resultados da busca -> Idade: {cargo_idade}, Gênero: {cargo_genero}, Verificado: {cargo_verificado}")

            # PASSO 7: Verificar se todos os cargos foram encontrados
            print("[DEBUG] Passo 7: Verificando se todos os cargos foram encontrados...")
            if not all([cargo_idade, cargo_genero, cargo_verificado]):
                print("[ERRO] Falha na verificação 'not all'. Um ou mais cargos são 'None'.")
                await interaction.followup.send("Ops! Um ou mais cargos não foram encontrados no servidor. Avise um administrador!", ephemeral=True)
                return
            print("[DEBUG] Todos os cargos necessários foram encontrados.")

            # PASSO 8: Tentar adicionar os cargos ao membro
            print(f"[DEBUG] Passo 8: Adicionando cargos para '{membro_no_servidor.name}'...")
            await membro_no_servidor.add_roles(cargo_verificado, cargo_idade, cargo_genero)
            print("[DEBUG] Passo 9: Cargos adicionados com sucesso!")

            # PASSO 10: Enviar mensagem de sucesso
            print("[DEBUG] Passo 10: Enviando followup de sucesso.")
            await interaction.followup.send("✅ Tudo certo! Seus cargos foram atribuídos com sucesso e você deve conseguir ver todo o servidor agora! 🎊", ephemeral=True)
            print("--- CALLBACK 'ENVIAR RESPOSTAS' FINALIZADO COM SUCESSO ---")

        except Exception as e:
            # Este bloco captura qualquer erro inesperado que possa acontecer
            print(f"\n--- ERRO INESPERADO NO CALLBACK 'ENVIAR RESPOSTAS' ---")
            print(f"[ERRO CRÍTICO] Ocorreu uma exceção: {e}")
            import traceback
            traceback.print_exc() # Imprime o traceback completo do erro
            print("-------------------------------------------------")
            await interaction.followup.send("Ocorreu um erro crítico ao processar sua solicitação. A equipe de ADMs já foi notificada!", ephemeral=True)
# View com o Botão de Início
class RegistroView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📝 Iniciar Registro", style=discord.ButtonStyle.success, custom_id="botao_registro")
    async def botao_callback(self, interaction: discord.Interaction, button: discord.Button):
        print(f"\n[DEBUG] Botão 'Iniciar Registro' clicado por {interaction.user.name}")
        print(f"[AÇÃO] Enviando formulário para {interaction.user.name}...")
        await interaction.response.edit_message(
            content="Show! Me responde essas coisinhas pro pessoal do nosso servidor te conhecer melhor?",
            view=FormularioView(membro=interaction.user)
        )
       

# --- ESTRUTURA DOS COGS ---

class Registro(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(RegistroView())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"\n[EVENTO] Novo membro detectado: {member.name} (ID: {member.id})")
        if member.bot:
            print(f"[INFO] O membro {member.name} é um bot. Ignorando.")
            return
        
        mensagem_dm = (
            f"Oii👋 {member.mention}, Seja Bem-vindo(a) ao **{member.guild.name}**!\n\n"
            "Eu sou o 🤖 Robozinho amigo dos ADMs que veio te ajudar a ter acesso completo ao servidor. Por favor, inicie seu registro clicando no botão abaixo. ⬇️"
        )
        
        try:
            print(f"[AÇÃO] Tentando enviar DM para {member.name}...")
            await member.send(mensagem_dm, view=RegistroView())
            print(f"[SUCESSO] DM enviada para {member.name}.")
        except discord.Forbidden:
            print(f"[ERRO] Falha ao enviar DM para {member.name}. As DMs dele(a) podem estar fechadas.")

class Diagnostico(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="verificar_permissoes")
    @commands.has_permissions(administrator=True) 
    async def verificar_permissoes(self, ctx):
        bot_membro = ctx.guild.me
        if bot_membro.guild_permissions.manage_roles:
            await ctx.send("✅ Eu tenho a permissão de **Gerenciar Cargos** neste servidor!")
        else:
            await ctx.send("❌ Eu **NÃO** tenho a permissão de **Gerenciar Cargos** neste servidor. Por favor, verifique minhas permissões e a hierarquia de cargos.")

# --- FUNÇÃO SETUP CORRIGIDA ---
async def setup(bot):
    await bot.add_cog(Registro(bot))
    await bot.add_cog(Diagnostico(bot))
    print("[SETUP] Cogs 'Registro' e 'Diagnostico' carregados.")