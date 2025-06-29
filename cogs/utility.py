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

async def setup(bot):
    await bot.add_cog(Utility(bot))