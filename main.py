import discord
from discord.ext import commands
import asyncio
import logging
import json
import os
import signal
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load configuration
def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found. Creating default config.")
        default_config = {
            "verification_role_id": 1020374565190389767,
            "ticket_category_id": None,
            "staff_role_ids": [],
            "verification_emoji": "✅"
        }
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=2)
        return default_config

config = load_config()

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
    async def setup_hook(self):
        # Load cogs
        await self.load_extension('cogs.tickets')
        await self.load_extension('cogs.verification')
        await self.load_extension('cogs.welcome')
        await self.load_extension('cogs.utility')
        await self.load_extension('cogs.fivem_status')
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Moderando Neon Vice RP"
        )
        await self.change_presence(activity=activity)
    
    async def send_email_notification(self):
        """Send email notification about bot shutdown"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = "neonvicebot@replit.app"
            msg['To'] = "unlobo77777@gmail.com"
            msg['Subject'] = "🔴 Neon Vice Bot - Desconectado"
            
            # Create HTML content
            html_body = f"""
            <html>
              <head></head>
              <body>
                <h2 style="color: #ff0000;">Bot Neon Vice Desconectado</h2>
                <p>El bot de Discord <strong>Neon Vice</strong> se ha desconectado del servidor.</p>
                <table style="border-collapse: collapse; width: 100%;">
                  <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><strong>Estado:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">Bot apagado</td>
                  </tr>
                  <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><strong>Fecha y Hora:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</td>
                  </tr>
                  <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><strong>Servidor:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">Replit</td>
                  </tr>
                </table>
                <p style="margin-top: 20px;">
                  <em>Este es un mensaje automático del sistema de monitoreo del bot.</em>
                </p>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Note: In a production environment, you would need proper SMTP credentials
            # For now, we'll log the attempt
            logger.info("Email notification prepared for unlobo77777@gmail.com")
            logger.info(f"Email content: Bot shutdown notification at {datetime.now()}")
            
        except Exception as e:
            logger.error(f"Failed to prepare email notification: {e}")

    async def send_shutdown_notification(self):
        """Send notification to admin when bot shuts down"""
        try:
            admin_id = 462635310724022285
            user = await self.fetch_user(admin_id)
            if user:
                embed = discord.Embed(
                    title="🔴 Bot Desconectado",
                    description="El bot Neon Vice se ha desconectado del servidor.",
                    color=0xff0000
                )
                embed.add_field(
                    name="Estado",
                    value="Bot apagado",
                    inline=True
                )
                embed.add_field(
                    name="Tiempo",
                    value=f"<t:{int(discord.utils.utcnow().timestamp())}:F>",
                    inline=True
                )
                await user.send(embed=embed)
                logger.info(f"Shutdown notification sent to admin {admin_id}")
            
            # Send email notification
            await self.send_email_notification()
            
        except Exception as e:
            logger.error(f"Failed to send shutdown notification: {e}")
    
    async def close(self):
        """Override close method to send notification before shutdown"""
        await self.send_shutdown_notification()
        await super().close()
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions to execute this command!")
        else:
            logger.error(f"Unexpected error: {error}")
            await ctx.send("❌ An unexpected error occurred!")

# Create bot instance
bot = DiscordBot()

# Error handler for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        await interaction.response.send_message("❌ I don't have the required permissions!", ephemeral=True)
    else:
        logger.error(f"Slash command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An unexpected error occurred!", ephemeral=True)
        else:
            await interaction.followup.send("❌ An unexpected error occurred!", ephemeral=True)

# Signal handlers for graceful shutdown
async def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    await bot.close()

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(signal_handler(s, f)))
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(signal_handler(s, f)))

# Run the bot
if __name__ == "__main__":
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN environment variable not found!")
        exit(1)
    
    # Setup signal handlers
    setup_signal_handlers()
    
    try:
        bot.run(bot_token)
    except discord.LoginFailure:
        logger.error("Invalid bot token!")
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
    finally:
        logger.info("Bot has been shut down")
