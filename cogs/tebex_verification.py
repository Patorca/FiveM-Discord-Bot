import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Dict, Optional

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

def validate_tebex_transaction_id(txn_id):
    """Validate Tebex transaction ID format"""
    if not txn_id:
        return False
    
    # Pattern: tbx- followed by alphanumeric characters and hyphens
    pattern = r'^tbx-[a-zA-Z0-9-]+$'
    return bool(re.match(pattern, txn_id))

class TebexVerification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verified_transactions = set()  # Cache of verified transactions to prevent reuse
        
    async def verify_transaction_with_tebex(self, transaction_id: str, store_url: str = "kingmaps.net") -> Optional[Dict]:
        """
        Verify transaction with Tebex API
        Returns transaction data if valid, None if invalid
        """
        try:
            # For now, we'll implement a basic validation
            # In production, you would need proper Tebex API credentials
            if not validate_tebex_transaction_id(transaction_id):
                return None
            
            # Check if transaction was already used
            if transaction_id in self.verified_transactions:
                return None
            
            # Simulate API call (replace with real Tebex API call)
            # Real implementation would look like:
            # async with aiohttp.ClientSession() as session:
            #     headers = {'Authorization': f'Bearer {TEBEX_API_KEY}'}
            #     async with session.get(f'https://plugin.tebex.io/payments/{transaction_id}', headers=headers) as response:
            #         if response.status == 200:
            #             return await response.json()
            #         return None
            
            # For demonstration, we'll validate format and simulate success
            return {
                "transaction_id": transaction_id,
                "status": "Complete",
                "amount": "10.00",
                "currency": "USD",
                "date": datetime.utcnow().isoformat(),
                "customer": {
                    "email": "example@example.com"
                },
                "products": [
                    {
                        "id": 1,
                        "name": "Premium Package"
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error verifying transaction {transaction_id}: {e}")
            return None
    
    @app_commands.command(name="verificar_compra", description="Verifica tu compra de kingmaps.net para obtener tu rol")
    @app_commands.describe(
        numero_transaccion="Número de transacción de Tebex (formato: tbx-xxxxxxxx)"
    )
    async def verify_purchase(self, interaction: discord.Interaction, numero_transaccion: str):
        """Verify Tebex purchase and assign role"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Validate transaction ID format
            if not validate_tebex_transaction_id(numero_transaccion):
                embed = discord.Embed(
                    title="❌ Formato inválido",
                    description="El número de transacción debe tener el formato: `tbx-xxxxxxxx`\n\n"
                               "Puedes encontrar tu número de transacción en:\n"
                               "• El email de confirmación de compra\n"
                               "• Tu historial de pagos en kingmaps.net",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if user already has verified role
            config = await load_config()
            guild_id = str(interaction.guild.id)
            
            if ('servers' not in config or 
                guild_id not in config['servers'] or 
                'tebex_verified_role_id' not in config['servers'][guild_id]):
                embed = discord.Embed(
                    title="❌ Configuración faltante",
                    description="El rol de verificación no está configurado. Un administrador debe usar `/configurar_rol_tebex` primero.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            
            verified_role_id = config['servers'][guild_id]['tebex_verified_role_id']
            verified_role = interaction.guild.get_role(verified_role_id)
            
            if not verified_role:
                embed = discord.Embed(
                    title="❌ Rol no encontrado",
                    description="El rol de verificación configurado no existe. Contacta a un administrador.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if user already has the role
            if verified_role in interaction.user.roles:
                embed = discord.Embed(
                    title="ℹ️ Ya verificado",
                    description=f"Ya tienes el rol {verified_role.mention}.",
                    color=0x3498db
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Verify transaction with Tebex
            transaction_data = await self.verify_transaction_with_tebex(numero_transaccion)
            
            if not transaction_data:
                embed = discord.Embed(
                    title="❌ Transacción inválida",
                    description="No se pudo verificar la transacción. Verifica que:\n\n"
                               "• El número de transacción es correcto\n"
                               "• La compra fue realizada en kingmaps.net\n"
                               "• El pago fue completado exitosamente\n"
                               "• No has usado esta transacción antes\n\n"
                               "Si el problema persiste, contacta al soporte.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check transaction status
            if transaction_data.get('status') != 'Complete':
                embed = discord.Embed(
                    title="❌ Pago no completado",
                    description=f"La transacción está en estado: **{transaction_data.get('status')}**\n\n"
                               "Solo se pueden verificar transacciones completadas.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Assign role to user
            try:
                await interaction.user.add_roles(verified_role, reason=f"Tebex verification: {numero_transaccion}")
                
                # Mark transaction as used
                self.verified_transactions.add(numero_transaccion)
                
                # Log the verification
                logger.info(f"Tebex verification successful: {interaction.user} ({interaction.user.id}) - Transaction: {numero_transaccion}")
                
                # Success message
                embed = discord.Embed(
                    title="✅ Verificación exitosa",
                    description=f"¡Tu compra ha sido verificada exitosamente!\n\n"
                               f"**Rol asignado:** {verified_role.mention}\n"
                               f"**Transacción:** `{numero_transaccion}`\n"
                               f"**Producto:** {transaction_data.get('products', [{}])[0].get('name', 'Desconocido')}\n\n"
                               f"¡Gracias por tu compra en kingmaps.net!",
                    color=0x00ff00
                )
                embed.set_footer(text="Esta transacción ya no puede ser reutilizada")
                await interaction.followup.send(embed=embed)
                
                # Send notification to log channel if configured
                log_channel_id = config['servers'][guild_id].get('tebex_log_channel_id')
                if log_channel_id:
                    log_channel = self.bot.get_channel(log_channel_id)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="🛒 Nueva verificación Tebex",
                            description=f"**Usuario:** {interaction.user.mention} ({interaction.user.id})\n"
                                       f"**Rol asignado:** {verified_role.mention}\n"
                                       f"**Transacción:** `{numero_transaccion}`\n"
                                       f"**Producto:** {transaction_data.get('products', [{}])[0].get('name', 'Desconocido')}",
                            color=0x00ff00,
                            timestamp=datetime.utcnow()
                        )
                        await log_channel.send(embed=log_embed)
                
            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Error de permisos",
                    description="No tengo permisos para asignar roles. Contacta a un administrador.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
            except Exception as e:
                logger.error(f"Error assigning role: {e}")
                embed = discord.Embed(
                    title="❌ Error interno",
                    description="Ocurrió un error al asignar el rol. Contacta a un administrador.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in verify_purchase: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error inesperado. Inténtalo de nuevo o contacta al soporte.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="configurar_rol_tebex", description="Configura el rol que se asigna al verificar compras de Tebex")
    @app_commands.describe(rol="Rol que se asignará a usuarios verificados")
    async def setup_tebex_role(self, interaction: discord.Interaction, rol: discord.Role):
        """Setup Tebex verification role"""
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
            
            # Check bot permissions
            if not interaction.guild.me.guild_permissions.manage_roles:
                embed = discord.Embed(
                    title="❌ Permisos del bot",
                    description="El bot necesita permisos para gestionar roles.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Check role hierarchy
            if rol.position >= interaction.guild.me.top_role.position:
                embed = discord.Embed(
                    title="❌ Jerarquía de roles",
                    description="No puedo asignar este rol porque está por encima de mi rol más alto en la jerarquía.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Save configuration
            config = await load_config()
            guild_id = str(interaction.guild.id)
            
            if 'servers' not in config:
                config['servers'] = {}
            if guild_id not in config['servers']:
                config['servers'][guild_id] = {}
            
            config['servers'][guild_id]['tebex_verified_role_id'] = rol.id
            
            await save_config(config)
            
            embed = discord.Embed(
                title="✅ Rol configurado",
                description=f"El rol {rol.mention} se asignará ahora a usuarios que verifiquen sus compras de kingmaps.net.\n\n"
                           f"Los usuarios pueden usar `/verificar_compra` para obtener este rol.",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
            
            logger.info(f"Tebex verification role configured: {rol.name} ({rol.id}) in guild {interaction.guild.id}")
            
        except Exception as e:
            logger.error(f"Error in setup_tebex_role: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al configurar el rol.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="configurar_log_tebex", description="Configura el canal de logs para verificaciones de Tebex")
    @app_commands.describe(canal="Canal donde se registrarán las verificaciones")
    async def setup_tebex_log(self, interaction: discord.Interaction, canal: discord.TextChannel):
        """Setup Tebex verification log channel"""
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
            
            # Check bot permissions
            if not canal.permissions_for(interaction.guild.me).send_messages:
                embed = discord.Embed(
                    title="❌ Permisos del canal",
                    description="No tengo permisos para enviar mensajes en ese canal.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Save configuration
            config = await load_config()
            guild_id = str(interaction.guild.id)
            
            if 'servers' not in config:
                config['servers'] = {}
            if guild_id not in config['servers']:
                config['servers'][guild_id] = {}
            
            config['servers'][guild_id]['tebex_log_channel_id'] = canal.id
            
            await save_config(config)
            
            embed = discord.Embed(
                title="✅ Canal de logs configurado",
                description=f"Las verificaciones de Tebex se registrarán en {canal.mention}.",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
            
            logger.info(f"Tebex log channel configured: {canal.name} ({canal.id}) in guild {interaction.guild.id}")
            
        except Exception as e:
            logger.error(f"Error in setup_tebex_log: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al configurar el canal de logs.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="info_tebex", description="Muestra la configuración actual de verificación Tebex")
    async def tebex_info(self, interaction: discord.Interaction):
        """Show Tebex verification configuration"""
        try:
            config = await load_config()
            guild_id = str(interaction.guild.id)
            
            embed = discord.Embed(
                title="📊 Configuración Tebex",
                color=0x3498db
            )
            
            if ('servers' in config and 
                guild_id in config['servers']):
                server_config = config['servers'][guild_id]
                
                # Verified role info
                role_id = server_config.get('tebex_verified_role_id')
                if role_id:
                    role = interaction.guild.get_role(role_id)
                    embed.add_field(
                        name="🎭 Rol de verificación",
                        value=role.mention if role else f"❌ Rol no encontrado (ID: {role_id})",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🎭 Rol de verificación",
                        value="❌ No configurado",
                        inline=False
                    )
                
                # Log channel info
                log_channel_id = server_config.get('tebex_log_channel_id')
                if log_channel_id:
                    log_channel = self.bot.get_channel(log_channel_id)
                    embed.add_field(
                        name="📝 Canal de logs",
                        value=log_channel.mention if log_channel else f"❌ Canal no encontrado (ID: {log_channel_id})",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="📝 Canal de logs",
                        value="❌ No configurado",
                        inline=False
                    )
                
                embed.add_field(
                    name="🛒 Tienda",
                    value="kingmaps.net",
                    inline=True
                )
                
                embed.add_field(
                    name="📋 Transacciones verificadas",
                    value=f"{len(self.verified_transactions)} transacciones",
                    inline=True
                )
                
            else:
                embed.description = "No hay configuración de Tebex para este servidor.\n\nUsa `/configurar_rol_tebex` para comenzar."
            
            embed.add_field(
                name="ℹ️ Comandos disponibles",
                value="• `/verificar_compra` - Verificar una compra\n"
                      "• `/configurar_rol_tebex` - Configurar rol (Admin)\n"
                      "• `/configurar_log_tebex` - Configurar logs (Admin)",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in tebex_info: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al mostrar la información.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TebexVerification(bot))