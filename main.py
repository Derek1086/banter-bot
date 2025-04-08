import discord
from discord import app_commands
import os
import random
import asyncio
import datetime
from dotenv import load_dotenv
import openai
from openai import AsyncOpenAI

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
openai_api_key = os.getenv('OPENAI_API_KEY')

active_banter_users = {}

class BanterClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        
    async def setup_hook(self):
        await self.tree.sync()
        print("Command tree synced!")
        
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        
    async def on_member_join(self, member):
        """Sends a welcome message when a new member joins."""
        for channel in member.guild.text_channels:
            if channel.permissions_for(member.guild.me).send_messages:
                await channel.send(f"{member.mention} What's your business, traveler?")
                break

    async def on_message(self, message):
        """Handles incoming messages and generates responses if they are replies to the bot's messages."""
        if message.author.bot:
            return  # Ignore bot messages

        # Check if the message is a reply to a message sent by the bot
        if message.reference and message.reference.message_id in [msg.id for msg in self.cached_messages]:
            # Get the original bot message
            original_message = await message.channel.fetch_message(message.reference.message_id)

            # Only respond if it's a reply to the bot's banter message
            if original_message.author == self.user:
                # Generate a response based on the user's reply
                banter_response = await generate_banter(message.author.display_name, user_message=message.content)
                await message.channel.send(f"{message.author.mention} {banter_response}")


async def generate_banter(username, user_message=None):
    """
    Generates a witty banter message using OpenAI's GPT model.

    Args:
        username (str): The target username to include in the banter.
        user_message (str, optional): The message from the user to base the banter response on. Defaults to None.

    Returns:
        str: The generated banter message.
    """
    try:
        client = AsyncOpenAI(api_key=openai_api_key)

        # If the user provided a message, generate a response based on it
        if user_message:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a grumpy but lovable old British man who's full of witty insults, sarcasm, and dry humour. "
                            "You love a good cheeky roast and use British slang like 'muppet', 'numpty', 'bloke', 'dodgy', etc. "
                            "You're never cruel or hurtful — just snarky, clever, and endearingly rude. "
                            "Keep responses under 50 words. You're talking to a mate you’ve known for years."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Respond to {username}’s message with a witty, sarcastic, cheeky roast. The message was: {user_message}"
                    }
                ]
            )
        else:
            # Generate initial banter if no user message was provided
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a grumpy but lovable old British man who's full of witty insults, sarcasm, and dry humour. "
                            "You love a good cheeky roast and use British slang like 'muppet', 'numpty', 'bloke', 'dodgy', etc. "
                            "You're never cruel or hurtful — just snarky, clever, and endearingly rude. "
                            "Keep responses under 50 words. You're talking to a mate you’ve known for years."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Roast my mate {username} in a cheeky, British way. Be witty, sarcastic, and sound like an old British geezer."
                    }
                ]
            )

        # Return the banter message
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating banter: {e}")
        return f"Oi {username}, consider yourself lucky — my insult generator’s knackered today."


async def schedule_random_banter(user_id, max_seconds):
    """
    Schedule random banter messages throughout the day.

    Args:
        user_id (int): The ID of the user to send banter to.
        max_seconds (float): The maximum number of seconds until the end of the day to randomize banter timings.
    """
    user_data = active_banter_users.get(user_id)
    if not user_data:
        return
        
    # Generate a random number of messages to send
    num_messages = random.randint(2, 5)
    intervals = sorted([random.random() * max_seconds for _ in range(num_messages)])
    
    for interval in intervals:
        await asyncio.sleep(interval)
        
        # If the user is no longer active, stop sending banter
        if user_id not in active_banter_users:
            break
            
        user_data = active_banter_users[user_id]
        banter_message = await generate_banter(user_data['user'].display_name)
        await user_data['channel'].send(f"{user_data['user'].mention} {banter_message}")
    
    # Clean up after banter session ends
    if user_id in active_banter_users:
        del active_banter_users[user_id]


client = BanterClient()

@client.tree.command(name="banter", description="Start bantering with a user throughout the day")
@app_commands.describe(username="The user to banter with")
async def banter_command(interaction: discord.Interaction, username: discord.Member):
    """
    Starts a banter session with a user for the day.

    Args:
        interaction (discord.Interaction): The interaction that triggered the command.
        username (discord.Member): The user to banter with.

    Sends:
        A confirmation message and an initial banter message to the user.
    """
    target_user = username 

    if target_user.id in active_banter_users:
        await interaction.response.send_message(
            f"Already bantering with {target_user.display_name} today!", ephemeral=True
        )
        return

    now = datetime.datetime.now()
    end_of_day = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)
    seconds_until_end_of_day = (end_of_day - now).total_seconds()

    active_banter_users[target_user.id] = {
        'user': target_user,
        'channel': interaction.channel,
        'end_time': end_of_day
    }

    initial_banter = await generate_banter(target_user.display_name)

    await interaction.response.send_message(
        f"Starting a day of banter with {target_user.mention}!"
    )
    await interaction.channel.send(f"{target_user.mention} {initial_banter}")

    # Schedule random banter messages for the day
    client.loop.create_task(
        schedule_random_banter(target_user.id, seconds_until_end_of_day)
    )


@client.tree.command(name="welcome", description="Test the welcome message functionality")
@app_commands.describe(user="The user to welcome")
async def welcome_command(interaction: discord.Interaction, user: discord.Member):
    """
    Simulates a welcome message for a user.

    Args:
        interaction (discord.Interaction): The interaction that triggered the command.
        user (discord.Member): The user to simulate the welcome for.
    """
    await interaction.response.send_message(f"Simulating welcome for {user.mention}...", ephemeral=True)
    await client.on_member_join(user)

client.run(token)
