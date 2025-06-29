import discord
import json
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

def load_config() -> dict:
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found")
        return {}
    except json.JSONDecodeError:
        logger.error("Invalid JSON in config.json")
        return {}

def save_config(config: dict) -> bool:
    """Save configuration to config.json"""
    try:
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def has_staff_role(user: discord.Member, config: dict) -> bool:
    """Check if user has any staff role"""
    staff_role_ids = config.get('staff_role_ids', [])
    for role in user.roles:
        if role.id in staff_role_ids:
            return True
    return False

def can_manage_tickets(user: discord.Member, channel: discord.TextChannel, config: dict) -> bool:
    """Check if user can manage tickets (close, etc.)"""
    # Check if user is ticket creator
    if f'-{user.name.lower()}-{user.discriminator}' in channel.name:
        return True
    
    # Check if user has staff role
    if has_staff_role(user, config):
        return True
    
    # Check if user has manage channels permission
    if channel.permissions_for(user).manage_channels:
        return True
    
    return False

def format_user_info(user: discord.User) -> str:
    """Format user information for logging"""
    return f"{user.display_name} ({user.name}#{user.discriminator}) - ID: {user.id}"

def create_error_embed(title: str, description: str, color: int = 0xff0000) -> discord.Embed:
    """Create a standardized error embed"""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=color
    )
    return embed

def create_success_embed(title: str, description: str, color: int = 0x00ff00) -> discord.Embed:
    """Create a standardized success embed"""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=color
    )
    return embed

def create_info_embed(title: str, description: str, color: int = 0x3498db) -> discord.Embed:
    """Create a standardized info embed"""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=color
    )
    return embed

async def safe_send(destination, *args, **kwargs) -> Optional[discord.Message]:
    """Safely send a message, handling common exceptions"""
    try:
        return await destination.send(*args, **kwargs)
    except discord.Forbidden:
        logger.error(f"No permission to send message in {destination}")
        return None
    except discord.HTTPException as e:
        logger.error(f"HTTP error sending message: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        return None

def validate_permissions(channel: discord.TextChannel, member: discord.Member, required_perms: List[str]) -> List[str]:
    """Validate if member has required permissions in channel"""
    permissions = channel.permissions_for(member)
    missing_perms = []
    
    for perm in required_perms:
        if not getattr(permissions, perm, False):
            missing_perms.append(perm.replace('_', ' ').title())
    
    return missing_perms

def get_ticket_user_from_channel(channel: discord.TextChannel) -> Optional[str]:
    """Extract username from ticket channel name"""
    if not channel.name.startswith('ticket-'):
        return None
    
    parts = channel.name.split('-')
    if len(parts) >= 3:
        # ticket-username-discriminator
        return '-'.join(parts[1:-1])  # Handle usernames with dashes
    
    return None

class BotColors:
    """Standard colors for bot embeds"""
    SUCCESS = 0x00ff00
    ERROR = 0xff0000
    WARNING = 0xffaa00
    INFO = 0x3498db
    PRIMARY = 0x5865f2
    SECONDARY = 0x747f8d

class BotEmojis:
    """Standard emojis for bot messages"""
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    TICKET = "🎫"
    LOCK = "🔒"
    UNLOCK = "🔓"
    VERIFICATION = "🔐"
    LOADING = "⏳"
