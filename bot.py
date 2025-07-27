import discord
from discord.ext import commands
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from database import WebhookDatabase
import asyncio

# Load environment variables
load_dotenv()

# Set proper intents
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)
db = WebhookDatabase()

def create_event_data(message, event_type, **kwargs):
    """Create JSON payload for n8n"""
    return {
        "event_type": event_type,
        "timestamp": int(datetime.now().timestamp() * 1000),
        "content": {
            "text": message.content if hasattr(message, 'content') else str(message),
            "type": determine_content_type(message)
        },
        "author": {
            "id": str(message.author.id),
            "username": message.author.name,
            "discriminator": str(message.author.discriminator),
            "display_name": message.author.display_name,
            "avatar_url": str(message.author.avatar.url) if message.author.avatar else None
        },
        "channel": {
            "id": str(message.channel.id),
            "name": message.channel.name,
            "type": str(message.channel.type)
        },
        "guild": {
            "id": str(message.guild.id) if message.guild else None,
            "name": message.guild.name if message.guild else None
        },
        "message_id": str(message.id),
        "attachments": [
            {
                "id": str(att.id),
                "filename": att.filename,
                "url": att.url,
                "content_type": att.content_type
            } for att in message.attachments
        ],
        "mentions": [
            {
                "id": str(user.id),
                "username": user.name
            } for user in message.mentions
        ],
        "reply_to": str(message.reference.message_id) if message.reference else None,
        **kwargs
    }

def determine_content_type(message):
    """Determine content type"""
    if hasattr(message, 'attachments') and message.attachments:
        attachment = message.attachments[0]
        if attachment.content_type:
            if attachment.content_type.startswith('image/'):
                return 'image'
            elif attachment.content_type.startswith('video/'):
                return 'video'
            elif attachment.content_type.startswith('audio/'):
                return 'audio'
        return 'file'

    if hasattr(message, 'reference') and message.reference:
        return 'reply'

    if hasattr(message, 'content') and 'http' in message.content:
        return 'link'

    return 'text'

async def send_to_n8n(data, webhook_url):
    """Send data to n8n webhook"""
    try:
        response = requests.post(
            webhook_url,
            json=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Discord-n8n-Bot/1.0'
            },
            timeout=20
        )

        if response.status_code == 200:
            print(f"✅ Data sent to n8n successfully")
            return True
        else:
            print(f"❌ n8n returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending to n8n: {e}")
        return False
