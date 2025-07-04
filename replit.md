# Discord Bot Replit Workspace

## Overview

This is a Discord bot built with Python using the discord.py library. The bot provides verification and ticket system functionality for Discord servers. It's designed to run on Replit with Python 3.11 and includes configuration-driven features for role-based verification and support ticket management.

## System Architecture

### Core Architecture
- **Language**: Python 3.11
- **Framework**: discord.py (>=2.5.2)
- **Architecture Pattern**: Command/Event-driven with Cog system
- **Configuration**: JSON-based configuration management
- **Logging**: Built-in Python logging with file and console output

### Project Structure
```
├── main.py              # Bot entry point and core setup
├── config.json          # Configuration file
├── cogs/               # Discord.py cogs for modular functionality
│   ├── verification.py  # User verification system
│   └── tickets.py      # Support ticket system
├── utils/
│   └── helpers.py      # Utility functions
├── pyproject.toml      # Python project configuration
└── .replit            # Replit configuration
```

## Key Components

### 1. Bot Core (main.py)
- **Purpose**: Main bot initialization and configuration loading
- **Features**: 
  - Automatic config.json creation with defaults
  - Comprehensive logging setup
  - Discord intents configuration for message content, reactions, guilds, and members
  - Bot class inheritance with custom command prefix ('!')

### 2. Verification System (cogs/verification.py)
- **Purpose**: Handles user verification through emoji reactions
- **Architecture**: Event-driven reaction listener
- **Key Features**:
  - Reaction-based verification system
  - Configurable verification emoji (default: ✅)
  - Role assignment upon verification
  - Embed-based verification messages

### 3. Ticket System (cogs/tickets.py)
- **Purpose**: Support ticket creation and management
- **Architecture**: Discord UI Views with persistent buttons
- **Key Features**:
  - Button-based ticket creation
  - Automatic channel creation with proper permissions
  - Duplicate ticket prevention
  - Category-based organization
  - Custom naming convention: `ticket-{username}-{discriminator}`

### 4. Utility Functions (utils/helpers.py)
- **Purpose**: Shared utility functions across the bot
- **Key Functions**:
  - Configuration loading and saving
  - Staff role validation
  - Ticket management permissions
  - Error handling for JSON operations

### 5. Configuration Management
- **File**: config.json
- **Structure**:
  ```json
  {
    "verification_role_id": 1020374565190389767,
    "ticket_category_id": null,
    "staff_role_ids": [],
    "verification_emoji": "✅"
  }
  ```

## Data Flow

### Verification Flow
1. User reacts to verification message with configured emoji
2. Bot detects reaction via `on_raw_reaction_add` event
3. Bot validates message source and embed content
4. Bot assigns verification role to user
5. Action logged for audit purposes

### Ticket Creation Flow
1. User clicks "Create Ticket" button
2. Bot checks for existing tickets by username
3. Bot creates new channel with proper permissions
4. Bot sets up ticket-specific overwrites
5. Bot places channel in configured category (if set)

## External Dependencies

### Python Packages
- **discord.py** (>=2.5.2): Core Discord API wrapper
- **aiohttp**: HTTP client for Discord API (dependency of discord.py)
- **Standard library**: json, logging, asyncio, os

### Discord Requirements
- **Bot Token**: Required environment variable or manual input
- **Bot Permissions**: 
  - Send Messages
  - Manage Channels
  - Manage Roles
  - Add Reactions
  - Read Message History
  - View Channels

## Deployment Strategy

### Replit Configuration
- **Runtime**: Python 3.11 with Nix package manager
- **Execution**: Automatic pip install of discord.py followed by main.py execution
- **Workflow**: Parallel execution setup with dedicated "Discord Bot" workflow

### Environment Setup
1. Bot automatically installs discord.py on startup
2. Configuration file created with defaults if missing
3. Logging initialized with both file and console output
4. Bot token required for authentication (not included in repository)

### Scalability Considerations
- Modular cog system allows easy feature expansion
- JSON configuration supports runtime modifications
- Logging system provides operational visibility
- Permission-based access control supports multi-server deployment

## Changelog
- June 24, 2025. Initial setup
- June 24, 2025. Updated verification message to Spanish with custom text: "Al Verificarte aceptas las normas de conducta de el servidor y comportarte de manera adecuada."
- June 24, 2025. Changed bot status to "Watching Moderando Neon Vice RP"
- June 24, 2025. Translated ticket panel message to Spanish with custom text: "Al abrir un ticket te estas poniendo en contacto con la administracion que te respondera en breve, porfavor expon los motivos de tu ticket de manera concisa para que te podamos ayudar mejor"
- June 24, 2025. Added transcript system - generates ticket transcripts sent to channel ID 1175492699156127866 and DM to ticket creator when tickets are closed
- June 24, 2025. Added staff role mention (ID: 1020374565207150626) when tickets are created
- June 24, 2025. Added welcome system - sends welcome message to new members in channel ID 1020374565710467163 with server icon and member count
- June 24, 2025. Added shutdown notification system - sends DM to admin (ID: 462635310724022285) when bot disconnects
- June 24, 2025. Enhanced shutdown notifications to include email alerts to unlobo77777@gmail.com with HTML formatted status reports
- June 24, 2025. Added utility cog with /ping command for bot latency monitoring with Discord API latency, response time, and status indicators
- June 25, 2025. Enhanced welcome system with multi-server support - added /configurar_bienvenida, /desactivar_bienvenida, and /info_bienvenida commands for per-server configuration
- June 28, 2025. Successfully migrated from Replit Agent to standard Replit environment with security improvements and dependency management
- June 28, 2025. Enhanced welcome message system with original creative content, roleplay-themed messaging, and added /previsualizar_bienvenida command for administrators
- June 28, 2025. Added FiveM server status monitoring system with automatic updates every 5 minutes, real-time status tracking from status.cfx.re, and commands for configuration
- June 29, 2025. Successfully completed migration from Replit Agent to standard Replit environment with enhanced security practices, proper dependency management via pyproject.toml, and secure environment variable handling for Discord bot token
- June 29, 2025. Enhanced ticket system with staff role management and transcript channel configuration - added /set-staff-role, /remove-staff-role, /set-transcript-channel, /remove-transcript-channel, and /ticket-info commands for complete administrative control
- June 29, 2025. Enhanced ticket system with automatic staff role mentions when tickets are created and improved DM transcript delivery with fallback notifications when DMs are disabled
- June 29, 2025. Changed bot activity status from "Watching" to "Playing" Moderando PT Scripts
- June 30, 2025. Enhanced FiveM status monitoring system with persistent message configuration - monitor now automatically resumes after bot restarts and continues editing the same status message instead of creating new ones
- June 30, 2025. Added comprehensive moderation system with /limpiar, /banear, /timeout, and /quitar-timeout commands featuring safety validations, role hierarchy checks, DM notifications, and detailed logging
- June 30, 2025. Enhanced moderation system with customizable role permissions - added /set-moderator-role, /remove-moderator-role, and /moderation-info commands allowing administrators to define which roles can use moderation commands beyond default Discord permissions
- June 30, 2025. Fixed FiveM status monitoring persistence issue - system now properly loads configuration on startup and maintains monitoring across bot restarts

## User Preferences

Preferred communication style: Simple, everyday language.
Preferred language: Spanish (for bot messages and interface text)