import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import asyncio
import logging
import re
import json
from datetime import datetime
from typing import Dict, List, Optional

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

class FiveMStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_url = "https://status.cfx.re"
        self.server_monitors = {}  # guild_id -> {channel_id, message_id}
        self.last_status = {}
        self.config_loaded = False
        
    async def setup_monitor_from_config(self):
        """Load monitor configuration from config file"""
        try:
            config = await load_config()
            if 'servers' in config:
                for guild_id_str, server_config in config['servers'].items():
                    guild_id = int(guild_id_str)
                    channel_id = server_config.get('fivem_status_channel_id')
                    message_id = server_config.get('fivem_status_message_id')
                    
                    if channel_id and message_id:
                        # Verificar que el canal y mensaje existen
                        try:
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                await channel.fetch_message(message_id)
                                self.server_monitors[guild_id] = {
                                    'channel_id': channel_id,
                                    'message_id': message_id
                                }
                                logger.info(f"Loaded FiveM monitor for guild {guild_id}: channel={channel_id}, message={message_id}")
                            else:
                                logger.warning(f"FiveM status channel not found for guild {guild_id}, skipping")
                        except discord.NotFound:
                            logger.warning(f"FiveM status message not found for guild {guild_id}, clearing message ID")
                            # Limpiar mensaje ID inválido
                            config['servers'][guild_id_str]['fivem_status_message_id'] = None
                            await save_config(config)
                        except Exception as e:
                            logger.error(f"Error validating FiveM status message for guild {guild_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error loading FiveM monitor config: {e}")
        
        # Start the monitor
        if not self.status_monitor.is_running():
            self.status_monitor.start()
        
    async def cog_load(self):
        """Called when the cog is loaded"""
        await self.setup_monitor_from_config()
    
    async def cog_unload(self):
        """Called when the cog is unloaded"""
        self.status_monitor.cancel()
    
    async def fetch_fivem_status(self) -> Dict[str, str]:
        """Fetch the current FiveM service status"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.status_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self.parse_status_content(content)
                    else:
                        logger.error(f"Error fetching status: HTTP {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error fetching FiveM status: {e}")
            return {}
    
    def parse_status_content(self, content: str) -> Dict[str, str]:
        """Parse the status page content to extract service statuses"""
        status_dict = {}
        
        # Map of service patterns and their display names
        services = {
            "FiveM": "🎮 FiveM",
            "RedM": "🤠 RedM", 
            "Cfx.re Platform Server \\(FXServer\\)": "🖥️ FXServer",
            "Game Services": "🎯 Game Services",
            "CnL": "🔗 CnL",
            "Policy": "📋 Policy",
            "Keymaster": "🔑 Keymaster",
            "Web Services": "🌐 Web Services",
            "Forums": "💬 Forums",
            "Server List Frontend": "📋 Server List",
            "\"Runtime\"": "⚡ Runtime",
            "IDMS": "🆔 IDMS",
            "Portal": "🚪 Portal"
        }
        
        # Look for operational status indicators
        for service_pattern, display_name in services.items():
            # Create regex pattern to find service status
            pattern = rf"{service_pattern}.*?(?:Operational|Degraded Performance|Partial Outage|Major Outage|Maintenance)"
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            
            if match:
                text = match.group(0)
                if "Operational" in text:
                    status_dict[display_name] = "🟢 Operativo"
                elif "Degraded Performance" in text:
                    status_dict[display_name] = "🟡 Rendimiento Degradado"
                elif "Partial Outage" in text:
                    status_dict[display_name] = "🟠 Falla Parcial"
                elif "Major Outage" in text:
                    status_dict[display_name] = "🔴 Falla Mayor"
                elif "Maintenance" in text:
                    status_dict[display_name] = "🔧 Mantenimiento"
                else:
                    status_dict[display_name] = "❓ Desconocido"
            else:
                status_dict[display_name] = "❓ No disponible"
        
        # Check overall system status
        if "All Systems Operational" in content:
            status_dict["overall"] = "🟢 Todos los sistemas operativos"
        elif "Some Systems Experiencing Issues" in content:
            status_dict["overall"] = "🟡 Algunos sistemas con problemas"
        elif "Major Service Outage" in content:
            status_dict["overall"] = "🔴 Falla mayor del servicio"
        else:
            status_dict["overall"] = "❓ Estado general desconocido"
            
        return status_dict
    
    def create_status_embed(self, status_data: Dict[str, str]) -> discord.Embed:
        """Create an embed with the current FiveM status"""
        # Determine embed color based on overall status
        if "🟢" in status_data.get("overall", ""):
            color = 0x00ff00  # Green
        elif "🟡" in status_data.get("overall", ""):
            color = 0xffff00  # Yellow
        elif "🟠" in status_data.get("overall", ""):
            color = 0xff8000  # Orange
        elif "🔴" in status_data.get("overall", ""):
            color = 0xff0000  # Red
        else:
            color = 0x808080  # Gray
        
        embed = discord.Embed(
            title="📊 Estado de los Servidores FiveM",
            description=f"**Estado General:** {status_data.get('overall', 'Desconocido')}\n\n"
                       f"Información actualizada desde [status.cfx.re]({self.status_url})",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        # Main gaming services
        gaming_services = []
        for service, status in status_data.items():
            if service in ["🎮 FiveM", "🤠 RedM", "🖥️ FXServer", "🎯 Game Services"]:
                gaming_services.append(f"{service}: {status}")
        
        if gaming_services:
            embed.add_field(
                name="🎮 **Servicios de Juego**",
                value="\n".join(gaming_services),
                inline=False
            )
        
        # Platform services
        platform_services = []
        for service, status in status_data.items():
            if service in ["🔗 CnL", "📋 Policy", "🔑 Keymaster", "🌐 Web Services"]:
                platform_services.append(f"{service}: {status}")
        
        if platform_services:
            embed.add_field(
                name="🛠️ **Servicios de Plataforma**",
                value="\n".join(platform_services),
                inline=False
            )
        
        # Community services
        community_services = []
        for service, status in status_data.items():
            if service in ["💬 Forums", "📋 Server List", "⚡ Runtime", "🆔 IDMS", "🚪 Portal"]:
                community_services.append(f"{service}: {status}")
        
        if community_services:
            embed.add_field(
                name="👥 **Servicios de Comunidad**",
                value="\n".join(community_services),
                inline=False
            )
        
        embed.set_footer(
            text="🔄 Actualizado automáticamente cada 5 minutos • PT Scripts BOT",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        return embed
        
    async def load_config_and_start(self):
        """Load configuration on first monitor run"""
        try:
            config = await load_config()
            if 'servers' in config:
                for guild_id_str, server_config in config['servers'].items():
                    guild_id = int(guild_id_str)
                    channel_id = server_config.get('fivem_status_channel_id')
                    message_id = server_config.get('fivem_status_message_id')
                    
                    if channel_id and message_id:
                        # Verificar que el canal y mensaje existen
                        try:
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                await channel.fetch_message(message_id)
                                self.server_monitors[guild_id] = {
                                    'channel_id': channel_id,
                                    'message_id': message_id
                                }
                                logger.info(f"Loaded FiveM monitor for guild {guild_id}: channel={channel_id}, message={message_id}")
                            else:
                                logger.warning(f"FiveM status channel not found for guild {guild_id}, skipping")
                        except discord.NotFound:
                            logger.warning(f"FiveM status message not found for guild {guild_id}, clearing message ID")
                            # Limpiar mensaje ID inválido
                            config['servers'][guild_id_str]['fivem_status_message_id'] = None
                            await save_config(config)
                        except Exception as e:
                            logger.error(f"Error validating FiveM status message for guild {guild_id}: {e}")
                        
            self.config_loaded = True
                        
        except Exception as e:
            logger.error(f"Error loading FiveM monitor config on startup: {e}")
            self.config_loaded = True  # Mark as loaded even if failed to prevent repeated attempts
    
    @tasks.loop(minutes=5)
    async def status_monitor(self):
        """Monitor FiveM status every 5 minutes and update all server messages"""
        try:
            # Check if we need to load configuration
            if not self.config_loaded or not self.server_monitors:
                await self.load_config_and_start()
                if not self.server_monitors:
                    logger.debug("Status monitor: No monitors configured after loading config")
                    return
            
            logger.info("Status monitor: Checking FiveM status...")
            status_data = await self.fetch_fivem_status()
            if not status_data:
                logger.error("Status monitor: Failed to fetch status data")
                return
            
            # Always update the message (not just when status changes) to show it's active
            self.last_status = status_data
            embed = self.create_status_embed(status_data)
            
            # Update messages for all configured servers
            for guild_id, monitor_config in self.server_monitors.items():
                channel_id = monitor_config['channel_id']
                message_id = monitor_config['message_id']
                
                # Get the channel and message
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    logger.error(f"Status monitor: Channel {channel_id} not found for guild {guild_id}")
                    continue
                
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed)
                    logger.info(f"Status monitor: FiveM status message updated successfully for guild {guild_id}")
                except discord.NotFound:
                    # Message was deleted, remove from config and memory
                    logger.warning(f"Status monitor: Message not found for guild {guild_id}, removing from config")
                    del self.server_monitors[guild_id]
                    # Update config file
                    try:
                        config = await load_config()
                        if 'servers' in config and str(guild_id) in config['servers']:
                            config['servers'][str(guild_id)]['fivem_status_message_id'] = None
                            await save_config(config)
                    except Exception as config_error:
                        logger.error(f"Error updating config after message deletion: {config_error}")
                except Exception as e:
                    logger.error(f"Status monitor: Error updating message for guild {guild_id}: {e}")
            
        except Exception as e:
            logger.error(f"Status monitor: Unexpected error: {e}")
    
    @status_monitor.before_loop
    async def before_status_monitor(self):
        await self.bot.wait_until_ready()
        logger.info("FiveM status monitor waiting for bot ready...")
    
    @app_commands.command(name="estado_fivem", description="Muestra el estado actual de los servidores de FiveM")
    async def fivem_status_command(self, interaction: discord.Interaction):
        """Show current FiveM server status"""
        try:
            await interaction.response.defer()
            
            status_data = await self.fetch_fivem_status()
            
            if not status_data:
                embed = discord.Embed(
                    title="❌ Error",
                    description="No se pudo obtener el estado de los servidores FiveM.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            
            embed = self.create_status_embed(status_data)
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in fivem_status_command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al obtener el estado de FiveM.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="configurar_estado_fivem", description="Configura el monitoreo automático del estado de FiveM")
    @app_commands.describe(canal="Canal donde se mostrará el estado de FiveM")
    async def setup_fivem_monitor(self, interaction: discord.Interaction, canal: discord.TextChannel):
        """Setup automatic FiveM status monitoring"""
        try:
            # Check permissions
            if not interaction.user.guild_permissions.administrator:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="Necesitas permisos de administrador para usar este comando.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Get initial status
            status_data = await self.fetch_fivem_status()
            if not status_data:
                embed = discord.Embed(
                    title="❌ Error",
                    description="No se pudo obtener el estado inicial de FiveM.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create and send the status message
            embed = self.create_status_embed(status_data)
            message = await canal.send(embed=embed)
            
            # Store the message and channel info for this guild
            guild_id = interaction.guild.id
            self.server_monitors[guild_id] = {
                'channel_id': canal.id,
                'message_id': message.id
            }
            self.last_status = status_data
            
            # Save to config file for persistence
            try:
                config = await load_config()
                guild_id_str = str(interaction.guild.id)
                if 'servers' not in config:
                    config['servers'] = {}
                if guild_id_str not in config['servers']:
                    config['servers'][guild_id_str] = {}
                
                config['servers'][guild_id_str]['fivem_status_channel_id'] = canal.id
                config['servers'][guild_id_str]['fivem_status_message_id'] = message.id
                
                await save_config(config)
                logger.info(f"FiveM monitor config saved: channel={canal.id}, message={message.id}")
            except Exception as e:
                logger.error(f"Error saving FiveM monitor config: {e}")
            
            # Confirmation message
            confirmation_embed = discord.Embed(
                title="✅ Monitoreo configurado",
                description=f"El estado de FiveM se mostrará en {canal.mention} y se actualizará automáticamente cada 5 minutos.\n\n"
                           f"**El monitoreo persistirá** incluso si el bot se reinicia.",
                color=0x00ff00
            )
            await interaction.followup.send(embed=confirmation_embed)
            
            logger.info(f"FiveM status monitor configured for channel {canal.id}")
            
        except Exception as e:
            logger.error(f"Error in setup_fivem_monitor: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al configurar el monitoreo de FiveM.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="desactivar_estado_fivem", description="Desactiva el monitoreo automático del estado de FiveM")
    async def disable_fivem_monitor(self, interaction: discord.Interaction):
        """Disable automatic FiveM status monitoring"""
        try:
            # Check permissions
            if not interaction.user.guild_permissions.administrator:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="Necesitas permisos de administrador para usar este comando.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            guild_id = interaction.guild.id
            if guild_id not in self.server_monitors:
                embed = discord.Embed(
                    title="ℹ️ Sin configuración",
                    description="El monitoreo de FiveM no está actualmente configurado para este servidor.",
                    color=0x3498db
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Clear the configuration for this guild
            del self.server_monitors[guild_id]
            
            # Remove from config file
            try:
                config = await load_config()
                guild_id_str = str(interaction.guild.id)
                if ('servers' in config and 
                    guild_id_str in config['servers']):
                    
                    if 'fivem_status_channel_id' in config['servers'][guild_id_str]:
                        del config['servers'][guild_id_str]['fivem_status_channel_id']
                    if 'fivem_status_message_id' in config['servers'][guild_id_str]:
                        del config['servers'][guild_id_str]['fivem_status_message_id']
                    
                    await save_config(config)
                    logger.info("FiveM monitor config removed from file")
            except Exception as e:
                logger.error(f"Error removing FiveM monitor config: {e}")
            
            embed = discord.Embed(
                title="✅ Monitoreo desactivado",
                description="El monitoreo automático del estado de FiveM ha sido desactivado.",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
            
            logger.info("FiveM status monitor disabled")
            
        except Exception as e:
            logger.error(f"Error in disable_fivem_monitor: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al desactivar el monitoreo de FiveM.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="forzar_actualizacion_fivem", description="Fuerza una actualización manual del estado de FiveM")
    async def force_update_fivem(self, interaction: discord.Interaction):
        """Force manual update of FiveM status"""
        try:
            # Check permissions
            if not interaction.user.guild_permissions.manage_guild:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description="Necesitas permisos para gestionar el servidor para usar este comando.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            guild_id = interaction.guild.id
            if guild_id not in self.server_monitors:
                embed = discord.Embed(
                    title="ℹ️ Sin configuración",
                    description="El monitoreo de FiveM no está configurado para este servidor. Usa `/configurar_estado_fivem` primero.",
                    color=0x3498db
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Force run the status monitor
            logger.info(f"Manual FiveM status update requested by {interaction.user}")
            await self.status_monitor()
            
            embed = discord.Embed(
                title="✅ Actualización forzada",
                description="Se ha forzado una actualización del estado de FiveM.",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in force_update_fivem: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al forzar la actualización.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="info_monitor_fivem", description="Muestra información sobre el monitoreo de FiveM")
    async def monitor_info_fivem(self, interaction: discord.Interaction):
        """Show information about FiveM monitoring"""
        try:
            guild_id = interaction.guild.id
            embed = discord.Embed(
                title="📊 Información del Monitor FiveM",
                color=0x3498db
            )
            
            if guild_id in self.server_monitors:
                monitor_config = self.server_monitors[guild_id]
                channel = self.bot.get_channel(monitor_config['channel_id'])
                
                embed.add_field(
                    name="Estado del Monitor",
                    value="🟢 Activo",
                    inline=True
                )
                embed.add_field(
                    name="Canal Configurado",
                    value=channel.mention if channel else f"❌ Canal no encontrado (ID: {monitor_config['channel_id']})",
                    inline=True
                )
                embed.add_field(
                    name="Frecuencia de Actualización",
                    value="⏰ Cada 5 minutos",
                    inline=True
                )
                embed.add_field(
                    name="ID del Mensaje",
                    value=f"`{monitor_config['message_id']}`",
                    inline=True
                )
                embed.add_field(
                    name="Loop Status",
                    value="🔄 Ejecutándose" if self.status_monitor.is_running() else "❌ Detenido",
                    inline=True
                )
                embed.add_field(
                    name="Próxima Actualización",
                    value=f"<t:{int(self.status_monitor.next_iteration.timestamp())}:R>" if self.status_monitor.next_iteration else "Desconocido",
                    inline=True
                )
                
                # Add global monitor information
                embed.add_field(
                    name="Servidores Monitoreados",
                    value=f"{len(self.server_monitors)} servidor(es)",
                    inline=True
                )
            else:
                embed.add_field(
                    name="Estado del Monitor",
                    value="🔴 No configurado",
                    inline=False
                )
                embed.description = "El monitoreo automático de FiveM no está configurado para este servidor.\nUsa `/configurar_estado_fivem` para configurarlo."
            
            embed.set_footer(text="Usa /forzar_actualizacion_fivem para una actualización manual")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in monitor_info_fivem: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al mostrar la información del monitor.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(FiveMStatus(bot))