"""
╔══════════════════════════════════════════════════════════════╗
║COLORADO STATE ROLEPLAY — STAFF APPLICATION BOT               ║
║(Discord Components V2 version)                               ║
║                                                              ║
║REQUIREMENTS:                                                 ║
║    pip install -U discord.py python-dotenv                   ║
║    (2.6+ required for Components V2 support)                 ║
║                                                              ║
║Setup:                                                        ║
║    Create a ".env" file next to bot.py and write:            ║
║        BOT_TOKEN=your_bot_token_here                         ║
║                                                              ║
║In the Discord Developer Portal -> Bot tab you must ENABLE    ║
║these privileged intents:                                     ║
║    - SERVER MEMBERS INTENT                                   ║
║    - MESSAGE CONTENT INTENT                                  ║
║                                                              ║
║Run:                                                          ║
║    python bot.py                                             ║
║                                                              ║
║Commands:                                                     ║
║    /roleplay-request {roleplay} {players-involved} {duration}║
║        -> Anyone can use it, 5 min cooldown per user.        ║
║    /request-training                                         ║
║        -> TRAINING_ROLE_ID only, channel-restricted,         ║
║           global 15 min cooldown, "Host a Training" button   ║
║    /setup-verify (Manage Server permission)                  ║
║        -> Sends the verification panel                       ║
║    /bot message {message}                                    ║
║        -> MANAGEMENT_ROLE_ID only. Sends bot message (with   ║
║           approval flow if ping detected).                   ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import math
import os
import random
import re
import time
from typing import Optional
from urllib.parse import urlencode

import aiohttp
import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════════════════

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Guild ID — commands are synced to this guild INSTANTLY.
GUILD_ID = 1428083974726746185

STAFF_APPLICATION_URL = "https://chicago-rp-staff.onrender.com/"

EMBED_COLOR = 2830663

# ── Welcome system ──
WELCOME_CHANNEL_ID = 1545499120733659176

# ── Role IDs ──
UNVERIFIED_ROLE_ID = 1545498816323526687
VERIFIED_ROLE_ID = 1545498809730207750

# ── Roleplay request system ──
ROLEPLAY_CHANNEL_ID = 1545499358303096872      # Channel where the request is posted
ROLEPLAY_PING_ROLE_ID = 1545498622282563624    # Role that gets pinged + has accept/deny permission
RP_LOG_CHANNEL_ID = 1545499135065727031        # Channel where accept/deny results are announced

# ── Ghost ping system ──
GHOST_PING_WINDOW_SECONDS = 30

# ── Training request system ──
TRAINING_ROLE_ID = 1545498654373318747
TRAINING_CHANNEL_ID = 1545499270122176637
TRAINING_VOICE_CHANNEL_ID = 1545499284151992363
TRAINING_VOICE_CHANNEL_ID_2 = 1545499289936199710
TRAINING_VOICE_LINK = "https://discord.com/channels/1428083974726746185/1545499284151992363"
TRAINING_FALLBACK_LINK = "https://discord.com/channels/1428083974726746185/1545499289936199710"

# ── Anti-Raid system ──
ANTI_RAID_CHANNEL_ID = 1545499002152296468
ANTI_RAID_PING_ROLE_ID = 1545498154760409130
QUARANTINE_ROLE_ID = 1545498793192063087
QUARANTINE_ALLOWED_CHANNEL_IDS = {1545499008867242085, 1545499015024746506}
CHANNEL_DELETE_LIMIT = 5
ROLE_DELETE_LIMIT = 5

# ── Verification (Verify) system ──
VERIFY_CHANNEL_ID = 1545498995650986098

# ── Roblox verification (OAuth2) ──
ROBLOX_CLIENT_ID = os.getenv("ROBLOX_CLIENT_ID", "")
ROBLOX_CLIENT_SECRET = os.getenv("ROBLOX_CLIENT_SECRET", "")
ROBLOX_REDIRECT_URI = os.getenv("ROBLOX_REDIRECT_URI", "http://localhost:5309/callback")
ROBLOX_AUTHORIZE_URL = "https://apis.roblox.com/oauth/v1/authorize"
ROBLOX_TOKEN_URL = "https://apis.roblox.com/oauth/v1/token"
ROBLOX_USERINFO_URL = "https://apis.roblox.com/oauth/v1/userinfo"
CALLBACK_HOST = "0.0.0.0"
CALLBACK_PORT = int(os.getenv("PORT") or os.getenv("ROBLOX_AUTH_PORT", "5309"))
ROBLOX_VERIFY_REQUIRED = True

# ── Staff management system ──
MANAGEMENT_ROLE_ID = 1545498273731715103    # promote/infract/strike/terminate + revoke commands (or higher)
LIST_ROLE_ID = 1545498622282563624          # viewing your own list (or higher)
LIST_OTHERS_ROLE_ID = 1545498273731715103   # viewing someone else's list via the user parameter (or higher)
PROMO_LOG_CHANNEL_ID = 1545499327642992700  # Promotion announcements
INFR_LOG_CHANNEL_ID = 1545499321527697498   # Infraction / Strike / Termination announcements
INFRACTION_ROLE_IDS = {1: 1545500595715051730, 2: 1545498761105641676, 3: 1545498766772273253}
STRIKE_ROLE_IDS = {1: 1545498774619820162, 2: 1545498781242359910, 3: 1545498787118588055}

# 1. Banner (at the top, above the heading)
BANNER_TOP_URL = "https://media.discordapp.net/attachments/980177239373140008/1538162090798485504/Untitled_design_12.png?ex=6a81ac94&is=6a805b14&hm=dad6e9e41d7194b996f1584d84311ddefc3f92f27ac21fadaf991b9fd5e4767c&=&format=webp&quality=lossless"

# 2. Banner (below the description text, at the bottom)
BANNER_BOTTOM_URL = "https://media.discordapp.net/attachments/980177239373140008/1538162398442033232/Untitled_design_13.png?ex=6a81acdd&is=6a805b5d&hm=f23bbbc57139bde3c49cbfa231e1b5d20f6f2d4741a5bced30671b1e2155e7aa&=&format=webp&quality=lossless"

HEADING_TEXT = "### :chicago: Colorado State Roleplay Applications"

DESCRIPTION_TEXT = (
    "> :right_arrow: Welcome to the **Colorado State Roleplay** staff application channel, here you can "
    "join our awesome staff community! Our staff teams are **dedicated** to "
    "help us grow and stay safe! Please make sure to read all of our "
    "requirements before applying, otherwise your application might result "
    "in a fail."
)

REQUIREMENTS = [
    "Must be 13+ years old",
    "Must be active in the community",
    "Must be mature and professional",
    "Must be respectful to all members",
    "Must follow the server rules",
]


def build_requirements_embed() -> discord.Embed:
    """Ephemeral embed shown when the Staff Requirements button is clicked."""
    description = "\n\n".join(f"> **•**  {req}" for req in REQUIREMENTS)
    embed = discord.Embed(
        color=EMBED_COLOR,
        title="Staff Requirements",
        description=description,
    )
    embed.set_footer(text="Only you can see this message.")
    return embed


# ══════════════════════════════════════════════════════════════
#  COMMON HELPERS
# ══════════════════════════════════════════════════════════════

USER_MENTION_RE = re.compile(r"<@!?(\d+)>")
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def first_user_id_in(text: str | None) -> int | None:
    match = USER_MENTION_RE.search(text or "")
    return int(match.group(1)) if match else None


def user_mention(user_id: int) -> str:
    return f"<@{user_id}>"


def embed_field_value(embed: discord.Embed | None, name: str) -> str | None:
    if embed is None:
        return None
    for field in embed.fields:
        if field.name == name:
            return field.value
    return None


def is_button_disabled(message: discord.Message | None, custom_id: str) -> bool:
    if message is None:
        return False
    for component in message.components:
        children = getattr(component, "children", None)
        if children is None:
            children = [component] if hasattr(component, "custom_id") else []
        for child in children:
            if getattr(child, "custom_id", None) == custom_id:
                return bool(getattr(child, "disabled", False))
    return False


def iter_all_channels(guild: discord.Guild):
    for channel in guild.channels:
        yield channel
        threads = getattr(channel, "threads", None)
        if threads is not None:
            for thread in threads:
                yield thread


_CLOUDFLARE_BLOCK_UNTIL: float = 0.0


def _note_cloudflare_block(duration: float = 45.0) -> None:
    global _CLOUDFLARE_BLOCK_UNTIL
    _CLOUDFLARE_BLOCK_UNTIL = max(_CLOUDFLARE_BLOCK_UNTIL, time.monotonic() + duration)


async def _wait_out_cloudflare_block(what: str) -> None:
    global _CLOUDFLARE_BLOCK_UNTIL
    remaining = _CLOUDFLARE_BLOCK_UNTIL - time.monotonic()
    if remaining > 0:
        wait = min(remaining, 60.0)
        print(f"[!] Cloudflare block active — waiting {wait:.0f}s before {what}...")
        await asyncio.sleep(wait)
        _CLOUDFLARE_BLOCK_UNTIL = 0.0


async def send_with_retry(coro_factory, what: str, max_attempts: int = 8) -> bool:
    await _wait_out_cloudflare_block(what)
    for attempt in range(1, max_attempts + 1):
        try:
            await coro_factory()
            return True
        except discord.HTTPException as exc:
            status = getattr(exc, "status", None)
            if status == 429 and attempt < max_attempts:
                delay = min(2 ** attempt, 30)
                _note_cloudflare_block()
                print(f"[!] Rate limited (429) while {what}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue
            print(f"[!] Error while {what}: {exc}")
            return False
        except discord.NotFound:
            print(f"[!] Interaction expired while {what} (NotFound).")
            return False
    return False


# ══════════════════════════════════════════════════════════════
#  STAFF REQUIREMENTS BUTTON
# ══════════════════════════════════════════════════════════════

class RequirementsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Staff Requirements",
            style=discord.ButtonStyle.secondary,
            custom_id="staff_requirements",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=build_requirements_embed(),
            ephemeral=True,
        )


# ══════════════════════════════════════════════════════════════
#  WELCOME MESSAGE
# ══════════════════════════════════════════════════════════════

class MemberCountButton(discord.ui.Button):
    def __init__(self, count: int):
        super().__init__(
            label=f"Members: {count}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )


class WelcomeView(discord.ui.View):
    def __init__(self, count: int):
        super().__init__(timeout=None)
        self.add_item(MemberCountButton(count))


# ══════════════════════════════════════════════════════════════
#  COMPONENTS V2 LAYOUT
# ══════════════════════════════════════════════════════════════

class ApplicationsLayout(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        container = discord.ui.Container(
            discord.ui.MediaGallery(discord.MediaGalleryItem(media=BANNER_TOP_URL)),
            discord.ui.Section(
                discord.ui.TextDisplay(HEADING_TEXT),
                accessory=RequirementsButton(),
            ),
            discord.ui.Separator(),
            discord.ui.TextDisplay(DESCRIPTION_TEXT),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                discord.ui.Button(
                    style=discord.ButtonStyle.link,
                    label="Staff Application  ↗",
                    url=STAFF_APPLICATION_URL,
                )
            ),
            discord.ui.Separator(),
            discord.ui.MediaGallery(discord.MediaGalleryItem(media=BANNER_BOTTOM_URL)),
            accent_colour=discord.Colour(EMBED_COLOR),
        )

        self.add_item(container)


# ══════════════════════════════════════════════════════════════
#  ROLEPLAY REQUEST
# ══════════════════════════════════════════════════════════════

class DenyReasonModal(discord.ui.Modal, title="Deny Reason"):
    reason = discord.ui.TextInput(
        label="Why is this request being denied?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=400,
        placeholder="Type the reason here...",
    )

    def __init__(self, parent_view: "RoleplayRequestView"):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        for child in self.parent_view.children:
            child.disabled = True
        await interaction.response.edit_message(view=self.parent_view)

        requester_id = self.parent_view.get_requester_id(interaction)
        if requester_id is None:
            return

        log_channel = interaction.guild.get_channel(RP_LOG_CHANNEL_ID)
        if log_channel is not None:
            try:
                await log_channel.send(
                    f"{user_mention(requester_id)} Your roleplay request has been denied. "
                    f"Reason: {self.reason.value}\n"
                    f"-# If you think this decision is wrong, please open a ticket."
                )
            except discord.HTTPException as exc:
                print(f"[!] Could not send the deny log message: {exc}")


class RoleplayRequestView(discord.ui.View):
    def __init__(self, requester: discord.abc.User | None = None):
        super().__init__(timeout=None)
        self.requester = requester

    def get_requester_id(self, interaction: discord.Interaction) -> int | None:
        if self.requester is not None:
            return self.requester.id
        if interaction.message is not None and interaction.message.embeds:
            return first_user_id_in(
                embed_field_value(interaction.message.embeds[0], "Requested By")
            )
        return None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        role = interaction.guild.get_role(ROLEPLAY_PING_ROLE_ID)
        if role is None or role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ You don't have permission to accept/deny this request.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, custom_id="rp_accept")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_button_disabled(interaction.message, "rp_accept"):
            await interaction.response.send_message(
                "This request has already been handled.", ephemeral=True
            )
            return

        requester_id = self.get_requester_id(interaction)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        if requester_id is None:
            return

        log_channel = interaction.guild.get_channel(RP_LOG_CHANNEL_ID)
        if log_channel is not None:
            try:
                await log_channel.send(
                    f"{user_mention(requester_id)} Your roleplay request has been accepted!"
                )
            except discord.HTTPException as exc:
                print(f"[!] Could not send the accept log message: {exc}")

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="rp_deny")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_button_disabled(interaction.message, "rp_deny"):
            await interaction.response.send_message(
                "This request has already been handled.", ephemeral=True
            )
            return
        await interaction.response.send_modal(DenyReasonModal(self))


# ══════════════════════════════════════════════════════════════
#  TRAINING REQUEST
# ══════════════════════════════════════════════════════════════

class HostTrainingView(discord.ui.View):
    def __init__(self, requester: discord.abc.User | None = None):
        super().__init__(timeout=None)
        self.requester = requester

    def get_requester_id(self, interaction: discord.Interaction) -> int | None:
        if self.requester is not None:
            return self.requester.id
        if interaction.message is not None and interaction.message.embeds:
            return first_user_id_in(interaction.message.embeds[0].description)
        return None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        role = interaction.guild.get_role(TRAINING_ROLE_ID)
        if role is None or role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ You don't have the required role to use this button.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Host a Training",
        style=discord.ButtonStyle.success,
        custom_id="host_training",
    )
    async def host_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_button_disabled(interaction.message, "host_training"):
            await interaction.response.send_message(
                "This training request has already been handled.", ephemeral=True
            )
            return

        requester_id = self.get_requester_id(interaction)
        voice_channel = interaction.guild.get_channel(TRAINING_VOICE_CHANNEL_ID)
        voice_channel_2 = interaction.guild.get_channel(TRAINING_VOICE_CHANNEL_ID_2) if 'TRAINING_VOICE_CHANNEL_ID_2' in globals() else None
        already_hosting = False

        if isinstance(voice_channel, discord.VoiceChannel):
            role = interaction.guild.get_role(TRAINING_ROLE_ID)
            if role is not None:
                already_hosting = any(role in member.roles for member in voice_channel.members)

        link = TRAINING_FALLBACK_LINK if already_hosting else TRAINING_VOICE_LINK

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        if requester_id is not None:
            await interaction.followup.send(f"{user_mention(requester_id)} Please head to {link}")
        else:
            await interaction.followup.send(f"Please head to {link}")


# ══════════════════════════════════════════════════════════════
#  ANTI-RAID
# ══════════════════════════════════════════════════════════════

channel_delete_counts: dict[int, int] = {}
role_delete_counts: dict[int, int] = {}

channel_delete_snapshots: dict[int, dict] = {}
role_delete_snapshots: dict[int, dict] = {}
executor_channel_deletions: dict[int, list[int]] = {}
executor_role_deletions: dict[int, list[int]] = {}

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anti_raid_state.json")


def _cap_snapshots() -> None:
    while len(channel_delete_snapshots) > 200:
        channel_delete_snapshots.pop(next(iter(channel_delete_snapshots)))
    while len(role_delete_snapshots) > 200:
        role_delete_snapshots.pop(next(iter(role_delete_snapshots)))


def _save_anti_raid_state() -> None:
    data = {
        "channel_delete_counts": {str(k): v for k, v in channel_delete_counts.items()},
        "role_delete_counts": {str(k): v for k, v in role_delete_counts.items()},
        "channel_delete_snapshots": {str(k): v for k, v in channel_delete_snapshots.items()},
        "role_delete_snapshots": {str(k): v for k, v in role_delete_snapshots.items()},
        "executor_channel_deletions": {str(k): v for k, v in executor_channel_deletions.items()},
        "executor_role_deletions": {str(k): v for k, v in executor_role_deletions.items()},
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError as exc:
        print(f"[!] Anti-raid durumu kaydedilemedi: {exc}")


def _load_anti_raid_state() -> None:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return
    channel_delete_counts.update({int(k): v for k, v in data.get("channel_delete_counts", {}).items()})
    role_delete_counts.update({int(k): v for k, v in data.get("role_delete_counts", {}).items()})
    channel_delete_snapshots.update({int(k): v for k, v in data.get("channel_delete_snapshots", {}).items()})
    role_delete_snapshots.update({int(k): v for k, v in data.get("role_delete_snapshots", {}).items()})
    executor_channel_deletions.update({int(k): v for k, v in data.get("executor_channel_deletions", {}).items()})
    executor_role_deletions.update({int(k): v for k, v in data.get("executor_role_deletions", {}).items()})


_load_anti_raid_state()


async def apply_lockdown(guild: discord.Guild) -> None:
    role = guild.get_role(QUARANTINE_ROLE_ID)
    if role is None:
        return

    async def work(channel):
        overwrite = channel.overwrites_for(role)
        if channel.id in QUARANTINE_ALLOWED_CHANNEL_IDS:
            overwrite.view_channel = True
            overwrite.send_messages = True
        else:
            overwrite.view_channel = False
        try:
            await channel.set_permissions(role, overwrite=overwrite, reason="Anti-Raid LOCKDOWN")
        except Exception:
            pass

    semaphore = asyncio.Semaphore(10)
    async def bounded_work(ch):
        async with semaphore:
            await work(ch)

    await asyncio.gather(*(bounded_work(c) for c in iter_all_channels(guild)))


async def apply_member_quarantine(member: discord.Member) -> None:
    guild = member.guild
    role = guild.get_role(QUARANTINE_ROLE_ID)
    if role is not None:
        try:
            if role not in member.roles:
                await member.add_roles(role, reason="Anti-Raid LOCKDOWN quarantine")
        except Exception:
            pass


async def punish_member(member: discord.Member, guild: discord.Guild) -> None:
    quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
    new_roles = [quarantine_role] if quarantine_role is not None else []
    try:
        await member.edit(
            roles=new_roles,
            nick="Under Investigation",
            reason="Anti-Raid: channel/role deletion limit exceeded",
        )
    except Exception:
        pass

    notify_channel = guild.get_channel(ANTI_RAID_CHANNEL_ID)
    if notify_channel is not None:
        try:
            await notify_channel.send(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    title="🚨 Anti-Raid: Member Punished",
                    description=(
                        f"{member.mention} reached the deletion limit!\n"
                        f"All roles were removed, their nickname was set to "
                        f"**Under Investigation** and the quarantine role was applied."
                    ),
                    timestamp=discord.utils.utcnow(),
                )
            )
        except Exception:
            pass


def snapshot_channel(channel: discord.abc.GuildChannel) -> dict:
    overwrites = []
    try:
        for target, overwrite in channel.overwrites.items():
            allow, deny = overwrite.pair()
            overwrites.append({
                "id": target.id,
                "type": "member" if target.type is discord.Member else "role",
                "allow": allow.value,
                "deny": deny.value,
            })
    except Exception:
        pass
    return {
        "name": channel.name,
        "type": int(channel.type.value),
        "category_id": channel.category_id,
        "position": channel.position,
        "topic": getattr(channel, "topic", None),
        "nsfw": getattr(channel, "nsfw", None),
        "slowmode_delay": getattr(channel, "slowmode_delay", None),
        "bitrate": getattr(channel, "bitrate", None),
        "user_limit": getattr(channel, "user_limit", None),
        "overwrites": overwrites,
    }


def snapshot_role(role: discord.Role) -> dict:
    return {
        "name": role.name,
        "colour": role.colour.value,
        "hoist": role.hoist,
        "mentionable": role.mentionable,
        "permissions": role.permissions.value,
        "position": role.position,
    }


def rebuild_overwrites(snapshot: dict) -> dict:
    overwrites = {}
    for o in snapshot.get("overwrites", []):
        target_type = discord.Member if o.get("type") == "member" else discord.Role
        target = discord.Object(id=o["id"], type=target_type)
        overwrites[target] = discord.PermissionOverwrite.from_pair(
            discord.Permissions(o["allow"]), discord.Permissions(o["deny"])
        )
    return overwrites


async def recover_channel(guild: discord.Guild, snapshot: dict) -> discord.abc.GuildChannel | None:
    try:
        overwrites = rebuild_overwrites(snapshot)
        category = guild.get_channel(snapshot.get("category_id"))
        ctype = discord.ChannelType(snapshot["type"])
        base = {"name": snapshot["name"], "overwrites": overwrites, "reason": "Anti-Raid recovery"}
        if category is not None:
            base["category"] = category

        if ctype is discord.ChannelType.voice:
            channel = await guild.create_voice_channel(
                bitrate=snapshot.get("bitrate") or 64000,
                user_limit=snapshot.get("user_limit") or 0,
                **base,
            )
        elif ctype is discord.ChannelType.category:
            channel = await guild.create_category(**base)
        elif ctype is discord.ChannelType.stage_voice:
            channel = await guild.create_stage_channel(**base)
        elif ctype is discord.ChannelType.forum:
            channel = await guild.create_forum(**base)
        else:
            channel = await guild.create_text_channel(
                topic=snapshot.get("topic"),
                nsfw=bool(snapshot.get("nsfw")),
                slowmode_delay=snapshot.get("slowmode_delay") or 0,
                news=(ctype is discord.ChannelType.news),
                **base,
            )
        try:
            if snapshot.get("position"):
                await channel.edit(position=snapshot["position"])
        except Exception:
            pass
        return channel
    except Exception as exc:
        print(f"[!] Could not recover channel: {exc}")
    return None


async def recover_role(guild: discord.Guild, snapshot: dict) -> discord.Role | None:
    try:
        role = await guild.create_role(
            name=snapshot["name"],
            permissions=discord.Permissions(snapshot.get("permissions", 0)),
            colour=discord.Colour(snapshot.get("colour", 0)),
            hoist=bool(snapshot.get("hoist", False)),
            mentionable=bool(snapshot.get("mentionable", False)),
            reason="Anti-Raid recovery",
        )
        try:
            if snapshot.get("position"):
                await role.edit(position=snapshot["position"])
        except Exception:
            pass
        return role
    except Exception as exc:
        print(f"[!] Could not recover role: {exc}")
    return None


async def recover_executor_deletions(guild: discord.Guild, executor_id: int, kind: str) -> list:
    if kind == "channel":
        item_ids = executor_channel_deletions.pop(executor_id, [])
        snapshots = channel_delete_snapshots
        recover = recover_channel
    else:
        item_ids = executor_role_deletions.pop(executor_id, [])
        snapshots = role_delete_snapshots
        recover = recover_role

    recovered = []
    for item_id in list(item_ids):
        snapshot = snapshots.pop(item_id, None)
        if snapshot is None:
            continue
        item = await recover(guild, snapshot)
        if item is not None:
            recovered.append(item)
    return recovered


async def notify_recovery(guild: discord.Guild, member: discord.Member, kind: str, recovered: list) -> None:
    channel = guild.get_channel(ANTI_RAID_CHANNEL_ID)
    if channel is None:
        return
    label = "channel" if kind == "channel" else "role"
    if recovered:
        lines = [f"• **#{item.name}**" if kind == "channel" else f"• **@{item.name}**" for item in recovered]
        description = f"Recovered **{len(recovered)}** deleted {label}(s) caused by {member.mention}:\n" + "\n".join(lines)
        color = discord.Color.green()
    else:
        description = f"Could not recover deleted {label}s caused by {member.mention} — no snapshot data available."
        color = discord.Color.orange()

    try:
        await channel.send(
            embed=discord.Embed(title="♻️ Anti-Raid Recovery", color=color, description=description, timestamp=discord.utils.utcnow())
        )
    except Exception:
        pass


def build_channel_delete_embed(channel: discord.abc.GuildChannel, executor: discord.abc.User | None, count: int) -> discord.Embed:
    embed = discord.Embed(
        color=discord.Color.red(),
        title="⚠️ Channel Deleted!",
        description=f"Someone just deleted the **#{channel.name}** channel!\nIf you're not aware of it, please press the button below.",
        timestamp=discord.utils.utcnow(),
    )
    if executor is not None:
        embed.add_field(name="Deleted By", value=f"{executor.mention}\n`{executor}` — ID: {executor.id}", inline=False)
    else:
        embed.add_field(name="Deleted By", value="Unknown", inline=False)
    embed.add_field(name="Channel", value=f"**#{channel.name}** (`{channel.id}`)", inline=True)
    embed.add_field(name="Delete Count", value=f"{count}/{CHANNEL_DELETE_LIMIT}", inline=True)
    embed.set_footer(text="Anti-Raid System")
    return embed


def build_role_delete_embed(role: discord.Role, executor: discord.abc.User | None, count: int) -> discord.Embed:
    embed = discord.Embed(
        color=discord.Color.red(),
        title="⚠️ Role Deleted!",
        description=f"Someone just deleted the **{role.name}** role!\nIf you're not aware of it, please press the button below.",
        timestamp=discord.utils.utcnow(),
    )
    if executor is not None:
        embed.add_field(name="Deleted By", value=f"{executor.mention}\n`{executor}` — ID: {executor.id}", inline=False)
    else:
        embed.add_field(name="Deleted By", value="Unknown", inline=False)
    embed.add_field(name="Role", value=f"**{role.name}** (`{role.id}`)", inline=True)
    embed.add_field(name="Delete Count", value=f"{count}/{ROLE_DELETE_LIMIT}", inline=True)
    embed.set_footer(text="Anti-Raid System")
    return embed


class AntiRaidView(discord.ui.View):
    def __init__(self, executor: discord.abc.User | None = None, kind: str | None = None, target_id: int | None = None):
        super().__init__(timeout=None)
        self.executor = executor
        self.kind = kind
        self.target_id = target_id

    def get_kind(self, interaction: discord.Interaction) -> str:
        if self.kind is not None:
            return self.kind
        if interaction.message is not None and interaction.message.embeds:
            title = (interaction.message.embeds[0].title or "").lower()
            if "role" in title:
                return "role"
        return "channel"

    def get_target_id(self, interaction: discord.Interaction) -> int | None:
        if self.target_id is not None:
            return self.target_id
        if interaction.message is not None and interaction.message.embeds:
            field_name = "Channel" if self.get_kind(interaction) == "channel" else "Role"
            value = embed_field_value(interaction.message.embeds[0], field_name)
            if value:
                match = re.search(r"\(`(\d+)`\)", value)
                if match:
                    return int(match.group(1))
        return None

    def get_executor_id(self, interaction: discord.Interaction) -> int | None:
        if self.executor is not None:
            return self.executor.id
        if interaction.message is not None and interaction.message.embeds:
            return first_user_id_in(embed_field_value(interaction.message.embeds[0], "Deleted By"))
        return None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need the **Manage Server** permission to use this button.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="I'm Aware", style=discord.ButtonStyle.secondary, custom_id="ar_aware")
    async def aware_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_button_disabled(interaction.message, "ar_aware"):
            await interaction.response.send_message("This notification has already been handled.", ephemeral=True)
            return

        await interaction.response.defer()
        executor_id = self.get_executor_id(interaction)
        kind = self.get_kind(interaction)
        target_id = self.get_target_id(interaction)

        counts = channel_delete_counts if kind == "channel" else role_delete_counts
        if executor_id is not None:
            counts[executor_id] = max(0, counts.get(executor_id, 0) - 1)

        recovered_name = None
        missing_data = False
        if target_id is not None:
            if kind == "channel":
                snapshot = channel_delete_snapshots.pop(target_id, None)
                if snapshot is not None:
                    channel = await recover_channel(interaction.guild, snapshot)
                    if channel is not None:
                        recovered_name = f"**#{channel.name}**"
                else:
                    missing_data = True
            else:
                snapshot = role_delete_snapshots.pop(target_id, None)
                if snapshot is not None:
                    role = await recover_role(interaction.guild, snapshot)
                    if role is not None:
                        recovered_name = f"**@{role.name}**"
                else:
                    missing_data = True
        _save_anti_raid_state()

        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(view=self)

        msg = f"✅ {interaction.user.mention} marked this event as **I'm Aware**."
        if recovered_name is not None:
            msg += f"\n♻️ {recovered_name} has been recovered."
        if missing_data:
            msg += "\n⚠️ Recovery data for this item was not found."
        await interaction.followup.send(msg)

    @discord.ui.button(label="LOCKDOWN", style=discord.ButtonStyle.danger, custom_id="ar_lockdown")
    async def lockdown_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_button_disabled(interaction.message, "ar_lockdown"):
            await interaction.response.send_message("This notification has already been handled.", ephemeral=True)
            return

        await interaction.response.defer()
        await apply_lockdown(interaction.guild)

        executor_id = self.get_executor_id(interaction)
        quarantined = None
        if executor_id is not None:
            member = interaction.guild.get_member(executor_id)
            if member is not None and member.id != interaction.user.id:
                await apply_member_quarantine(member)
                quarantined = member

        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(view=self)

        msg = f"🔒 {interaction.user.mention} started the **LOCKDOWN**."
        if quarantined is not None:
            msg += f"\n🚫 {quarantined.mention} has been given the quarantine role."
        await interaction.followup.send(msg)


# ══════════════════════════════════════════════════════════════
#  VERIFICATION SYSTEM (NO CHANNEL OVERRIDES)
# ══════════════════════════════════════════════════════════════

async def apply_verified_access(guild: discord.Guild, member: discord.Member) -> None:
    """Removes unverified role (1543236742843211776) and grants verified role (1543236668981518457)."""
    unverified_role = guild.get_role(UNVERIFIED_ROLE_ID)
    verified_role = guild.get_role(VERIFIED_ROLE_ID)

    if unverified_role is not None and unverified_role in member.roles:
        await send_with_retry(
            lambda: member.remove_roles(unverified_role, reason="Verified via verify button"),
            "removing unverified role",
        )
    if verified_role is not None and verified_role not in member.roles:
        await send_with_retry(
            lambda: member.add_roles(verified_role, reason="Verified via verify button"),
            "granting verified role",
        )


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        guild = interaction.guild
        if not isinstance(member, discord.Member) or guild is None:
            await interaction.response.send_message("❌ This button can only be used inside the server.", ephemeral=True)
            return

        verify_channel = guild.get_channel(VERIFY_CHANNEL_ID)
        state = roblox_verify_state(member, verify_channel)
        linked = roblox_links.get(str(member.id))

        if state == "require":
            await interaction.response.send_modal(RobloxUsernameModal())
            return

        await interaction.response.defer(ephemeral=True)

        if state == "linked":
            await apply_verified_access(guild, member)
            if linked:
                await apply_roblox_nickname(member, linked["username"])
            await send_with_retry(
                lambda: interaction.followup.send(
                    f"✅ You are verified! Your Roblox account **{linked['username']}** is linked.",
                    ephemeral=True,
                ),
                "sending verified message",
            )
            return

        await apply_verified_access(guild, member)
        await send_with_retry(
            lambda: interaction.followup.send(
                "✅ You have been verified! Welcome to **Colorado State Roleplay**.\n"
                "🔗 Want to link your Roblox account? Press the button below!",
                ephemeral=True,
                view=LinkRobloxView(member.id),
            ),
            "sending welcome message",
        )


# ══════════════════════════════════════════════════════════════
#  ROBLOX VERIFICATION
# ══════════════════════════════════════════════════════════════

ROBLOX_LINKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roblox_links.json")
roblox_links: dict[str, dict] = {}
pending_oauth: dict[str, dict] = {}


def _load_roblox_links() -> None:
    try:
        with open(ROBLOX_LINKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            roblox_links.update(data)
    except (OSError, ValueError):
        pass


def _save_roblox_links() -> None:
    try:
        with open(ROBLOX_LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(roblox_links, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[!] Could not save Roblox links: {exc}")


_load_roblox_links()


def roblox_enabled() -> bool:
    return bool(ROBLOX_CLIENT_ID and ROBLOX_CLIENT_SECRET)


def roblox_verify_state(member: discord.Member, verify_channel: discord.abc.GuildChannel | None = None) -> str:
    if roblox_links.get(str(member.id)):
        return "linked"
    verified_role = member.guild.get_role(VERIFIED_ROLE_ID)
    if verified_role and verified_role in member.roles:
        return "already"
    if ROBLOX_VERIFY_REQUIRED:
        return "require"
    return "optional"


def make_roblox_nickname(base: str, roblox_username: str) -> str:
    suffix = f" (@{roblox_username})"
    if len(base) + len(suffix) <= 32:
        return base + suffix
    cut = 32 - len(suffix)
    if cut <= 0:
        return suffix[:32]
    return base[:cut] + suffix


async def apply_roblox_nickname(member: discord.Member, roblox_username: str) -> bool:
    base = member.display_name or member.name
    new_nick = make_roblox_nickname(base, roblox_username)
    if member.nick == new_nick:
        return True
    return await send_with_retry(
        lambda: member.edit(nick=new_nick, reason="Roblox verification"),
        "setting Roblox nickname",
    )


ROBLOX_API_USERNAMES_URL = "https://users.roblox.com/v1/usernames/users"
ROBLOX_API_HEADSHOT_URL = "https://thumbnails.roblox.com/v1/users/avatar-headshot"


async def roblox_lookup_username(session: aiohttp.ClientSession, username: str) -> dict | None:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with session.post(
            ROBLOX_API_USERNAMES_URL,
            json={"usernames": [username], "excludeBannedUsers": True},
            headers=headers,
        ) as resp:
            if resp.status != 200:
                print(f"[!] Roblox lookup status {resp.status} for username {username}")
                return None
            data = await resp.json()
        items = data.get("data") or []
        if not items or items[0].get("id") is None:
            return None
        first = items[0]
        return {
            "id": int(first["id"]),
            "name": first["name"],
            "displayName": first.get("displayName") or first["name"],
        }
    except Exception as exc:
        print(f"[!] Roblox lookup error for {username}: {exc}")
        return None


async def roblox_fetch_headshot(session: aiohttp.ClientSession, user_id: int) -> str | None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with session.get(
            ROBLOX_API_HEADSHOT_URL,
            params={"userIds": user_id, "size": "420x420", "format": "Png", "isCircular": "false"},
            headers=headers,
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
        items = data.get("data") or []
        if items and items[0].get("imageUrl"):
            return items[0]["imageUrl"]
        return None
    except Exception:
        return None


class RobloxUsernameModal(discord.ui.Modal, title="Roblox Verification"):
    username = discord.ui.TextInput(
        label="What is your Roblox username?",
        placeholder="e.g. robloxpromaster123",
        required=True,
        min_length=3,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with aiohttp.ClientSession() as session:
            profile = await roblox_lookup_username(session, self.username.value.strip())

        if profile is None:
            await send_with_retry(
                lambda: interaction.followup.send("❌ Could not find a Roblox account with that username.", ephemeral=True),
                "sending lookup error",
            )
            return

        if any(link.get("roblox_id") == str(profile["id"]) for link in roblox_links.values()):
            await send_with_retry(
                lambda: interaction.followup.send("❌ This Roblox account is already linked to another Discord account.", ephemeral=True),
                "sending duplicate error",
            )
            return

        async with aiohttp.ClientSession() as session:
            avatar_url = await roblox_fetch_headshot(session, profile["id"])

        embed = discord.Embed(color=EMBED_COLOR, title="Is this your Roblox account?")
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        embed.add_field(name="Username", value=f"**{profile['name']}**", inline=True)
        embed.add_field(name="Display Name", value=profile.get("displayName") or "—", inline=True)
        embed.set_footer(text="Only you can see this message.")

        await send_with_retry(
            lambda: interaction.followup.send(embed=embed, view=RobloxConfirmView(interaction.user.id, profile), ephemeral=True),
            "sending Roblox confirm embed",
        )


class RobloxConfirmView(discord.ui.View):
    def __init__(self, user_id: int, profile: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.profile = profile

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the user who started verification can use this.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yes, that's me!", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_button_disabled(interaction.message, button.custom_id):
            return
        guild = interaction.guild
        if guild is None:
            return

        roblox_links[str(self.user_id)] = {
            "roblox_id": str(self.profile["id"]),
            "username": self.profile["name"],
            "linked_ts": int(time.time()),
        }
        _save_roblox_links()

        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        for child in self.children:
            child.disabled = True
        await send_with_retry(
            lambda: interaction.edit_original_response(
                content=f"✅ Confirmed! Your Roblox account **{self.profile['name']}** has been linked...",
                embed=None,
                view=self,
            ),
            "updating confirm msg",
        )

        member = guild.get_member(self.user_id)
        if member is not None:
            await apply_roblox_nickname(member, self.profile["name"])
            await apply_verified_access(guild, member)


class LinkRobloxView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your verification prompt.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Link Roblox", style=discord.ButtonStyle.primary, emoji="🔗")
    async def link_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RobloxUsernameModal())


async def start_roblox_callback_server() -> None:
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="Colorado Utilities Bot Running", content_type="text/html"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, CALLBACK_HOST, CALLBACK_PORT)
    try:
        await site.start()
        print(f"[+] Web server listening on {CALLBACK_HOST}:{CALLBACK_PORT}")
    except Exception as exc:
        print(f"[!] Web server error: {exc}")


# ══════════════════════════════════════════════════════════════
#  BOT MESSAGE APPROVAL SYSTEM (/bot message)
# ══════════════════════════════════════════════════════════════

BOT_MESSAGES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_bot_messages.json")
pending_bot_messages: dict[str, dict] = {}


def _load_pending_bot_messages():
    try:
        with open(BOT_MESSAGES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            pending_bot_messages.update(data)
    except (OSError, ValueError):
        pass


def _save_pending_bot_messages():
    try:
        with open(BOT_MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(pending_bot_messages, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[!] Could not save pending bot messages: {exc}")


_load_pending_bot_messages()


class BotMessageApprovalView(discord.ui.View):
    def __init__(self, req_id: str | None = None):
        super().__init__(timeout=None)
        self.req_id = req_id

    def get_req_id(self, interaction: discord.Interaction) -> str | None:
        if self.req_id:
            return self.req_id
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            for field in embed.fields:
                if field.name == "Request ID":
                    return field.value.strip("`")
        return None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member) or not has_role_or_higher(interaction.user, MANAGEMENT_ROLE_ID):
            await interaction.response.send_message("❌ You don't have permission to accept/deny this request.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Agree", style=discord.ButtonStyle.success, custom_id="bot_msg_agree")
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_button_disabled(interaction.message, "bot_msg_agree"):
            await interaction.response.send_message("This request has already been handled.", ephemeral=True)
            return

        req_id = self.get_req_id(interaction)
        data = pending_bot_messages.get(req_id)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        if data:
            data["status"] = "accepted"
            _save_pending_bot_messages()

            user_id = data["user_id"]
            channel_id = data["channel_id"]
            msg_text = data["message"]

            guild = interaction.guild
            member = guild.get_member(user_id) if guild else None
            if member is None:
                try:
                    member = await interaction.client.fetch_user(user_id)
                except Exception:
                    member = None

            if member:
                try:
                    await member.send(f"✅ Your bot message request (`{req_id}`) has been **accepted** and sent!")
                except discord.HTTPException:
                    pass

            target_channel = interaction.client.get_channel(channel_id)
            if target_channel:
                try:
                    await target_channel.send(msg_text)
                except discord.HTTPException as exc:
                    print(f"[!] Could not send accepted bot message: {exc}")

            await interaction.followup.send(f"✅ Request `{req_id}` accepted and message sent.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Request data not found.", ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="bot_msg_deny")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_button_disabled(interaction.message, "bot_msg_deny"):
            await interaction.response.send_message("This request has already been handled.", ephemeral=True)
            return

        req_id = self.get_req_id(interaction)
        data = pending_bot_messages.get(req_id)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        if data:
            data["status"] = "denied"
            _save_pending_bot_messages()

            user_id = data["user_id"]
            member = interaction.guild.get_member(user_id) if interaction.guild else None
            if member is None:
                try:
                    member = await interaction.client.fetch_user(user_id)
                except Exception:
                    member = None

            if member:
                try:
                    await member.send(f"❌ Your bot message request (`{req_id}`) has been **denied**.")
                except discord.HTTPException:
                    pass

            await interaction.followup.send(f"❌ Request `{req_id}` denied.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Request data not found.", ephemeral=True)


# ══════════════════════════════════════════════════════════════
#  BOT CLASS & SETUP
# ══════════════════════════════════════════════════════════════

class ColoradoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ApplicationsLayout())
        self.add_view(RoleplayRequestView())
        self.add_view(HostTrainingView())
        self.add_view(AntiRaidView())
        self.add_view(VerifyView())
        self.add_view(BotMessageApprovalView())

        await start_roblox_callback_server()

        # Register /bot message command group
        bot_group = app_commands.Group(name="bot", description="Bot commands")

        @bot_group.command(name="message", description="Send a message as the bot.")
        @app_commands.describe(message="The message for the bot to send")
        async def bot_message_command(interaction: discord.Interaction, message: str):
            if not isinstance(interaction.user, discord.Member) or not has_role_or_higher(interaction.user, MANAGEMENT_ROLE_ID):
                await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                return

            has_ping = message.find("@everyone") != -1 or message.find("@here") != -1 or bool(re.search(r"<@&(\d+)>", message))

            if has_ping:
                req_id = f"MSG-{''.join(random.choices(CODE_ALPHABET, k=6))}"
                pending_bot_messages[req_id] = {
                    "user_id": interaction.user.id,
                    "channel_id": interaction.channel_id,
                    "message": message,
                    "status": "pending",
                    "created_ts": int(time.time()),
                }
                _save_pending_bot_messages()

                await interaction.response.send_message(
                    "Your message contains a ping. A request have been sent to the system. Your message will be sended if it gets accepted.",
                    ephemeral=True
                )

                anti_raid_channel = interaction.guild.get_channel(ANTI_RAID_CHANNEL_ID)
                if anti_raid_channel:
                    embed = discord.Embed(
                        title="⚠️ Bot Message Request",
                        color=discord.Color.orange(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(name="User", value=f"{interaction.user.mention} (`{interaction.user}` - ID: {interaction.user.id})", inline=False)
                    embed.add_field(name="Message", value=message, inline=False)
                    embed.add_field(name="Date", value=f"<t:{int(time.time())}:F>", inline=True)
                    embed.add_field(name="Request ID", value=f"`{req_id}`", inline=True)
                    embed.description = f"{interaction.user.mention} tried to send a bot message containing a ping!\nDo you accept?"

                    try:
                        await anti_raid_channel.send(
                            content=f"<@&{ANTI_RAID_PING_ROLE_ID}>",
                            embed=embed,
                            view=BotMessageApprovalView(req_id)
                        )
                    except Exception as exc:
                        print(f"[!] Could not send bot message approval request: {exc}")
            else:
                await interaction.response.defer(ephemeral=True)
                try:
                    await interaction.channel.send(message)
                    await interaction.followup.send("✅ Message sent successfully.", ephemeral=True)
                except Exception as exc:
                    await interaction.followup.send(f"❌ Could not send message: `{exc}`", ephemeral=True)

        self.tree.add_command(bot_group)

        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            # Clear existing guild commands to remove stale/old commands (like /join)
            self.tree.clear_commands(guild=guild)
            await self.tree.sync(guild=guild)

            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"[+] Commands synced to guild {GUILD_ID} (stale commands cleared).")
        else:
            await self.tree.sync()
            print("[+] Commands synced globally.")

        cleanup_recent_pings.start()


bot = ColoradoBot()


@bot.event
async def on_ready():
    print("═" * 55)
    print(f"  ✅  Logged in as {bot.user}!")
    print(f"  🆔  ID: {bot.user.id}")
    print(f"  🌐  Active in {len(bot.guilds)} servers")
    print("═" * 55)


# ══════════════════════════════════════════════════════════════
#  NEW MEMBER JOIN — unverified role assignment (NO PERM OVERRIDES)
# ══════════════════════════════════════════════════════════════

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild

    # 1) Welcome message
    channel = guild.get_channel(WELCOME_CHANNEL_ID)
    if channel is not None:
        try:
            await channel.send(
                f"Hi {member.mention} and welcome to Colorado State Roleplay! "
                f"We hope you enjoy your stay with us.",
                view=WelcomeView(guild.member_count),
            )
        except Exception as exc:
            print(f"[!] Welcome message error: {exc}")

    # 2) Give unverified role (1543236742843211776)
    unverified_role = guild.get_role(UNVERIFIED_ROLE_ID)
    if unverified_role is not None and unverified_role not in member.roles:
        try:
            await member.add_roles(unverified_role, reason="Automatic unverified join role")
        except Exception as exc:
            print(f"[!] Could not give unverified role: {exc}")


# ══════════════════════════════════════════════════════════════
#  GHOST PING DETECTION
# ══════════════════════════════════════════════════════════════

recent_pings: dict[int, dict] = {}


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return

    has_ping = bool(message.mentions) or bool(message.role_mentions) or message.mention_everyone
    if has_ping:
        recent_pings[message.id] = {
            "channel_id": message.channel.id,
            "author_id": message.author.id,
            "timestamp": discord.utils.utcnow(),
        }

    await bot.process_commands(message)


async def handle_deleted_ping(message_id: int, channel_id: int) -> None:
    data = recent_pings.pop(message_id, None)
    if data is None:
        return

    elapsed = (discord.utils.utcnow() - data["timestamp"]).total_seconds()
    if elapsed > GHOST_PING_WINDOW_SECONDS:
        return

    channel = bot.get_channel(channel_id or data["channel_id"])
    if channel is None:
        return

    guild = getattr(channel, "guild", None)
    author = guild.get_member(data["author_id"]) if guild else None
    mention = author.mention if author else f"<@{data['author_id']}>"

    try:
        await channel.send(f"{mention} Do not ghost ping!")
    except Exception:
        pass


@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    await handle_deleted_ping(payload.message_id, payload.channel_id)


@bot.event
async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
    for message_id in payload.message_ids:
        await handle_deleted_ping(message_id, payload.channel_id)


@tasks.loop(minutes=2)
async def cleanup_recent_pings():
    now = discord.utils.utcnow()
    stale_ids = [
        mid for mid, data in recent_pings.items()
        if (now - data["timestamp"]).total_seconds() > GHOST_PING_WINDOW_SECONDS
    ]
    for mid in stale_ids:
        recent_pings.pop(mid, None)

    for state in [s for s, d in pending_oauth.items() if d["expires"] < time.time()]:
        pending_oauth.pop(state, None)


# ══════════════════════════════════════════════════════════════
#  COMMANDS (/roleplay-request, /request-training, /setup-verify)
# ══════════════════════════════════════════════════════════════

@bot.tree.command(
    name="roleplay-request",
    description="Request a custom roleplay (e.g. Hostage RP, Bank Robbery).",
)
@app_commands.describe(
    roleplay="The roleplay you are requesting (e.g. Bank Robbery)",
    players_involved="Who will be in the RP? (mention them with @, e.g. @User1 @User2)",
    duration="How long it lasts (e.g. 30 minutes)",
)
@app_commands.rename(players_involved="players-involved")
@app_commands.checks.cooldown(1, 300, key=lambda i: i.user.id)
async def roleplay_request(
    interaction: discord.Interaction,
    roleplay: str,
    players_involved: str,
    duration: str,
):
    await interaction.response.defer(ephemeral=True)
    channel = interaction.client.get_channel(ROLEPLAY_CHANNEL_ID)
    if channel is None:
        await interaction.followup.send("❌ Roleplay request channel not found.", ephemeral=True)
        return

    player_mentions = " ".join(
        dict.fromkeys(f"<@{user_id}>" for user_id in USER_MENTION_RE.findall(players_involved))
    )

    embed = discord.Embed(
        color=EMBED_COLOR,
        title="A player sent a roleplay request!",
        description=(
            f"**Roleplay:** {roleplay}\n"
            f"**Players Involved:** {players_involved}\n"
            f"**Duration:** {duration}"
        ),
    )
    embed.add_field(name="Requested By", value=interaction.user.mention)

    content_parts = [f"<@&{ROLEPLAY_PING_ROLE_ID}>", player_mentions]
    content = " ".join(part for part in content_parts if part)
    content += (
        f"\n-# The command is used by {interaction.user.mention}\n"
        f"-# Troll or random roleplay requests will result in a warning."
    )

    try:
        await channel.send(content=content, embed=embed, view=RoleplayRequestView(interaction.user))
    except Exception as exc:
        await interaction.followup.send(f"❌ Discord error: `{exc}`", ephemeral=True)
        return

    await interaction.followup.send(f"✅ Your roleplay request has been sent to {channel.mention}!", ephemeral=True)


@roleplay_request.error
async def roleplay_request_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes, seconds = divmod(round(error.retry_after), 60)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⏳ Please wait **{minutes} minutes {seconds} seconds** before using this command again.", ephemeral=True)
            else:
                await interaction.followup.send(f"⏳ Please wait **{minutes} minutes {seconds} seconds** before using this command again.", ephemeral=True)
        except Exception:
            pass
    else:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ An unexpected error occurred: `{error}`", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ An unexpected error occurred: `{error}`", ephemeral=True)
        except Exception:
            pass


@bot.tree.command(name="request-training", description="Request a training session.")
@app_commands.checks.has_role(TRAINING_ROLE_ID)
@app_commands.checks.cooldown(1, 900, key=lambda i: None)
async def request_training(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if interaction.channel_id != TRAINING_CHANNEL_ID:
        await interaction.followup.send(f"❌ This command can only be used in <#{TRAINING_CHANNEL_ID}>.", ephemeral=True)
        return

    embed = discord.Embed(
        color=EMBED_COLOR,
        description=f"**{interaction.user.mention} has requested a training!**\nIf you're going to host a training, please press the button below.",
    )
    try:
        await interaction.channel.send(
            content=f"<@&{TRAINING_ROLE_ID}>",
            embed=embed,
            view=HostTrainingView(interaction.user),
        )
        await interaction.followup.send("✅ Training request sent successfully!", ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"❌ Discord error: `{exc}`", ephemeral=True)


@request_training.error
async def request_training_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes, seconds = divmod(round(error.retry_after), 60)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⏳ Please wait **{minutes} minutes {seconds} seconds** before requesting training again.", ephemeral=True)
            else:
                await interaction.followup.send(f"⏳ Please wait **{minutes} minutes {seconds} seconds** before requesting training again.", ephemeral=True)
        except Exception:
            pass
    elif isinstance(error, app_commands.MissingRole):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ You don't have the required role to use this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ You don't have the required role to use this command.", ephemeral=True)
        except Exception:
            pass
    else:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ An unexpected error occurred: `{error}`", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ An unexpected error occurred: `{error}`", ephemeral=True)
        except Exception:
            pass


@bot.tree.command(name="setup-verify", description="Sends the verification panel.")
@app_commands.default_permissions(manage_guild=True)
async def setup_verify(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("❌ This command can only be used inside the server.", ephemeral=True)
        return

    channel = interaction.guild.get_channel(VERIFY_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message(f"❌ Verification channel not found (ID: `{VERIFY_CHANNEL_ID}`).", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    panel_exists = False
    try:
        async for old_message in channel.history(limit=50):
            if old_message.author != interaction.guild.me:
                continue
            for component in old_message.components:
                children = getattr(component, "children", None) or []
                for child in children:
                    if getattr(child, "custom_id", None) == "verify_button":
                        panel_exists = True
                        break
                if panel_exists:
                    break
            if panel_exists:
                break
    except Exception:
        pass

    if panel_exists:
        await interaction.followup.send(f"✅ A verification panel already exists in {channel.mention}.", ephemeral=True)
    else:
        try:
            await channel.send(
                "Welcome to **Colorado State Roleplay**! Click the button below to verify and gain full access.",
                view=VerifyView(),
            )
            await interaction.followup.send(f"✅ The verification panel has been sent to {channel.mention}.", ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(f"❌ Discord error: `{exc}`", ephemeral=True)


# ══════════════════════════════════════════════════════════════
#  ANTI-RAID EVENTS
# ══════════════════════════════════════════════════════════════

@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    guild = channel.guild
    try:
        channel_delete_snapshots[channel.id] = snapshot_channel(channel)
        _cap_snapshots()
        _save_anti_raid_state()
    except Exception:
        pass

    await asyncio.sleep(1)
    executor = None
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                executor = entry.user
                break
    except Exception:
        pass

    if executor is not None and executor.bot:
        channel_delete_snapshots.pop(channel.id, None)
        _save_anti_raid_state()
        return

    count = 0
    if executor is not None:
        channel_delete_counts[executor.id] = channel_delete_counts.get(executor.id, 0) + 1
        count = channel_delete_counts[executor.id]
        executor_channel_deletions.setdefault(executor.id, []).append(channel.id)

    notify_channel = guild.get_channel(ANTI_RAID_CHANNEL_ID)
    if notify_channel is not None:
        try:
            await notify_channel.send(
                content=f"<@&{ANTI_RAID_PING_ROLE_ID}>",
                embed=build_channel_delete_embed(channel, executor, count),
                view=AntiRaidView(executor, kind="channel", target_id=channel.id),
            )
        except Exception:
            pass

    if executor is not None and channel_delete_counts.get(executor.id, 0) >= CHANNEL_DELETE_LIMIT:
        member = guild.get_member(executor.id)
        if member is not None:
            await punish_member(member, guild)
            channel_delete_counts[executor.id] = 0
            recovered = await recover_executor_deletions(guild, executor.id, "channel")
            await notify_recovery(guild, member, "channel", recovered)

    _save_anti_raid_state()


@bot.event
async def on_guild_role_delete(role: discord.Role):
    guild = role.guild
    try:
        role_delete_snapshots[role.id] = snapshot_role(role)
        _cap_snapshots()
        _save_anti_raid_state()
    except Exception:
        pass

    await asyncio.sleep(1)
    executor = None
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                executor = entry.user
                break
    except Exception:
        pass

    if executor is not None and executor.bot:
        role_delete_snapshots.pop(role.id, None)
        _save_anti_raid_state()
        return

    count = 0
    if executor is not None:
        role_delete_counts[executor.id] = role_delete_counts.get(executor.id, 0) + 1
        count = role_delete_counts[executor.id]
        executor_role_deletions.setdefault(executor.id, []).append(role.id)

    notify_channel = guild.get_channel(ANTI_RAID_CHANNEL_ID)
    if notify_channel is not None:
        try:
            await notify_channel.send(
                content=f"<@&{ANTI_RAID_PING_ROLE_ID}>",
                embed=build_role_delete_embed(role, executor, count),
                view=AntiRaidView(executor, kind="role", target_id=role.id),
            )
        except Exception:
            pass

    if executor is not None and role_delete_counts.get(executor.id, 0) >= ROLE_DELETE_LIMIT:
        member = guild.get_member(executor.id)
        if member is not None:
            await punish_member(member, guild)
            role_delete_counts[executor.id] = 0
            recovered = await recover_executor_deletions(guild, executor.id, "role")
            await notify_recovery(guild, member, "role", recovered)

    _save_anti_raid_state()


# ══════════════════════════════════════════════════════════════
#  STAFF MANAGEMENT SYSTEM
# ══════════════════════════════════════════════════════════════

STAFF_RECORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "staff_records.json")
LIST_PAGE_SIZE = 10

RECORD_META = {
    "promotion":   {"prefix": "PROMO", "channel": PROMO_LOG_CHANNEL_ID, "label": "promotion"},
    "infraction":  {"prefix": "INFR",  "channel": INFR_LOG_CHANNEL_ID,  "label": "infraction"},
    "strike":      {"prefix": "STRK",  "channel": INFR_LOG_CHANNEL_ID,  "label": "strike"},
    "termination": {"prefix": "TERM",  "channel": INFR_LOG_CHANNEL_ID,  "label": "termination"},
}

TYPE_COLORS = {
    "promotion": 0xF1C40F,
    "infraction": 0xE67E22,
    "strike": 0x992D22,
    "termination": 0x2C3E50,
}

TYPE_TITLES = {
    "promotion": "🎖️ Staff Promotion",
    "infraction": "⚠️ Staff Infraction",
    "strike": "🚫 Staff Strike",
    "termination": "⛔ Staff Termination",
}

TYPE_VERBS = {
    "promotion": "Promoted",
    "infraction": "Infracted",
    "strike": "Struck",
    "termination": "Terminated",
}

TYPE_ICONS = {
    "promotion": "🎖️",
    "infraction": "⚠️",
    "strike": "🚫",
    "termination": "⛔",
}

CODE_FIELD_NAMES = {
    "promotion": "Promotion Code",
    "infraction": "Infraction Code",
    "strike": "Strike Code",
    "termination": "Termination Code",
}

STAFF_RECORDS: list[dict] = []


def _load_staff_records() -> None:
    try:
        with open(STAFF_RECORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        STAFF_RECORDS.extend(data if isinstance(data, list) else [])
    except (OSError, ValueError):
        pass


def _save_staff_records() -> None:
    try:
        with open(STAFF_RECORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(STAFF_RECORDS, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[!] Could not save staff records: {exc}")


_load_staff_records()


def has_role_or_higher(member: discord.Member, role_id: int) -> bool:
    if member.guild.owner_id == member.id:
        return True
    target = member.guild.get_role(role_id)
    if target is None:
        return False
    return any(r.position >= target.position for r in member.roles)


async def check_management(interaction: discord.Interaction) -> bool:
    member = interaction.user
    guild = interaction.guild
    if isinstance(member, discord.Member) and guild is not None:
        if has_role_or_higher(member, MANAGEMENT_ROLE_ID):
            return True
    await interaction.response.send_message("❌ You don't have the required role to use this command.", ephemeral=True)
    return False


async def check_role_or_higher(interaction: discord.Interaction, role_id: int, what: str) -> bool:
    member = interaction.user
    guild = interaction.guild
    if isinstance(member, discord.Member) and guild is not None:
        if has_role_or_higher(member, role_id):
            return True
    await interaction.response.send_message(f"❌ You don't have the required role to {what}.", ephemeral=True)
    return False


def generate_record_code(rtype: str) -> str:
    prefix = RECORD_META[rtype]["prefix"]
    while True:
        code = f"{prefix}-{''.join(random.choices(CODE_ALPHABET, k=6))}"
        if not any(r["code"] == code for r in STAFF_RECORDS):
            return code


def find_record(code: str, rtype: str) -> dict | None:
    code_upper = code.strip().upper()
    for record in STAFF_RECORDS:
        if record["code"].upper() == code_upper and record["type"] == rtype:
            return record
    return None


def create_record(
    rtype: str,
    *,
    member: discord.Member,
    executor: discord.Member | None,
    reason: str,
    tier: int | None = None,
    role_id: int | None = None,
    rank_role: discord.Role | None = None,
    system: bool = False,
) -> dict:
    record = {
        "code": generate_record_code(rtype),
        "type": rtype,
        "user_id": member.id,
        "user_name": member.name,
        "user_display": member.display_name,
        "user_avatar": str(member.display_avatar.url),
        "rank_id": rank_role.id if rank_role is not None else None,
        "rank_name": rank_role.name if rank_role is not None else None,
        "reason": reason,
        "executor_id": None if system else executor.id,
        "executor_name": "System" if system else executor.name,
        "executor_avatar": None if system else str(executor.display_avatar.url),
        "tier": tier,
        "role_id": role_id,
        "channel_id": RECORD_META[rtype]["channel"],
        "message_id": None,
        "status": "active",
        "system": system,
        "created_ts": int(time.time()),
        "revoked_ts": None,
        "revoked_by": None,
        "revoked_reason": None,
    }
    STAFF_RECORDS.append(record)
    _save_staff_records()
    return record


def status_text(record: dict) -> str:
    return "🟢 Active" if record.get("status", "active") == "active" else "🔴 Revoked"


def member_field_value(record: dict) -> str:
    return f"<@{record['user_id']}>\n**Username:** {record.get('user_name') or 'Unknown'}\n**Display Name:** {record.get('user_display') or '—'}\n**ID:** `{record['user_id']}`"


def build_staff_embed(record: dict) -> discord.Embed:
    rtype = record["type"]
    embed = discord.Embed(title=TYPE_TITLES[rtype], color=TYPE_COLORS[rtype])
    if record.get("user_avatar"):
        embed.set_thumbnail(url=record["user_avatar"])

    embed.add_field(
        name="Promoted Member" if rtype == "promotion" else "Staff Member",
        value=member_field_value(record),
        inline=False,
    )

    if rtype == "promotion" and record.get("rank_id"):
        embed.add_field(name="New Rank", value=f"<@&{record['rank_id']}>", inline=True)
    if rtype == "infraction" and record.get("tier") and record.get("role_id"):
        embed.add_field(name="Infraction Level", value=f"**Infraction {record['tier']}** — <@&{record['role_id']}>", inline=True)
    if rtype == "strike":
        embed.add_field(name="Strike Level", value=f"**Strike {record.get('tier', 1)}** — <@&{record['role_id']}>", inline=True)

    embed.add_field(name="Reason", value=record.get("reason") or "—", inline=False)
    embed.add_field(name=CODE_FIELD_NAMES[rtype], value=f"`{record['code']}`", inline=True)
    embed.add_field(name="Date", value=f"<t:{record['created_ts']}:F>", inline=True)
    embed.add_field(name="Status", value=status_text(record), inline=True)

    if record.get("status") == "revoked":
        embed.add_field(name="Revoked By", value=record.get("revoked_by") or "—", inline=True)
        embed.add_field(name="Revoked Reason", value=record.get("revoked_reason") or "—", inline=True)
        if record.get("revoked_ts"):
            embed.add_field(name="Revoked At", value=f"<t:{record['revoked_ts']}:F>", inline=True)

    executor_name = record.get("executor_name") or "System"
    footer_text = f"{TYPE_VERBS[rtype]} by {executor_name}"
    if record.get("system"):
        footer_text = "Struck by System"
    if record.get("executor_avatar"):
        embed.set_footer(text=footer_text, icon_url=record["executor_avatar"])
    else:
        embed.set_footer(text=footer_text)
    return embed


def record_content(record: dict) -> str:
    rtype = record["type"]
    mention = f"<@{record['user_id']}>"
    if rtype == "promotion":
        return f"🎉 {mention} you have been promoted to <@&{record['rank_id']}>! Congratulations!"
    if rtype == "infraction":
        return f"⚠️ {mention} you have received an infraction!"
    if rtype == "strike":
        text = f"🚫 {mention} you have received a strike!"
        if record.get("system"):
            text += "\n-# Done by the system due to 3 infractions."
        return text
    return f"⛔ {mention} you have received a termination!"


async def post_record(guild: discord.Guild, record: dict) -> bool:
    channel = guild.get_channel(record["channel_id"])
    if channel is None:
        return False
    try:
        message = await channel.send(content=record_content(record), embed=build_staff_embed(record))
        record["message_id"] = message.id
        _save_staff_records()
        return True
    except Exception as exc:
        print(f"[!] Could not post record: {exc}")
        return False


async def find_record_message(guild: discord.Guild, record: dict) -> discord.Message | None:
    channel = guild.get_channel(record["channel_id"])
    if channel is None:
        return None
    message_id = record.get("message_id")
    if message_id:
        try:
            return await channel.fetch_message(message_id)
        except Exception:
            pass

    code_upper = record["code"].upper()
    try:
        async for message in channel.history(limit=2000):
            if message.author != guild.me:
                continue
            for embed in message.embeds:
                for field in embed.fields:
                    if code_upper in (field.value or "").upper():
                        return message
    except Exception:
        pass
    return None


async def handle_infraction3_reached(member: discord.Member) -> None:
    guild = member.guild
    if any(guild.get_role(rid) in member.roles for rid in STRIKE_ROLE_IDS.values()):
        return

    strike1 = guild.get_role(STRIKE_ROLE_IDS[1])
    if strike1 is None:
        return
    try:
        await member.add_roles(strike1, reason="Automatic: 3 infractions completed")
    except Exception:
        return

    record = create_record(
        "strike",
        member=member,
        executor=None,
        reason="Automatic escalation (system).",
        tier=1,
        role_id=strike1.id,
        system=True,
    )
    await post_record(guild, record)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.roles == after.roles:
        return
    inf3 = after.guild.get_role(INFRACTION_ROLE_IDS[3])
    if inf3 is None:
        return
    if inf3 not in before.roles and inf3 in after.roles:
        await handle_infraction3_reached(after)


async def revoke_flow(interaction: discord.Interaction, rtype: str, code: str, reason: str) -> str:
    record = find_record(code, rtype)
    if record is None:
        return f"❌ No {RECORD_META[rtype]['label']} found with code `{code.strip().upper()}`."
    if record.get("status") == "revoked":
        return f"❌ This {RECORD_META[rtype]['label']} has already been revoked."

    removed_note = ""
    if record.get("role_id"):
        role = interaction.guild.get_role(record["role_id"])
        member = interaction.guild.get_member(record["user_id"])
        if role is not None and member is not None and role in member.roles:
            try:
                await member.remove_roles(role, reason=f"Revoke by {interaction.user.name}")
                removed_note = f"\n♻️ Role removed: **{role.name}**"
            except Exception:
                pass

    record.update({
        "status": "revoked",
        "revoked_by": f"{interaction.user.name} ({interaction.user.id})",
        "revoked_reason": reason,
        "revoked_ts": int(time.time()),
    })
    _save_staff_records()

    message = await find_record_message(interaction.guild, record)
    if message is not None:
        try:
            await message.reply(f"<@{record['user_id']}> This {RECORD_META[rtype]['label']} has been revoked. Reason: {reason}")
            await message.edit(embed=build_staff_embed(record))
        except Exception:
            pass

    return f"✅ {RECORD_META[rtype]['label']} `{record['code']}` revoked.{removed_note}"


def records_for_user(kind: str, user_id: int) -> list[dict]:
    if kind == "promotion":
        types = ("promotion",)
    else:
        types = ("infraction", "strike", "termination")
    return [r for r in STAFF_RECORDS if r["user_id"] == user_id and r["type"] in types][::-1]


class ListPaginationView(discord.ui.View):
    def __init__(self, author_id: int, kind: str, target_id: int, target_name: str):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.kind = kind
        self.target_id = target_id
        self.target_name = target_name
        self.page = 0
        self.message: discord.Message | None = None

    def build_page(self) -> discord.Embed:
        records = records_for_user(self.kind, self.target_id)
        total_pages = max(1, math.ceil(len(records) / LIST_PAGE_SIZE))
        self.page = min(max(self.page, 0), total_pages - 1)

        list_title = "Promotion List" if self.kind == "promotion" else "Infraction List"
        title = f"📋 Your {list_title}" if self.target_id == self.author_id else f"📋 {self.target_name}'s {list_title}"

        if not records:
            return discord.Embed(color=EMBED_COLOR, title=title, description="No records found for this user.")

        active = sum(1 for r in records if r.get("status", "active") == "active")
        revoked = len(records) - active

        embed = discord.Embed(color=EMBED_COLOR, title=title)
        if self.kind == "infraction":
            embed.description = "Includes infractions, strikes and terminations."

        start = self.page * LIST_PAGE_SIZE
        for record in records[start:start + LIST_PAGE_SIZE]:
            rtype = record["type"]
            if rtype == "promotion":
                short = f"Promoted to {record.get('rank_name') or '?'}"
            elif rtype == "infraction":
                short = f"Infraction {record.get('tier') or '—'}"
            elif rtype == "strike":
                short = f"Strike {record.get('tier', 1)}"
            else:
                short = "Termination"

            reason = (record.get("reason") or "—")[:150]
            value = f"**By:** {record.get('executor_name') or 'System'}\n**Date:** <t:{record['created_ts']}:d>\n**Reason:** {reason}\n**Status:** {status_text(record)}"
            embed.add_field(name=f"{TYPE_ICONS[rtype]} `{record['code']}` — {short}", value=value, inline=False)

        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} • {len(records)} total • {active} active • {revoked} revoked")
        return embed

    async def _render(self, interaction: discord.Interaction) -> None:
        embed = self.build_page()
        for child in self.children:
            child.disabled = False
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the user who ran the command can use this menu.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        await self._render(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        await self._render(interaction)


# ══════════════════════════════════════════════════════════════
#  STAFF MANAGEMENT COMMANDS
# ══════════════════════════════════════════════════════════════

@bot.tree.command(name="promote", description="Promote a staff member.")
@app_commands.describe(user="The staff member", rank="The new rank role", reason="Reason")
async def promote(interaction: discord.Interaction, user: discord.Member, rank: discord.Role, reason: str):
    if not await check_management(interaction):
        return
    await interaction.response.defer(ephemeral=True)

    try:
        if rank not in user.roles:
            await user.add_roles(rank, reason=f"Promotion by {interaction.user.name}")
    except Exception as exc:
        await interaction.followup.send(f"❌ Role grant error: `{exc}`", ephemeral=True)
        return

    record = create_record("promotion", member=user, executor=interaction.user, reason=reason, rank_role=rank)
    await post_record(interaction.guild, record)
    await interaction.followup.send(f"✅ {user.mention} promoted to {rank.mention}.\nCode: `{record['code']}`", ephemeral=True)


@bot.tree.command(name="revoke-promotion", description="Revoke a promotion.")
@app_commands.describe(code="Promotion code", reason="Reason")
async def revoke_promotion(interaction: discord.Interaction, code: str, reason: str):
    if not await check_management(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    result = await revoke_flow(interaction, "promotion", code, reason)
    await interaction.followup.send(result, ephemeral=True)


@bot.tree.command(name="infract", description="Give an infraction.")
@app_commands.describe(user="The staff member", reason="Reason")
async def infract(interaction: discord.Interaction, user: discord.Member, reason: str):
    if not await check_management(interaction):
        return
    await interaction.response.defer(ephemeral=True)

    tier, role = None, None
    for t in (1, 2, 3):
        candidate = interaction.guild.get_role(INFRACTION_ROLE_IDS[t])
        if candidate is not None and candidate not in user.roles:
            tier, role = t, candidate
            break

    if role is not None:
        try:
            await user.add_roles(role, reason=f"Infraction by {interaction.user.name}")
        except Exception:
            pass

    record = create_record("infraction", member=user, executor=interaction.user, reason=reason, tier=tier, role_id=role.id if role else None)
    await post_record(interaction.guild, record)
    await interaction.followup.send(f"✅ {user.mention} received an infraction.\nCode: `{record['code']}`", ephemeral=True)


@bot.tree.command(name="revoke-infraction", description="Revoke an infraction.")
@app_commands.describe(code="Infraction code", reason="Reason")
async def revoke_infraction(interaction: discord.Interaction, code: str, reason: str):
    if not await check_management(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    result = await revoke_flow(interaction, "infraction", code, reason)
    await interaction.followup.send(result, ephemeral=True)


@bot.tree.command(name="strike", description="Give a strike.")
@app_commands.describe(user="The staff member", reason="Reason")
async def strike(interaction: discord.Interaction, user: discord.Member, reason: str):
    if not await check_management(interaction):
        return
    await interaction.response.defer(ephemeral=True)

    tier, role = None, None
    for t in (1, 2, 3):
        candidate = interaction.guild.get_role(STRIKE_ROLE_IDS[t])
        if candidate is not None and candidate not in user.roles:
            tier, role = t, candidate
            break

    if role is not None:
        try:
            await user.add_roles(role, reason=f"Strike by {interaction.user.name}")
        except Exception:
            pass

    record = create_record("strike", member=user, executor=interaction.user, reason=reason, tier=tier, role_id=role.id if role else None)
    await post_record(interaction.guild, record)
    await interaction.followup.send(f"✅ {user.mention} received a strike.\nCode: `{record['code']}`", ephemeral=True)


@bot.tree.command(name="revoke-strike", description="Revoke a strike.")
@app_commands.describe(code="Strike code", reason="Reason")
async def revoke_strike(interaction: discord.Interaction, code: str, reason: str):
    if not await check_management(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    result = await revoke_flow(interaction, "strike", code, reason)
    await interaction.followup.send(result, ephemeral=True)


@bot.tree.command(name="terminate", description="Announce staff termination.")
@app_commands.describe(user="The staff member", reason="Reason")
async def terminate(interaction: discord.Interaction, user: discord.Member, reason: str):
    if not await check_management(interaction):
        return
    await interaction.response.defer(ephemeral=True)

    record = create_record("termination", member=user, executor=interaction.user, reason=reason)
    await post_record(interaction.guild, record)
    await interaction.followup.send(f"✅ Termination record created for {user.mention}.\nCode: `{record['code']}`", ephemeral=True)


@bot.tree.command(name="termination-revoke", description="Revoke a termination.")
@app_commands.describe(code="Termination code", reason="Reason")
async def termination_revoke(interaction: discord.Interaction, code: str, reason: str):
    if not await check_management(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    result = await revoke_flow(interaction, "termination", code, reason)
    await interaction.followup.send(result, ephemeral=True)


@bot.tree.command(name="promotion-list", description="View promotion history.")
@app_commands.describe(user="User whose list to view")
async def promotion_list(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    if user is None:
        if not await check_role_or_higher(interaction, LIST_ROLE_ID, "view your own list"):
            return
        target, ephemeral = interaction.user, True
    else:
        if not await check_role_or_higher(interaction, LIST_OTHERS_ROLE_ID, "view someone else's list"):
            return
        target, ephemeral = user, False

    view = ListPaginationView(interaction.user.id, "promotion", target.id, target.display_name)
    await interaction.response.send_message(embed=view.build_page(), view=view, ephemeral=ephemeral)


@bot.tree.command(name="infraction-list", description="View infraction history.")
@app_commands.describe(user="User whose list to view")
async def infraction_list(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    if user is None:
        if not await check_role_or_higher(interaction, LIST_ROLE_ID, "view your own list"):
            return
        target, ephemeral = interaction.user, True
    else:
        if not await check_role_or_higher(interaction, LIST_OTHERS_ROLE_ID, "view someone else's list"):
            return
        target, ephemeral = user, False

    view = ListPaginationView(interaction.user.id, "infraction", target.id, target.display_name)
    await interaction.response.send_message(embed=view.build_page(), view=view, ephemeral=ephemeral)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("\n[!] BOT_TOKEN not found in environment or .env file.\n")
    bot.run(BOT_TOKEN)
