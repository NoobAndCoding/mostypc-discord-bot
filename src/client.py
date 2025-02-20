import nextcord
from nextcord import SelectOption, SlashOption
from nextcord.ext import commands, tasks, application_checks
import asyncio
from setup import setup_manager
import os
from nextcord.ui import View, Select
import datetime
from collections import defaultdict
import aiomysql
import random
from easy_pil import *

qotd_data = {
    "question1": "Empty",
    "question2": "Empty",
    "question3": "Empty"
}

COUNTING_CHANNEL_ID = 1325876822436479028
QOTD_CHANNEL_ID = 1325877008655450183

bot = commands.Bot(command_prefix = "?", intents = nextcord.Intents.all())

async def create_pool():
    bot.db = await aiomysql.create_pool(
        host=os.getenv("DB_HOST"),
        port = 3306,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )

@tasks.loop(hours=24)  # Run every 24 hours
async def qotd_loop():
    channel = bot.get_channel(QOTD_CHANNEL_ID)
    
    if qotd_data["question1"]:  # Only send if there's a question
        embed = nextcord.Embed(
            title="Question of the Day! 🎉",
            description=f"**{qotd_data['question1']}**",
            color=nextcord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        await channel.send(embed=embed)

        # Shift Questions Forward
        qotd_data["question1"] = qotd_data["question2"]
        qotd_data["question2"] = qotd_data["question3"]
        qotd_data["question3"] = None  # Clear last slot

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await create_pool()
    print("Database connected")

    async with bot.db.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user BIGINT,
                    reason TEXT,
                    time INT,
                    guild BIGINT
                )
            """
            )
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS levels (
                    user BIGINT,
                    guild BIGINT,
                    level INT DEFAULT 0,
                    xp INT DEFAULT 0,
                    PRIMARY KEY (user, guild)
                )
            """
            )

async def addwarn(interaction: nextcord.Interaction, user, reason):
    async with bot.db.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO warnings (user, reason, time, guild) VALUES (%s, %s, %s, %s)",
                (user.id, reason, int(datetime.datetime.now().timestamp()), interaction.guild_id)
            )

@bot.slash_command(guild_ids=[1325874756624318515], description="Warns a user")
@application_checks.has_permissions(manage_messages=True)
async def warn(interaction: nextcord.Interaction, member: nextcord.Member, reason: str = "No reason provided."):
    await addwarn(interaction, member, reason)
    embed = nextcord.Embed(
        color=nextcord.Color.green(),
        title="Successfully logged warning",
        description=f"Warned {member.mention} for: {reason}"
    )
    embed.set_thumbnail(url=member.avatar.url)
    await interaction.send(embed=embed)


@bot.slash_command(guild_ids=[1325874756624318515], description="Remove's a user's warning")
@application_checks.has_permissions(manage_messages=True)
async def remove_warning(interaction: nextcord.Interaction, member: nextcord.Member, warning_id: int):
    async with bot.db.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT reason FROM warnings WHERE user = %s AND guild = %s AND id = %s", (member.id, interaction.guild_id, warning_id))
            data = await cursor.fetchone()
            if data:
                await cursor.execute("DELETE FROM warnings WHERE user = %s AND guild = %s AND id = %s", (member.id, interaction.guild_id, warning_id))
                embed = nextcord.Embed(
                    color=nextcord.Color.red(),
                    type="rich",
                    title="Successfully logged warning action",
                    description=f"Successfully removed warning from <@{member.id}>"
                )
                embed.set_thumbnail(url=member.avatar.url)
                await interaction.send(embed=embed)
            else:
                embed = nextcord.Embed(
                    title="404!",
                    description=f"No warnings found under <@{member.id}>'s account!",
                    colour=nextcord.Color.red(),
                    type="rich"
                )
                embed.set_thumbnail(url=member.avatar.url)
                await interaction.send(embed=embed)
    await bot.db.acquire()

@bot.slash_command(guild_ids=[1325874756624318515], description="Show a user's warnings")
@application_checks.has_permissions(manage_messages=True)
async def show_warnings(interaction: nextcord.Interaction, member: nextcord.Member):
    async with bot.db.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT reason, time, id FROM warnings WHERE user = %s and guild = %s", (member.id, interaction.guild_id))
            data = await cursor.fetchall()
            if data:
                embed = nextcord.Embed(
                    color=nextcord.Color.blurple(),
                    type="rich",
                    description=f"### {member.mention}'s warnings"
                )
                warnnum = 0
                for table in data:
                    warnnum += 1
                    embed.add_field(name=f"Warning No{warnnum}", value=f"Reason: {table[0]} \n Date Issued: <t:{int(table[1])}:F> \n Warning ID: {table[2]}", inline=False)
                    embed.set_thumbnail(url=member.avatar.url)
                await interaction.send(embed=embed)
            else:
                embed = nextcord.Embed(
                    title="404!",
                    description=f"No warnings found under <@{member.id}>'s account!",
                    colour=nextcord.Color.red(),
                    type="rich"
                )
                embed.set_thumbnail(url=member.avatar.url)
                await interaction.send(embed=embed)

