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

            # Mencionar todos los roles de staff configurados
            staff_role_ids = server_config.get('staff_role_ids', [])
            staff_mentions = []
            
            for role_id in staff_role_ids:
                staff_role = guild.get_role(role_id)
                if staff_role:
                    staff_mentions.append(staff_role.mention)
            
            # Enviar mensaje inicial con menciones de staff (si hay roles configurados)
            if staff_mentions:
                mentions_text = " ".join(staff_mentions)
                await ticket_channel.send(f"{mentions_text} - Nuevo ticket creado por {user.mention}")

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

                # Siempre intentar enviar DM al creador del ticket
                try:
                    transcript_file_dm = io.StringIO(transcript_content)
                    file_dm = discord.File(transcript_file_dm, filename=f"transcript-{channel.name}.txt")
                    dm_embed = discord.Embed(
                        title="📝 Transcript de tu Ticket",
                        description=(
                            f"Tu ticket en **{channel.guild.name}** ha sido cerrado.\n"
                            "Aquí tienes el transcript completo de la conversación.\n\n"
                            f"**Cerrado por:** {user.display_name}\n"
                            f"**Fecha de cierre:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        ),
                        color=0x3498db
                    )
                    dm_embed.set_footer(text=f"Servidor: {channel.guild.name}")
                    await ticket_creator.send(embed=dm_embed, file=file_dm)
                    logger.info(f"Transcript DM enviado exitosamente a {ticket_creator} ({ticket_creator.id})")
                except discord.Forbidden:
                    logger.warning(f"No se pudo enviar transcript DM a {ticket_creator} - DMs deshabilitados")
                    # Intentar notificar en el servidor si no se puede enviar DM
                    try:
                        notification_embed = discord.Embed(
                            title="⚠️ No se pudo enviar transcript por DM",
                            description=(
                                f"{ticket_creator.mention}, tu ticket ha sido cerrado pero no pudimos enviarte el transcript por DM.\n"
                                "Por favor, habilita los mensajes directos para recibir transcripts en el futuro."
                            ),
                            color=0xffaa00
                        )
                        if transcript_channel_id:
                            transcript_channel = channel.guild.get_channel(transcript_channel_id)
                            if transcript_channel:
                                await transcript_channel.send(embed=notification_embed)
                    except Exception as notif_error:
                        logger.error(f"Error enviando notificación de DM fallido: {notif_error}")
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

    @app_commands.command(name="set-staff-role", description="Establecer rol de staff para gestionar tickets")
    @app_commands.describe(role="Rol que podrá cerrar y gestionar tickets")
    @app_commands.default_permissions(manage_roles=True)
    async def set_staff_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        try:
            config = await load_config()
            guild_id_str = str(interaction.guild.id)
            if 'servers' not in config:
                config['servers'] = {}
            if guild_id_str not in config['servers']:
                config['servers'][guild_id_str] = {}
            if 'staff_role_ids' not in config['servers'][guild_id_str]:
                config['servers'][guild_id_str]['staff_role_ids'] = []

            # Agregar el rol si no está ya en la lista
            if role.id not in config['servers'][guild_id_str]['staff_role_ids']:
                config['servers'][guild_id_str]['staff_role_ids'].append(role.id)
                
                with open('config.json', 'w') as f:
                    json.dump(config, f, indent=2)
                
                await interaction.response.send_message(
                    f"✅ Rol de staff agregado: {role.mention}\n"
                    f"Los miembros con este rol ahora pueden cerrar y gestionar tickets.",
                    ephemeral=True
                )
                logger.info(f"Rol de staff {role.name} agregado por {interaction.user}")
            else:
                await interaction.response.send_message(
                    f"⚠️ El rol {role.mention} ya está configurado como rol de staff.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error guardando rol de staff: {e}")
            await interaction.response.send_message(
                "❌ Ocurrió un error al establecer el rol de staff!",
                ephemeral=True
            )

    @app_commands.command(name="remove-staff-role", description="Remover rol de staff de la gestión de tickets")
    @app_commands.describe(role="Rol a remover de los roles de staff")
    @app_commands.default_permissions(manage_roles=True)
    async def remove_staff_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        try:
            config = await load_config()
            guild_id_str = str(interaction.guild.id)
            
            if ('servers' not in config or 
                guild_id_str not in config['servers'] or 
                'staff_role_ids' not in config['servers'][guild_id_str]):
                await interaction.response.send_message(
                    "❌ No hay roles de staff configurados en este servidor.",
                    ephemeral=True
                )
                return

            if role.id in config['servers'][guild_id_str]['staff_role_ids']:
                config['servers'][guild_id_str]['staff_role_ids'].remove(role.id)
                
                with open('config.json', 'w') as f:
                    json.dump(config, f, indent=2)
                
                await interaction.response.send_message(
                    f"✅ Rol de staff removido: {role.mention}",
                    ephemeral=True
                )
                logger.info(f"Rol de staff {role.name} removido por {interaction.user}")
            else:
                await interaction.response.send_message(
                    f"⚠️ El rol {role.mention} no está configurado como rol de staff.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error removiendo rol de staff: {e}")
            await interaction.response.send_message(
                "❌ Ocurrió un error al remover el rol de staff!",
                ephemeral=True
            )

    @app_commands.command(name="set-transcript-channel", description="Establecer canal para enviar transcripts de tickets")
    @app_commands.describe(channel="Canal donde se enviarán los transcripts")
    @app_commands.default_permissions(manage_channels=True)
    async def set_transcript_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        try:
            # Verificar que el bot tiene permisos en el canal
            bot_perms = channel.permissions_for(interaction.guild.me)
            if not bot_perms.send_messages or not bot_perms.embed_links or not bot_perms.attach_files:
                await interaction.response.send_message(
                    f"❌ No tengo permisos suficientes en {channel.mention}!\n"
                    "Necesito permisos para: enviar mensajes, embeds y archivos adjuntos.",
                    ephemeral=True
                )
                return

            config = await load_config()
            guild_id_str = str(interaction.guild.id)
            if 'servers' not in config:
                config['servers'] = {}
            if guild_id_str not in config['servers']:
                config['servers'][guild_id_str] = {}

            config['servers'][guild_id_str]['transcript_channel_id'] = channel.id
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            await interaction.response.send_message(
                f"✅ Canal de transcripts establecido en: {channel.mention}\n"
                f"Los transcripts de los tickets cerrados se enviarán a este canal.",
                ephemeral=True
            )
            logger.info(f"Canal de transcripts establecido a {channel.name} por {interaction.user}")

        except Exception as e:
            logger.error(f"Error guardando canal de transcripts: {e}")
            await interaction.response.send_message(
                "❌ Ocurrió un error al establecer el canal de transcripts!",
                ephemeral=True
            )

    @app_commands.command(name="remove-transcript-channel", description="Desactivar el envío de transcripts a canal específico")
    @app_commands.default_permissions(manage_channels=True)
    async def remove_transcript_channel(
        self,
        interaction: discord.Interaction
    ):
        try:
            config = await load_config()
            guild_id_str = str(interaction.guild.id)
            
            if ('servers' not in config or 
                guild_id_str not in config['servers'] or 
                'transcript_channel_id' not in config['servers'][guild_id_str]):
                await interaction.response.send_message(
                    "❌ No hay canal de transcripts configurado en este servidor.",
                    ephemeral=True
                )
                return

            del config['servers'][guild_id_str]['transcript_channel_id']
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            await interaction.response.send_message(
                "✅ Canal de transcripts desactivado.\n"
                "Los transcripts solo se enviarán por DM al usuario.",
                ephemeral=True
            )
            logger.info(f"Canal de transcripts desactivado por {interaction.user}")

        except Exception as e:
            logger.error(f"Error desactivando canal de transcripts: {e}")
            await interaction.response.send_message(
                "❌ Ocurrió un error al desactivar el canal de transcripts!",
                ephemeral=True
            )

    @app_commands.command(name="ticket-info", description="Mostrar configuración actual del sistema de tickets")
    @app_commands.default_permissions(manage_channels=True)
    async def ticket_info(
        self,
        interaction: discord.Interaction
    ):
        try:
            config = await load_config()
            guild_id_str = str(interaction.guild.id)
            server_config = config.get('servers', {}).get(guild_id_str, {})
            
            embed = discord.Embed(
                title="🎫 Configuración del Sistema de Tickets",
                color=0x3498db
            )
            
            # Categoría de tickets
            category_id = server_config.get('ticket_category_id')
            if category_id:
                category = interaction.guild.get_channel(category_id)
                category_text = category.name if category else "⚠️ Categoría no encontrada"
            else:
                category_text = "No configurada"
            embed.add_field(
                name="📁 Categoría de Tickets",
                value=category_text,
                inline=False
            )
            
            # Roles de staff
            staff_role_ids = server_config.get('staff_role_ids', [])
            if staff_role_ids:
                staff_roles = []
                for role_id in staff_role_ids:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        staff_roles.append(role.mention)
                    else:
                        staff_roles.append(f"⚠️ Rol no encontrado (ID: {role_id})")
                staff_text = "\n".join(staff_roles)
            else:
                staff_text = "No configurados"
            embed.add_field(
                name="👮 Roles de Staff",
                value=staff_text,
                inline=False
            )
            
            # Canal de transcripts
            transcript_channel_id = server_config.get('transcript_channel_id')
            if transcript_channel_id:
                transcript_channel = interaction.guild.get_channel(transcript_channel_id)
                transcript_text = transcript_channel.mention if transcript_channel else "⚠️ Canal no encontrado"
            else:
                transcript_text = "No configurado"
            embed.add_field(
                name="📝 Canal de Transcripts",
                value=transcript_text,
                inline=False
            )
            
            embed.set_footer(text=f"Servidor: {interaction.guild.name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error mostrando info de tickets: {e}")
            await interaction.response.send_message(
                "❌ Ocurrió un error al mostrar la información de tickets!",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Tickets(bot))
