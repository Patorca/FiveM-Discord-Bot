import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

async def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

async def save_config(config):
    """Save configuration to config.json"""
    try:
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def has_moderation_permission(user: discord.Member, guild_id: int, config: dict) -> bool:
    """Check if user has moderation permissions"""
    # Administrators always have permission
    if user.guild_permissions.administrator:
        return True
    
    # Check if user has default Discord moderation permissions
    if (user.guild_permissions.ban_members or 
        user.guild_permissions.manage_messages or 
        user.guild_permissions.moderate_members):
        return True
    
    # Check configured moderation roles
    guild_id_str = str(guild_id)
    if ('servers' in config and 
        guild_id_str in config['servers'] and 
        'moderation_role_ids' in config['servers'][guild_id_str]):
        
        moderation_role_ids = config['servers'][guild_id_str]['moderation_role_ids']
        for role_id in moderation_role_ids:
            if discord.utils.get(user.roles, id=role_id):
                return True
    
    return False

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="limpiar", description="Elimina una cantidad específica de mensajes del canal")
    @app_commands.describe(
        cantidad="Número de mensajes a eliminar (máximo 100)",
        usuario="Usuario específico del cual eliminar mensajes (opcional)"
    )
    async def clear_messages(
        self, 
        interaction: discord.Interaction, 
        cantidad: int,
        usuario: Optional[discord.Member] = None
    ):
        """Delete a specified number of messages from the channel"""
        try:
            # Verificar permisos de moderación
            config = await load_config()
            if not has_moderation_permission(interaction.user, interaction.guild.id, config):
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No tienes permisos para usar comandos de moderación.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Validar cantidad
            if cantidad < 1 or cantidad > 100:
                embed = discord.Embed(
                    title="❌ Cantidad inválida",
                    description="Debes especificar un número entre 1 y 100 mensajes.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Verificar permisos del bot
            if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No tengo permisos para gestionar mensajes en este canal.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)

            # Función para filtrar mensajes por usuario si se especifica
            def check(message):
                if usuario:
                    return message.author == usuario
                return True

            try:
                if usuario:
                    deleted = await interaction.channel.purge(limit=cantidad * 2, check=check)
                    deleted = deleted[:cantidad]  # Limitar a la cantidad solicitada
                else:
                    deleted = await interaction.channel.purge(limit=cantidad)

                # Mensaje de confirmación
                embed = discord.Embed(
                    title="🧹 Mensajes eliminados",
                    description=f"Se eliminaron **{len(deleted)}** mensajes" +
                               (f" de {usuario.mention}" if usuario else "") + ".",
                    color=0x00ff00
                )
                embed.set_footer(
                    text=f"Acción realizada por {interaction.user.display_name}",
                    icon_url=interaction.user.display_avatar.url
                )
                
                confirmation = await interaction.followup.send(embed=embed)
                
                # Auto-eliminar mensaje de confirmación después de 5 segundos
                await asyncio.sleep(5)
                try:
                    await confirmation.delete()
                except:
                    pass

                # Log de la acción
                logger.info(
                    f"Messages cleared: {len(deleted)} messages in {interaction.channel.name} "
                    f"by {interaction.user} ({interaction.user.id})" +
                    (f" from user {usuario}" if usuario else "")
                )

            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No tengo permisos suficientes para eliminar mensajes.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in clear_messages: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al eliminar los mensajes.",
                color=0xff0000
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed)

    @app_commands.command(name="banear", description="Banea a un usuario del servidor")
    @app_commands.describe(
        usuario="Usuario a banear",
        razon="Razón del baneo",
        eliminar_mensajes="Días de mensajes a eliminar (0-7, por defecto 1)"
    )
    async def ban_user(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        razon: Optional[str] = "No especificada",
        eliminar_mensajes: Optional[int] = 1
    ):
        """Ban a user from the server"""
        try:
            # Verificar permisos de moderación
            config = await load_config()
            if not has_moderation_permission(interaction.user, interaction.guild.id, config):
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No tienes permisos para usar comandos de moderación.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            # Validaciones de seguridad
            if usuario == interaction.user:
                embed = discord.Embed(
                    title="❌ Acción inválida",
                    description="No puedes banearte a ti mismo.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if usuario == interaction.guild.owner:
                embed = discord.Embed(
                    title="❌ Acción inválida",
                    description="No puedes banear al dueño del servidor.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if usuario.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No puedes banear a alguien con un rol igual o superior al tuyo.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if usuario.top_role >= interaction.guild.me.top_role:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No puedo banear a alguien con un rol igual o superior al mío.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Validar días de eliminación de mensajes
            if eliminar_mensajes < 0 or eliminar_mensajes > 7:
                eliminar_mensajes = 1

            await interaction.response.defer(ephemeral=True)

            # Intentar enviar DM al usuario antes del baneo
            try:
                dm_embed = discord.Embed(
                    title="🔨 Has sido baneado",
                    description=f"Has sido baneado del servidor **{interaction.guild.name}**",
                    color=0xff0000
                )
                dm_embed.add_field(name="Razón", value=razon, inline=False)
                dm_embed.add_field(
                    name="Moderador", 
                    value=interaction.user.display_name, 
                    inline=False
                )
                dm_embed.set_footer(text=f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                await usuario.send(embed=dm_embed)
                dm_sent = True
            except (discord.Forbidden, discord.HTTPException):
                dm_sent = False

            # Ejecutar el baneo
            await usuario.ban(
                reason=f"Baneado por {interaction.user} - {razon}",
                delete_message_days=eliminar_mensajes
            )

            # Mensaje de confirmación
            embed = discord.Embed(
                title="🔨 Usuario baneado",
                description=f"**{usuario.display_name}** ha sido baneado del servidor.",
                color=0xff0000
            )
            embed.add_field(name="Usuario", value=f"{usuario.mention} ({usuario.id})", inline=True)
            embed.add_field(name="Moderador", value=interaction.user.mention, inline=True)
            embed.add_field(name="Razón", value=razon, inline=False)
            embed.add_field(
                name="Mensajes eliminados", 
                value=f"{eliminar_mensajes} día{'s' if eliminar_mensajes != 1 else ''}", 
                inline=True
            )
            embed.add_field(
                name="DM enviado", 
                value="✅ Sí" if dm_sent else "❌ No", 
                inline=True
            )
            embed.set_footer(
                text=f"ID del usuario: {usuario.id}",
                icon_url=usuario.display_avatar.url
            )

            await interaction.followup.send(embed=embed)

            # Log de la acción
            logger.info(
                f"User banned: {usuario} ({usuario.id}) by {interaction.user} "
                f"({interaction.user.id}) in {interaction.guild.name} - Reason: {razon}"
            )

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="No tengo permisos para banear usuarios.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in ban_user: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al banear al usuario.",
                color=0xff0000
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed)

    @app_commands.command(name="timeout", description="Silencia temporalmente a un usuario")
    @app_commands.describe(
        usuario="Usuario a silenciar",
        duracion="Duración en minutos (máximo 40320 = 28 días)",
        razon="Razón del timeout"
    )
    async def timeout_user(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        duracion: int,
        razon: Optional[str] = "No especificada"
    ):
        """Timeout a user for a specified duration"""
        try:
            # Verificar permisos de moderación
            config = await load_config()
            if not has_moderation_permission(interaction.user, interaction.guild.id, config):
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No tienes permisos para usar comandos de moderación.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            # Validaciones de seguridad
            if usuario == interaction.user:
                embed = discord.Embed(
                    title="❌ Acción inválida",
                    description="No puedes silenciarte a ti mismo.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if usuario == interaction.guild.owner:
                embed = discord.Embed(
                    title="❌ Acción inválida",
                    description="No puedes silenciar al dueño del servidor.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if usuario.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No puedes silenciar a alguien con un rol igual o superior al tuyo.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if usuario.top_role >= interaction.guild.me.top_role:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No puedo silenciar a alguien con un rol igual o superior al mío.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Validar duración
            if duracion < 1 or duracion > 40320:  # 40320 minutos = 28 días (límite de Discord)
                embed = discord.Embed(
                    title="❌ Duración inválida",
                    description="La duración debe estar entre 1 minuto y 40320 minutos (28 días).",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)

            # Calcular tiempo de finalización
            until = datetime.utcnow() + timedelta(minutes=duracion)

            # Intentar enviar DM al usuario antes del timeout
            try:
                dm_embed = discord.Embed(
                    title="🔇 Has sido silenciado",
                    description=f"Has sido silenciado en **{interaction.guild.name}**",
                    color=0xff8000
                )
                dm_embed.add_field(name="Duración", value=f"{duracion} minutos", inline=True)
                dm_embed.add_field(name="Razón", value=razon, inline=False)
                dm_embed.add_field(
                    name="Moderador", 
                    value=interaction.user.display_name, 
                    inline=False
                )
                dm_embed.add_field(
                    name="Finaliza",
                    value=f"<t:{int(until.timestamp())}:f>",
                    inline=False
                )
                
                await usuario.send(embed=dm_embed)
                dm_sent = True
            except (discord.Forbidden, discord.HTTPException):
                dm_sent = False

            # Ejecutar el timeout
            await usuario.timeout(
                until=until,
                reason=f"Timeout por {interaction.user} - {razon}"
            )

            # Mensaje de confirmación
            embed = discord.Embed(
                title="🔇 Usuario silenciado",
                description=f"**{usuario.display_name}** ha sido silenciado.",
                color=0xff8000
            )
            embed.add_field(name="Usuario", value=f"{usuario.mention} ({usuario.id})", inline=True)
            embed.add_field(name="Moderador", value=interaction.user.mention, inline=True)
            embed.add_field(name="Duración", value=f"{duracion} minutos", inline=True)
            embed.add_field(name="Razón", value=razon, inline=False)
            embed.add_field(
                name="Finaliza",
                value=f"<t:{int(until.timestamp())}:f>",
                inline=True
            )
            embed.add_field(
                name="DM enviado", 
                value="✅ Sí" if dm_sent else "❌ No", 
                inline=True
            )
            embed.set_footer(
                text=f"ID del usuario: {usuario.id}",
                icon_url=usuario.display_avatar.url
            )

            await interaction.followup.send(embed=embed)

            # Log de la acción
            logger.info(
                f"User timed out: {usuario} ({usuario.id}) by {interaction.user} "
                f"({interaction.user.id}) for {duracion} minutes - Reason: {razon}"
            )

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="No tengo permisos para silenciar usuarios.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in timeout_user: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al silenciar al usuario.",
                color=0xff0000
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed)

    @app_commands.command(name="quitar-timeout", description="Quita el silencio de un usuario")
    @app_commands.describe(usuario="Usuario al que quitar el silencio")
    async def remove_timeout(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member
    ):
        """Remove timeout from a user"""
        try:
            # Verificar permisos de moderación
            config = await load_config()
            if not has_moderation_permission(interaction.user, interaction.guild.id, config):
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="No tienes permisos para usar comandos de moderación.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            if not usuario.is_timed_out():
                embed = discord.Embed(
                    title="ℹ️ Usuario no silenciado",
                    description=f"**{usuario.display_name}** no está actualmente silenciado.",
                    color=0x3498db
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)

            # Quitar el timeout
            await usuario.timeout(until=None)

            # Mensaje de confirmación
            embed = discord.Embed(
                title="🔊 Silencio removido",
                description=f"Se ha quitado el silencio a **{usuario.display_name}**.",
                color=0x00ff00
            )
            embed.add_field(name="Usuario", value=f"{usuario.mention} ({usuario.id})", inline=True)
            embed.add_field(name="Moderador", value=interaction.user.mention, inline=True)
            embed.set_footer(
                text=f"ID del usuario: {usuario.id}",
                icon_url=usuario.display_avatar.url
            )

            await interaction.followup.send(embed=embed)

            # Log de la acción
            logger.info(
                f"Timeout removed: {usuario} ({usuario.id}) by {interaction.user} "
                f"({interaction.user.id}) in {interaction.guild.name}"
            )

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="No tengo permisos para quitar timeouts.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in remove_timeout: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al quitar el silencio.",
                color=0xff0000
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed)

    @app_commands.command(name="set-moderator-role", description="Establecer rol que puede usar comandos de moderación")
    @app_commands.describe(role="Rol que podrá usar comandos de moderación")
    @app_commands.default_permissions(administrator=True)
    async def set_moderator_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """Add a role to moderation permissions"""
        try:
            config = await load_config()
            guild_id_str = str(interaction.guild.id)
            if 'servers' not in config:
                config['servers'] = {}
            if guild_id_str not in config['servers']:
                config['servers'][guild_id_str] = {}
            if 'moderation_role_ids' not in config['servers'][guild_id_str]:
                config['servers'][guild_id_str]['moderation_role_ids'] = []

            # Agregar el rol si no está ya en la lista
            if role.id not in config['servers'][guild_id_str]['moderation_role_ids']:
                config['servers'][guild_id_str]['moderation_role_ids'].append(role.id)
                
                await save_config(config)
                
                embed = discord.Embed(
                    title="✅ Rol de moderación agregado",
                    description=f"Rol agregado: {role.mention}\n"
                               f"Los miembros con este rol ahora pueden usar comandos de moderación.",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Moderation role {role.name} added by {interaction.user}")
            else:
                embed = discord.Embed(
                    title="⚠️ Rol ya configurado",
                    description=f"El rol {role.mention} ya está configurado como rol de moderación.",
                    color=0xffaa00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error setting moderator role: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al establecer el rol de moderación.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="remove-moderator-role", description="Remover rol de los comandos de moderación")
    @app_commands.describe(role="Rol a remover de los roles de moderación")
    @app_commands.default_permissions(administrator=True)
    async def remove_moderator_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """Remove a role from moderation permissions"""
        try:
            config = await load_config()
            guild_id_str = str(interaction.guild.id)
            
            if ('servers' not in config or 
                guild_id_str not in config['servers'] or 
                'moderation_role_ids' not in config['servers'][guild_id_str]):
                embed = discord.Embed(
                    title="❌ No hay roles configurados",
                    description="No hay roles de moderación configurados en este servidor.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if role.id in config['servers'][guild_id_str]['moderation_role_ids']:
                config['servers'][guild_id_str]['moderation_role_ids'].remove(role.id)
                
                await save_config(config)
                
                embed = discord.Embed(
                    title="✅ Rol de moderación removido",
                    description=f"Rol removido: {role.mention}",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Moderation role {role.name} removed by {interaction.user}")
            else:
                embed = discord.Embed(
                    title="⚠️ Rol no configurado",
                    description=f"El rol {role.mention} no está configurado como rol de moderación.",
                    color=0xffaa00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error removing moderator role: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al remover el rol de moderación.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="moderation-info", description="Mostrar configuración actual del sistema de moderación")
    @app_commands.default_permissions(administrator=True)
    async def moderation_info(
        self,
        interaction: discord.Interaction
    ):
        """Show current moderation configuration"""
        try:
            config = await load_config()
            guild_id_str = str(interaction.guild.id)
            server_config = config.get('servers', {}).get(guild_id_str, {})
            
            embed = discord.Embed(
                title="🛡️ Configuración del Sistema de Moderación",
                color=0x3498db
            )
            
            # Roles de moderación configurados
            moderation_role_ids = server_config.get('moderation_role_ids', [])
            if moderation_role_ids:
                moderation_roles = []
                for role_id in moderation_role_ids:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        moderation_roles.append(role.mention)
                    else:
                        moderation_roles.append(f"⚠️ Rol no encontrado (ID: {role_id})")
                roles_text = "\n".join(moderation_roles)
            else:
                roles_text = "No configurados"
            
            embed.add_field(
                name="👮 Roles de Moderación",
                value=roles_text,
                inline=False
            )
            
            # Información sobre permisos predeterminados
            embed.add_field(
                name="🔐 Permisos Predeterminados",
                value="• Administradores\n• Usuarios con permiso `Banear miembros`\n• Usuarios con permiso `Gestionar mensajes`\n• Usuarios con permiso `Moderar miembros`",
                inline=False
            )
            
            # Comandos disponibles
            embed.add_field(
                name="⚙️ Comandos Disponibles",
                value="• `/limpiar` - Eliminar mensajes\n• `/banear` - Banear usuarios\n• `/timeout` - Silenciar usuarios\n• `/quitar-timeout` - Quitar silencio",
                inline=False
            )
            
            embed.set_footer(text=f"Servidor: {interaction.guild.name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error showing moderation info: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al mostrar la información de moderación.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))