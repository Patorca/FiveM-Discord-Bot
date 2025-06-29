import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_server_config(guild_id: int):
    try:
        with open("config.json", "r") as f:
            data = json.load(f)
        return data["servers"].get(str(guild_id))
    except Exception as e:
        logging.error(f"Error loading config for guild {guild_id}: {e}")
        return None

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        config = get_server_config(payload.guild_id)
        if not config:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        user = guild.get_member(payload.user_id)
        if not user:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        if message.author != self.bot.user or not message.embeds:
            return

        embed = message.embeds[0]
        if "verification" not in embed.title.lower():
            return

        if str(payload.emoji) != config.get("verification_emoji", "✅"):
            return

        role = guild.get_role(config["verification_role_id"])
        if not role:
            logger.error(f"Verification role {config['verification_role_id']} not found in {guild.name}")
            return

        if role in user.roles:
            return

        try:
            await user.add_roles(role, reason="Verification reaction")
            logger.info(f"Added verification role to {user} in {guild.name}")
            try:
                dm_embed = discord.Embed(
                    title="✅ Verification Complete",
                    description=f"You have been successfully verified in **{guild.name}**!",
                    color=0x00ff00
                )
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass
        except discord.Forbidden:
            logger.error(f"Missing permissions to add roles in {guild.name}")
        except Exception as e:
            logger.error(f"Error adding role: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        config = get_server_config(payload.guild_id)
        if not config:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        user = guild.get_member(payload.user_id)
        if not user:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        if message.author != self.bot.user or not message.embeds:
            return

        embed = message.embeds[0]
        if "verification" not in embed.title.lower():
            return

        if str(payload.emoji) != config.get("verification_emoji", "✅"):
            return

        role = guild.get_role(config["verification_role_id"])
        if not role:
            logger.error(f"Verification role {config['verification_role_id']} not found in {guild.name}")
            return

        if role not in user.roles:
            return

        try:
            await user.remove_roles(role, reason="Verification reaction removed")
            logger.info(f"Removed verification role from {user} in {guild.name}")
        except discord.Forbidden:
            logger.error(f"Missing permissions to remove roles in {guild.name}")
        except Exception as e:
            logger.error(f"Error removing role: {e}")

    @app_commands.command(name="verification", description="Send verification message with reaction")
    @app_commands.describe(channel="Channel to send verification message (optional)")
    @app_commands.default_permissions(manage_roles=True)
    async def verification(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None
    ):
        config = get_server_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("⚠️ This server has no verification config set.", ephemeral=True)
            return

        if channel is None:
            channel = interaction.channel

        perms = channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.embed_links or not perms.add_reactions:
            await interaction.response.send_message("❌ I need permission to send messages, embeds, and add reactions in that channel.", ephemeral=True)
            return

        role = interaction.guild.get_role(config["verification_role_id"])
        if not role:
            await interaction.response.send_message("❌ Verification role not found in this server.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔐 Server Verification",
            description=f"Al Verificarte aceptas las normas de conducta del servidor y comportarte de manera adecuada.\n\n"
                        f"Reacciona con {config.get('verification_emoji', '✅')} para recibir el rol {role.mention}.\n\n"
                        f"**Beneficios:**\n• Acceso completo\n• Participar en canales\n• ¡Únete a la comunidad!\n\n"
                        f"**Nota:** Quitar la reacción eliminará el rol.",
            color=0x3498db
        )
        embed.set_footer(
            text=f"Reacciona con {config.get('verification_emoji', '✅')} para verificarte",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        message = await channel.send(embed=embed)
        await message.add_reaction(config.get('verification_emoji', '✅'))
        await interaction.response.send_message(f"✅ Verification message sent in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="set-verification-role", description="Set the verification role for this server")
    @app_commands.describe(role="Role to assign when users verify")
    @app_commands.default_permissions(manage_roles=True)
    async def set_verification_role(self, interaction: discord.Interaction, role: discord.Role):
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ That role is above my permissions.", ephemeral=True)
            return

        try:
            with open("config.json", "r") as f:
                data = json.load(f)
            guild_id = str(interaction.guild.id)
            if "servers" not in data:
                data["servers"] = {}
            if guild_id not in data["servers"]:
                data["servers"][guild_id] = {}
            data["servers"][guild_id]["verification_role_id"] = role.id
            with open("config.json", "w") as f:
                json.dump(data, f, indent=2)
            await interaction.response.send_message(f"✅ Set verification role to {role.mention}", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting verification role: {e}")
            await interaction.response.send_message("❌ Failed to set verification role.", ephemeral=True)

    @app_commands.command(name="set-verification-emoji", description="Set the emoji used for verification")
    @app_commands.describe(emoji="Emoji to use for verification")
    @app_commands.default_permissions(manage_roles=True)
    async def set_verification_emoji(self, interaction: discord.Interaction, emoji: str):
        try:
            test_message = await interaction.channel.send("Testing emoji...")
            await test_message.add_reaction(emoji)
            await test_message.delete()

            with open("config.json", "r") as f:
                data = json.load(f)
            guild_id = str(interaction.guild.id)
            if "servers" not in data:
                data["servers"] = {}
            if guild_id not in data["servers"]:
                data["servers"][guild_id] = {}
            data["servers"][guild_id]["verification_emoji"] = emoji
            with open("config.json", "w") as f:
                json.dump(data, f, indent=2)

            await interaction.response.send_message(f"✅ Set verification emoji to {emoji}", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("❌ Invalid emoji.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting verification emoji: {e}")
            await interaction.response.send_message("❌ Failed to set verification emoji.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Verification(bot))
