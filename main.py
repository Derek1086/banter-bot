import discord
from discord import app_commands
import os
import random
import asyncio
import datetime
import signal
import sys
from dotenv import load_dotenv
import openai
from openai import AsyncOpenAI
from keep_alive import keep_alive

load_dotenv(override=True)
token = os.getenv("DISCORD_TOKEN")
openai_api_key = os.getenv('OPENAI_API_KEY')

class BanterClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.recent_responders = {}
        
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
        if message.reference and message.reference.message_id:
            try:
                # Get the original bot message
                original_message = await message.channel.fetch_message(message.reference.message_id)
                
                # Only respond if it's a reply to the bot's message
                if original_message.author == self.user:
                    # Generate a response based on the user's reply
                    banter_response = await generate_banter(message.author.display_name, user_message=message.content)
                    await message.channel.send(f"{message.author.mention} {banter_response}")
            except discord.errors.NotFound:
                # Original message was deleted or not found
                pass


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
                            "Keep responses under 50 words. You're talking to a mate you've known for years."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Respond to {username}'s message with a witty, sarcastic, cheeky roast. The message was: {user_message}"
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
                            "Keep responses under 50 words. You're talking to a mate you've known for years."
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
        return f"Oi {username}, consider yourself lucky — my insult generator's knackered today."


client = BanterClient()

@client.tree.command(name="banter", description="Banter with a user")
@app_commands.describe(username="The user to banter with")
async def banter_command(interaction: discord.Interaction, username: discord.Member):
    """
    Starts a banter interaction with a user.

    Args:
        interaction (discord.Interaction): The interaction that triggered the command.
        username (discord.Member): The user to banter with.

    Sends:
        A banter message to the specified user.
    """
    # Prevent self-banter
    if username.id == interaction.client.user.id:
        await interaction.response.send_message(
            "Oi, I'm not roasting meself, mate. Pick someone else.", ephemeral=True
        )
        return

    target_user = username 

    # Generate and send banter
    initial_banter = await generate_banter(target_user.display_name)
    
    await interaction.response.send_message(
        f"Starting some banter with {target_user.mention}!"
    )
    await interaction.channel.send(f"{target_user.mention} {initial_banter}")


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


@client.tree.command(name="shutdown", description="Safely shut down the bot (admin only)")
async def shutdown_command(interaction: discord.Interaction):
    """
    Safely shuts down the bot.
    
    Args:
        interaction (discord.Interaction): The interaction that triggered the command.
    """
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to shut down the bot.", ephemeral=True)
        return
    
    await interaction.response.send_message("Shutting down the bot...", ephemeral=True)
    print("Shutdown command received. Shutting down...")
    
    await client.close()
    os._exit(0)


def signal_handler(sig, frame):
    print(f"Received signal {sig}. Shutting down...")
    
    # Schedule the shutdown coroutine
    if client.loop.is_running():
        asyncio.create_task(shutdown())
    else:
        sys.exit(0)


async def shutdown():
    """Performs graceful shutdown of the bot."""
    print("Closing Discord connection...")
    await client.close()
    
    # Wait a moment to ensure connections are closed
    await asyncio.sleep(1)
    
    os._exit(0)


signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Kill command

keep_alive()

if __name__ == "__main__":
    try:
        client.run(token)
    except Exception as e:
        print(f"Error running bot: {e}")
        print(f"Error type: {type(e).__name__}")