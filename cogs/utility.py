import discord
from discord.ext import commands
from discord import app_commands
import time
import logging

logger = logging.getLogger(__name__)

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ping", description="Muestra la latencia del bot")
    async def ping(self, interaction: discord.Interaction):
        """Show bot latency and response time"""
        try:
            # Get Discord API latency
            api_latency = round(self.bot.latency * 1000, 2)
            
            # Measure response time
            start_time = time.time()
            
            embed = discord.Embed(
                title="🏓 Pong!",
                description="Información de latencia del bot",
                color=0x00ff00
            )
            
            embed.add_field(
                name="📡 Latencia API Discord",
                value=f"`{api_latency}ms`",
                inline=True
            )
            
            # Calculate response time after sending
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            # Update embed with response time
            embed.add_field(
                name="⚡ Tiempo de Respuesta",
                value=f"`{response_time}ms`",
                inline=True
            )
            
            # Add status indicator
            if api_latency < 100:
                status = "🟢 Excelente"
            elif api_latency < 200:
                status = "🟡 Bueno"
            elif api_latency < 300:
                status = "🟠 Regular"
            else:
                status = "🔴 Lento"
            
            embed.add_field(
                name="📊 Estado",
                value=status,
                inline=True
            )
            
            embed.set_footer(
                text=f"Bot: {self.bot.user.name}",
                icon_url=self.bot.user.display_avatar.url
            )
            
            # Edit the response with updated information
            await interaction.edit_original_response(embed=embed)
            
            logger.info(f"Ping command used by {interaction.user} - API: {api_latency}ms, Response: {response_time}ms")
            
        except Exception as e:
            logger.error(f"Error in ping command: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Error al obtener la latencia del bot!",
                    ephemeral=True
                )

    @app_commands.command(name="servidor-info", description="Muestra información detallada del servidor")
    async def server_info(self, interaction: discord.Interaction):
        """Show detailed server information"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Este comando solo puede usarse en un servidor!",
                    ephemeral=True
                )
                return

            # Create embed with server information
            embed = discord.Embed(
                title=f"📊 Información de {guild.name}",
                color=0x3498db,
                timestamp=discord.utils.utcnow()
            )

            # Server icon
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            # Basic information
            embed.add_field(
                name="🆔 ID del Servidor",
                value=f"`{guild.id}`",
                inline=True
            )

            embed.add_field(
                name="👑 Propietario",
                value=f"{guild.owner.mention if guild.owner else 'Desconocido'}",
                inline=True
            )

            embed.add_field(
                name="📅 Creado",
                value=f"<t:{int(guild.created_at.timestamp())}:D>",
                inline=True
            )

            # Member statistics
            total_members = guild.member_count
            online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
            bots = sum(1 for member in guild.members if member.bot)
            humans = total_members - bots

            embed.add_field(
                name="👥 Miembros Totales",
                value=f"`{total_members}`",
                inline=True
            )

            embed.add_field(
                name="🟢 En Línea",
                value=f"`{online_members}`",
                inline=True
            )

            embed.add_field(
                name="👤 Humanos / 🤖 Bots",
                value=f"`{humans}` / `{bots}`",
                inline=True
            )

            # Channel statistics
            text_channels = len(guild.text_channels)
            voice_channels = len(guild.voice_channels)
            categories = len(guild.categories)

            embed.add_field(
                name="💬 Canales de Texto",
                value=f"`{text_channels}`",
                inline=True
            )

            embed.add_field(
                name="🔊 Canales de Voz",
                value=f"`{voice_channels}`",
                inline=True
            )

            embed.add_field(
                name="📁 Categorías",
                value=f"`{categories}`",
                inline=True
            )

            # Server features
            embed.add_field(
                name="🛡️ Nivel de Verificación",
                value=f"`{guild.verification_level.name.title()}`",
                inline=True
            )

            embed.add_field(
                name="🎭 Roles",
                value=f"`{len(guild.roles)}`",
                inline=True
            )

            embed.add_field(
                name="😀 Emojis",
                value=f"`{len(guild.emojis)}`",
                inline=True
            )

            # Server boost info
            if guild.premium_tier > 0:
                embed.add_field(
                    name="💎 Nivel de Boost",
                    value=f"Nivel `{guild.premium_tier}` ({guild.premium_subscription_count} boosts)",
                    inline=False
                )

            # Server features if any
            if guild.features:
                features_text = ", ".join([feature.replace("_", " ").title() for feature in guild.features[:5]])
                if len(guild.features) > 5:
                    features_text += f" (+{len(guild.features) - 5} más)"
                
                embed.add_field(
                    name="⭐ Características",
                    value=features_text,
                    inline=False
                )

            embed.set_footer(
                text=f"Solicitado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"Server info command used by {interaction.user} in {guild.name}")

        except Exception as e:
            logger.error(f"Error in server info command: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Error al obtener la información del servidor!",
                    ephemeral=True
                )

    @app_commands.command(name="servidor-logo", description="Muestra el logo/icono del servidor")
    async def server_logo(self, interaction: discord.Interaction):
        """Show server logo/icon"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Este comando solo puede usarse en un servidor!",
                    ephemeral=True
                )
                return

            if not guild.icon:
                await interaction.response.send_message(
                    "❌ Este servidor no tiene un logo/icono configurado!",
                    ephemeral=True
                )
                return

            # Create embed with server icon
            embed = discord.Embed(
                title=f"🖼️ Logo de {guild.name}",
                color=0x3498db,
                timestamp=discord.utils.utcnow()
            )

            # Set the server icon as the main image
            embed.set_image(url=guild.icon.url)

            # Add download links for different sizes
            icon_formats = []
            
            # Add PNG format
            png_url = guild.icon.replace(format='png', size=1024).url
            icon_formats.append(f"[PNG (1024x1024)]({png_url})")
            
            # Add WEBP format if available
            webp_url = guild.icon.replace(format='webp', size=1024).url
            icon_formats.append(f"[WEBP (1024x1024)]({webp_url})")
            
            # Add JPG format
            jpg_url = guild.icon.replace(format='jpg', size=1024).url
            icon_formats.append(f"[JPG (1024x1024)]({jpg_url})")

            embed.add_field(
                name="📥 Descargar en diferentes formatos",
                value=" • ".join(icon_formats),
                inline=False
            )

            embed.add_field(
                name="🆔 ID del Servidor",
                value=f"`{guild.id}`",
                inline=True
            )

            embed.add_field(
                name="📅 Servidor creado",
                value=f"<t:{int(guild.created_at.timestamp())}:D>",
                inline=True
            )

            embed.set_footer(
                text=f"Solicitado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"Server logo command used by {interaction.user} in {guild.name}")

        except Exception as e:
            logger.error(f"Error in server logo command: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Error al obtener el logo del servidor!",
                    ephemeral=True
                )

async def setup(bot):
    await bot.add_cog(Utility(bot))