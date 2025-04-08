import discord
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('DISCORD_TOKEN')

class Client(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

intents = discord.Intents.default()
intents.message_content = True

client = Client(intents=intents)

client.run(token)
