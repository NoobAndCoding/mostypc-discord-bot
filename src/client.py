import nextcord
from nextcord.ext import commands
from setup import setup_manager
import os

bot = commands.Bot(command_prefix = "!", intents = nextcord.Intents.all())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_member_join(member: nextcord.Member, interaction: nextcord.Interaction):
    channel = bot.get_channel(1325876532006355035, 1296427052664094780)
    embed = nextcord.Embed(
        color = nextcord.Color.blurple,
        type = "rich",
        title = f"Welcome to the MostyPC community {member.display_name}",
        description = "Hope you have a good time here!"
    )
    embed.thumbnail = member.avatar.url()
    await channel.send(embed = embed)

bot.run(os.getenv("TOKEN"))