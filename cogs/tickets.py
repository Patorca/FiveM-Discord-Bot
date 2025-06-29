import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
from typing import Optional
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

async def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

async def create_transcript(channel: discord.TextChannel, user: discord.User) -> str:
    messages = []
    async for message in channel.history(limit=None, oldest_first=True):
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = f"{message.author.display_name} ({message.author.name}#{message.author.discriminator})"
        content = message.content or "[No content]"
        if message.embeds:
            for embed in message.embeds:
                if embed.title:
                    content += f"\n[Embed: {embed.title}]"
                if embed.description:
                    content += f"\n{embed.description}"
        if message.attachments:
            for attachment in message.attachments:
                content += f"\n[Attachment: {attachment.filename}]"
        messages.append(f"[{timestamp}] {author}: {content}")

    transcript = (
        f"Transcript del Ticket: {channel.name}\n"
        f"Usuario: {user.display_name} ({user.name}#{user.discriminator})\n"
        f"Creado: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Cerrado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        + "=" * 50 + "\n\n" + "\n".join(messages)
    )
    return transcript

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Crear Ticket',
        style=discord.ButtonStyle.primary,
        emoji='🎫',
        custom_id='create_ticket'
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user

        existing_ticket = discord.utils.get(
            guild.channels,
            name=f'ticket-{user.name.lower()}-{user.discriminator}'
        )
        if existing_ticket:
            await interaction.followup.send(
                f"❌ Ya tienes un ticket abierto: {existing_ticket.mention}",
                ephemeral=True
            )
            return

        try:
            config = await load_config()
            guild_id_str = str(guild.id)
            server_config = config.get('servers', {}).get(guild_id_str, {})

            category = None
            if category_id := server_config.get('ticket_category_id'):
                category = guild.get_channel(category_id)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True,
                    attach_files=True, embed_links=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True,
                    manage_channels=True, manage_messages=True
                )
            }

            for role_id in server_config.get('staff_role_ids', []):
                role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True,
                        manage_messages=True
                    )

            ticket_channel = await guild.create_text_channel(
                name=f'ticket-{user.name.lower()}-{user.discriminator}',
                category=category,
                overwrites=overwrites,
                topic=f'Support ticket for {user.display_name} ({user.id})'
            )

            close_view = CloseTicketView()

            embed = discord.Embed(
                title="🎫 Ticket de Soporte Creado",
                description=(
                    f"¡Hola {user.mention}! Gracias por crear un ticket.\n\n"
                    "Por favor describe tu problema en detalle y nuestro staff te ayudará en breve.\n\n"
                    "Para cerrar este ticket, haz clic en el botón de abajo."
                ),
                color=0x00ff00
            )
            embed.set_footer(text=f"Ticket creado por {user.display_name}", icon_url=user.display_avatar.url)

            # Mencionar rol staff definido en config
            staff_mention_role_id = server_config.get('staff_mention_role_id')
            if staff_mention_role_id:
                staff_role = guild.get_role(staff_mention_role_id)
                if staff_role:
                    await ticket_channel.send(f"{staff_role.mention} - Nuevo ticket creado por {user.mention}")

            await ticket_channel.send(embed=embed, view=close_view)
            await interaction.followup.send(
                f"✅ Tu ticket ha sido creado: {ticket_channel.mention}",
                ephemeral=True
            )
            logger.info(f"Ticket created by {user} ({user.id}) in {guild.name}")

        except discord.Forbidden:
            await interaction.followup.send("❌ No tengo permisos para crear canales!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.followup.send("❌ Ocurrió un error al crear tu ticket!", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Cerrar Ticket',
        style=discord.ButtonStyle.danger,
        emoji='🔒',
        custom_id='close_ticket'
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.channel.name.startswith('ticket-'):
            await interaction.response.send_message(
                "❌ Este botón solo puede usarse en canales de ticket!",
                ephemeral=True
            )
            return

        user = interaction.user
        channel = interaction.channel
        can_close = False

        if f'-{user.name.lower()}-{user.discriminator}' in channel.name:
            can_close = True

        if not can_close:
            config = await load_config()
            guild_id_str = str(channel.guild.id)
            server_config = config.get('servers', {}).get(guild_id_str, {})
            staff_role_ids = server_config.get('staff_role_ids', [])
            for role_id in staff_role_ids:
                if discord.utils.get(user.roles, id=role_id):
                    can_close = True
                    break

        if not can_close and channel.permissions_for(user).manage_channels:
            can_close = True

        if not can_close:
            await interaction.response.send_message(
                "❌ No tienes permiso para cerrar este ticket!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🔒 Cerrando Ticket",
            description="Este ticket se cerrará en 5 segundos...",
            color=0xff0000
        )
        embed.set_footer(text=f"Cerrado por {user.display_name}", icon_url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

        ticket_creator = None
        parts = channel.name.split('-')
        if len(parts) >= 3:
            username = '-'.join(parts[1:-1])
            discriminator = parts[-1]
            for member in channel.guild.members:
                if member.name.lower() == username and member.discriminator == discriminator:
                    ticket_creator = member
                    break

        try:
            if ticket_creator:
                transcript_content = await create_transcript(channel, ticket_creator)

                import io
                transcript_file = io.StringIO(transcript_content)
                file = discord.File(transcript_file, filename=f"transcript-{channel.name}.txt")

                config = await load_config()
                guild_id_str = str(channel.guild.id)
                server_config = config.get('servers', {}).get(guild_id_str, {})

                transcript_channel_id = server_config.get('transcript_channel_id')
                if transcript_channel_id:
                    transcript_channel = channel.guild.get_channel(transcript_channel_id)
                    if transcript_channel:
                        transcript_embed = discord.Embed(
                            title="📝 Transcript del Ticket",
                            description=(
                                f"**Canal:** {channel.name}\n"
                                f"**Usuario:** {ticket_creator.display_name}\n"
                                f"**Cerrado por:** {user.display_name}\n"
                                f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            ),
                            color=0x3498db
                        )
                        await transcript_channel.send(embed=transcript_embed, file=file)

                try:
                    transcript_file_dm = io.StringIO(transcript_content)
                    file_dm = discord.File(transcript_file_dm, filename=f"transcript-{channel.name}.txt")
                    dm_embed = discord.Embed(
                        title="📝 Transcript de tu Ticket",
                        description=(
                            f"Tu ticket en **{channel.guild.name}** ha sido cerrado.\n"
                            "Aquí tienes el transcript completo de la conversación."
                        ),
                        color=0x3498db
                    )
                    await ticket_creator.send(embed=dm_embed, file=file_dm)
                except discord.Forbidden:
                    logger.info(f"No se pudo enviar transcript DM a {ticket_creator} - DMs deshabilitados")
                except Exception as e:
                    logger.error(f"Error enviando transcript DM: {e}")

        except Exception as e:
            logger.error(f"Error creando transcript: {e}")

        await asyncio.sleep(5)

        try:
            await channel.delete(reason=f"Ticket cerrado por {user}")
            logger.info(f"Ticket {channel.name} cerrado por {user} ({user.id})")
        except discord.NotFound:
            pass
        except Exception as e:
            logger.error(f"Error cerrando ticket: {e}")

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketView())
        self.bot.add_view(CloseTicketView())

    @app_commands.command(name="ticket-panel", description="Crear un panel de tickets con botón")
    @app_commands.describe(channel="Canal para enviar el panel de tickets (opcional)")
    @app_commands.default_permissions(manage_channels=True)
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None
    ):
        if channel is None:
            channel = interaction.channel

        bot_perms = channel.permissions_for(interaction.guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            await interaction.response.send_message(
                f"❌ No tengo permisos para enviar mensajes o embeds en {channel.mention}!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎫 Sistema de Tickets de Soporte",
            description=(
                "Al abrir un ticket te estas poniendo en contacto con la administración que te responderá en breve, "
                "por favor expón los motivos de tu ticket de manera concisa para que te podamos ayudar mejor.\n\n"
                "**Qué ocurre cuando creas un ticket:**\n"
                "• Se creará un canal privado solo para ti\n"
                "• Solo tú y el staff pueden verlo\n"
                "• Describe tu problema y te ayudaremos\n\n"
                "**Nota importante:** Solo puedes tener un ticket abierto a la vez."
            ),
            color=0x3498db
        )
        embed.set_footer(text="Haz clic en el botón para crear un ticket")

        view = TicketView()

        try:
            await channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"✅ Panel de tickets creado en {channel.mention}!",
                ephemeral=True
            )
            logger.info(f"Panel de tickets creado por {interaction.user} en {channel.name}")
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ No tengo permiso para enviar mensajes en {channel.mention}!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creando panel de tickets: {e}")
            await interaction.response.send_message(
                "❌ Ocurrió un error al crear el panel de tickets!",
                ephemeral=True
            )

    @app_commands.command(name="set-ticket-category", description="Establecer categoría para los tickets")
    @app_commands.describe(category="Categoría para los tickets")
    @app_commands.default_permissions(manage_channels=True)
    async def set_ticket_category(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel
    ):
        try:
            config = await load_config()
            guild_id_str = str(interaction.guild.id)
            if 'servers' not in config:
                config['servers'] = {}
            if guild_id_str not in config['servers']:
                config['servers'][guild_id_str] = {}

            config['servers'][guild_id_str]['ticket_category_id'] = category.id
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
            await interaction.response.send_message(
                f"✅ Categoría de tickets establecida en: {category.name}",
                ephemeral=True
            )
            logger.info(f"Categoría de tickets establecida a {category.name} por {interaction.user}")

        except Exception as e:
            logger.error(f"Error guardando categoría: {e}")
            await interaction.response.send_message(
                "❌ Ocurrió un error al establecer la categoría del ticket!",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Tickets(bot))