@bot.event
async def on_member_join(member: nextcord.Member):
    channel_test = bot.get_channel(1296427052664094780)
    channel = bot.get_channel()
    embed = nextcord.Embed(
        color = nextcord.Color.blurple(),
        type = "rich",
        title = f"Welcome to the MostyPC community {member.display_name}",
        description = "Hope you have a good time here!"
    )
    embed.set_thumbnail(url = f"{member.avatar.url}")
    await channel.send(embed = embed)

class MyView(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.question1 = None
        self.question2 = None
        self.question3 = None
        self.add_item(MySelect(self))

class MyModal(nextcord.ui.Modal):
    def __init__(self, question: str, parent_view: MyView):
        super().__init__(
            title = "QOTD Edit Modal"
        )
        self.parent_view = parent_view    
        self.question = question

        self.answer = nextcord.ui.TextInput(
            label=f"Enter the qotd for {self.question}",
            placeholder="Type here...",
            required=True,
            max_length=150
        )

        self.add_item(self.answer)

    async def callback(self, interaction: nextcord.Interaction):
        answer = self.answer.value
        if self.question == "Question 1":
            qotd_data["question1"] = answer
        elif self.question == "Question 2":
            qotd_data["question2"] = answer
        elif self.question == "Question 3":
            qotd_data["question3"] = answer

        await interaction.response.send_message(f"✅ {self.question} updated: {answer}")

class MySelect(nextcord.ui.Select):
    question1 = None
    question2 = None
    question3 = None
    answer = None

    def __init__(self, parent_view: MyView):
        self.parent_view = parent_view
        options = [
            SelectOption(label = "Question No1 on queue", value = "Question 1", description = "Edit the Question, in the spot 1 on the queue",  emoji = "1️⃣"),
            SelectOption(label = "Question No2 on queue", value = "Question 2", description = "Edit the Question, in the spot 2 on the queue", emoji = "2️⃣"),
            SelectOption(label = "Question No3 on queue", value = "Question 3", description = "Edit the Question, in the spot 3 on the queue", emoji = "3️⃣"),
        ]
        super().__init__(placeholder = "Which question would you like to edit?", min_values=1, max_values=1, options = options)

    async def callback(self, interaction: nextcord.Interaction):
        selected_question = self.values[0]
        modal = MyModal(selected_question, self.parent_view)
        await interaction.response.send_modal(modal)


@bot.slash_command(guild_ids = [1325874756624318515])
@application_checks.has_permissions(manage_messages = True)
async def add_qotd(interaction: nextcord.Interaction, question):
    await interaction.send(view=MyView())
    embed = nextcord.Embed(
        color = nextcord.Color.blurple(),
        type = "rich",
        title = "Command Log",
        description = f"{interaction.user.mention} used the command: \"add_qotd\""
    )
    embed.set_thumbnail(url = f"{interaction.user.avatar.url}")

@bot.slash_command(guild_ids = [1325874756624318515])
@application_checks.has_permissions(manage_messages = True)
async def show_qotd(interaction: nextcord.Interaction):
    view = MyView()
    
    embed1 = nextcord.Embed(
        title = "Showing QOTD Queue",
        description= f"**Question 1:** { qotd_data.get("question1") } \n "
                     f"**Question 2:** { qotd_data.get("question2") } \n "
                     f"**Question 3:** { qotd_data.get("question3") } ",
        color = nextcord.Color.blurple()
    )
    await interaction.send(embed=embed1)
    embed = nextcord.Embed(
        color = nextcord.Color.blurple(),
        type = "rich",
        title = "Command Log",
        description = f"{interaction.user.mention} used the command: \"show_qotd\""
    )
    embed.set_thumbnail(url = f"{interaction.user.avatar.url}")
    await interaction.send(embed=embed)
    

current_count = 0
last_user = None
count_leaderboard = defaultdict(int)  # Leaderboard stored as a dictionary

@bot.event
async def on_message(message):
    global current_count, last_user, count_leaderboard

    if message.channel.id == COUNTING_CHANNEL_ID:
        # ✅ Check if the message contains ONLY a number
        if not message.content.isdigit():
            return

        number = int(message.content)  # Convert message to an integer

        if number != current_count + 1:
            await message.add_reaction("❌")  # React red ❌ for incorrect count
            return

        if message.author.id == last_user and not message.author.bot:
            await message.add_reaction("❌")  # React red ❌ for duplicate user count
            await message.channel.send(
                f"{message.author.mention} ruined the count! Resetting to 0 and clearing the leaderboard.",
                delete_after=45  # ⏳ Auto-delete after 45 seconds
            )
            current_count = 0
            last_user = None
            count_leaderboard.clear()  # 🔥 Leaderboard is reset!
            return

        # ✅ Correct count
        await message.add_reaction("✅")  # React green ✅
        current_count = number
        last_user = message.author.id

        if not message.author.bot:  # Don't track bot counts
            count_leaderboard[message.author.id] += 1  # Add to leaderboard

    await bot.process_commands(message)  # Ensure commands still work

@bot.slash_command()
async def leaderboard(interaction):
    """Shows the top counters."""
    if not count_leaderboard:
        await interaction.send("Leaderboard is empty! Start counting to earn a rank.", delete_after=45)
        return

    sorted_leaderboard = sorted(count_leaderboard.items(), key=lambda x: x[1], reverse=True)
    embed = nextcord.Embed(title="📊 Counting Leaderboard", color=nextcord.Color.gold())

    for rank, (user_id, score) in enumerate(sorted_leaderboard[:10], start=1):  # Top 10 users
        user = await bot.fetch_user(user_id)
        embed.add_field(name=f"#{rank} {user.display_name}", value=f"✅ {score} counts", inline=False)

    await interaction.send(embed=embed, delete_after=45)  # ⏳ Auto-delete after 45 seconds

@bot.event
async def on_message(message: nextcord.Message):
    if message.author.bot:
        return
    author = message.author
    guild = message.guild
    async with bot.db.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT xp, level FROM levels WHERE user = %s AND guild = %s", (author.id, guild.id))
            result = await cursor.fetchone()
            
            if not result:
                await cursor.execute("INSERT INTO levels (user, guild, level, xp) VALUES (%s, %s, %s, %s)", (author.id, guild.id, 0, 0))
                xp, level = 0, 0
            else:
                xp, level = result

            xp += random.randint(2, 4)
            if xp >= 100:
                level += 1
                xp = 0
                await message.channel.send(f"{author.mention} has leveled up to level **{level}**!")
            
            await cursor.execute("UPDATE levels SET xp = %s, level = %s WHERE user = %s AND guild = %s", (xp, level, author.id, guild.id))
    
    await bot.process_commands(message)



@bot.command(aliases=["lvl", "r", "l"])
async def level(ctx: commands.Context, member: nextcord.Member = None):
    if member is None:
        member = ctx.author
    async with bot.db.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT xp, level FROM levels WHERE user = %s AND guild = %s", (ctx.author.id, ctx.guild.id))
            result = await cursor.fetchone()

            if not result[0] or not result[1]:
                await cursor.execute("INSERT IGNORE INTO levels (level, xp, user, guild) VALUES (%s, %s, %s, %s)", (0, 0, ctx.author.id, ctx.guild.id))
                await bot.db.acquire()

            try:
                xp = result[0]
                level = result[1]
            except TypeError:
                xp = 0
                level = 0

            user_data = {
                "name": f"{member.name}#{member.discriminator}",
                "xp": xp,
                "level": level,
                "next_level_xp": 100,
                "percentage": xp,
            }

            background_picture = load_image("https://fv5-3.files.fm/thumb_show.php?i=2qj7e9k5gx&view&v=1&PHPSESSID=6c183193f76950210215614bff7bb1747b9bd197")
            background1 = Editor(background_picture)
            background = Editor(Canvas((900, 300), color = "#FFFFFF"))
            profile_picture = await load_image_async(str(member.avatar.url))
            profile = Editor(profile_picture).resize((150, 150)).circle_image()
            
            poppins = Font.poppins(variant = "bold", size = 40)
            poppins_small = Font.poppins(size = 30)

            background.paste(background1, (0, 0))

            background.rectangle((28, 28), width = 154, height = 154, radius = 77, color = "black")
            background.paste(profile, (30, 30))
            
            background.rectangle((30, 220), width = 840, height = 40, color = "#FFFFFF", radius = 5, outline = "black", stroke_width = 2)
            background.bar((30, 220), max_width = 840, height = 40, percentage = user_data["percentage"], color = "black", radius = 5)

            background.text((200, 40), user_data["name"], font = poppins, )

            background.rectangle((200, 100), width = 350, height = 2, fill = "black")

            background.text((200, 110), f"Level - {user_data["level"]}", font = poppins_small)
            background.text((200, 135), f"XP - {user_data["xp"]}/{user_data["next_level_xp"]}", font = poppins_small)

            file = nextcord.File(fp = background.image_bytes, filename = "levelcard.png")

    await ctx.channel.send(file = file)

bot.run(os.getenv("TOKEN"))