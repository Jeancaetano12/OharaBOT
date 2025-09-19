import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

@commands.command(name="play")
async def play(ctx, *, query: str):