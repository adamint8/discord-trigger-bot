import discord
from discord.ext import commands
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from database import WebhookDatabase
import asyncio

# טעינת משתנים
load_dotenv()

# הגדרת intents נכונים
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)
db = WebhookDatabase()

def create_event_data(message, event_type, **kwargs):
    """יצירת JSON payload לn8n"""
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
    """קביעת סוג התוכן"""
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
    """שליחה לn8n webhook"""
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

async def test_webhook(webhook_url):
    """בדיקת webhook מהירה"""
    test_data = {
        "event_type": "test",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "content": {
            "text": "Test message from Discord bot",
            "type": "test"
        },
        "author": {
            "id": "test",
            "username": "Bot Test",
            "discriminator": "0000"
        }
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10  # 2 שניות בלבד
        )
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False

# Events
@bot.event
async def on_ready():
    print(f'✅ Bot is ready! Logged in as {bot.user}')
    print(f'📊 Bot is in {len(bot.guilds)} guilds')
    
    for guild in bot.guilds:
        print(f'   - {guild.name} (ID: {guild.id}) - {guild.member_count} members')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')

@bot.event
async def on_connect():
    print('🔗 Bot connected to Discord!')

@bot.event
async def on_disconnect():
    print('⚠️ Bot disconnected from Discord')

@bot.event
async def on_message(message):
    """טיפול בהודעות"""
    if message.author.bot:
        return
    
    print(f'📨 Message from {message.author.name} in #{message.channel.name}: {message.content}')
    
    webhook_url = db.get_channel_webhook(str(message.channel.id))
    if not webhook_url:
        print(f'   ⚠️ No webhook configured for channel #{message.channel.name}')
        await bot.process_commands(message)
        return
    
    event_data = create_event_data(message, 'message_create')
    success = await send_to_n8n(event_data, webhook_url)
    
    if success:
        print(f'   ✅ Message forwarded to n8n')
    else:
        print(f'   ❌ Failed to forward message')
    
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    """טיפול בreactions"""
    if user.bot:
        return
    
    print(f'👍 Reaction {reaction.emoji} from {user.name}')
    
    webhook_url = db.get_channel_webhook(str(reaction.message.channel.id))
    if not webhook_url:
        return
    
    event_data = create_event_data(reaction.message, 'reaction_add', **{
        "reaction": {
            "emoji": str(reaction.emoji),
            "count": reaction.count
        },
        "user": {
            "id": str(user.id),
            "username": user.name,
            "discriminator": str(user.discriminator)
        }
    })
    
    await send_to_n8n(event_data, webhook_url)

# Error handler for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """טיפול בשגיאות slash commands"""
    if isinstance(error, discord.app_commands.CommandInvokeError):
        if "Unknown interaction" in str(error):
            print(f"❌ Interaction timeout for {interaction.user.name}")
            # נסה לשלוח הודעה רגילה אם האינטראקציה פגה
            try:
                await interaction.channel.send(f"⚠️ {interaction.user.mention} הפקודה לקחה יותר זמן מהצפוי. נסה שוב.")
            except:
                pass
            return
    
    print(f"❌ App command error: {error}")

# Slash Commands - עם error handling מתקדם
@bot.tree.command(name="setup", description="הגדרת webhook לערוץ הנוכחי")
async def setup_webhook(interaction: discord.Interaction, webhook_url: str):
    """הגדרת webhook לערוץ"""
    print(f'🔧 Setup command from {interaction.user.name} in #{interaction.channel.name}')
    
    try:
        # בדיקות מיידיות
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ אין לך הרשאה לנהל ערוצים", ephemeral=True)
            return
        
        if not webhook_url.startswith('http'):
            await interaction.response.send_message("❌ URL לא תקין - חייב להתחיל ב-http או https", ephemeral=True)
            return
        
        # תשובה מיידית
        await interaction.response.send_message("⏳ בדיקת webhook...", ephemeral=True)
        
        # בדיקת webhook מהירה
        print(f'🔍 Testing webhook: {webhook_url}')
        is_valid = await test_webhook(webhook_url)
        
        # שמירה בDB (גם אם הwebhook נכשל, נשמור אותו)
        success = db.add_channel_webhook(
            str(interaction.channel.id),
            webhook_url,
            str(interaction.guild.id)
        )
        
        if success:
            print(f'✅ Webhook saved for channel #{interaction.channel.name}')
            
            if is_valid:
                embed = discord.Embed(
                    title="✅ Webhook הוגדר בהצלחה",
                    description=f"ערוץ: #{interaction.channel.name}",
                    color=0x00ff00
                )
                embed.add_field(name="URL", value=webhook_url[:50] + "...", inline=False)
                embed.add_field(name="סטטוס", value="🟢 פעיל ומחובר", inline=True)
                embed.add_field(name="בדיקה", value="✅ Webhook מגיב", inline=True)
            else:
                embed = discord.Embed(
                    title="⚠️ Webhook נשמר אבל יש בעיה",
                    description=f"ערוץ: #{interaction.channel.name}",
                    color=0xffaa00
                )
                embed.add_field(name="URL", value=webhook_url[:50] + "...", inline=False)
                embed.add_field(name="סטטוס", value="🟡 נשמר אבל לא מגיב", inline=True)
                embed.add_field(name="בדיקה", value="❌ בדוק שn8n פעיל", inline=True)
            
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            await interaction.edit_original_response(content="❌ שגיאה בשמירת הwebhook במסד הנתונים")
            
    except discord.NotFound:
        print(f"❌ Interaction expired for {interaction.user.name}")
        # שלח הודעה רגילה כתחליף
        try:
            await interaction.channel.send(f"⚠️ {interaction.user.mention} הפקודה לקחה יותר זמן מהצפוי. הwebhook נשמר אבל בדוק עם `/status`")
        except:
            pass
    except Exception as e:
        print(f"❌ Unexpected error in setup: {e}")
        try:
            await interaction.edit_original_response(content=f"❌ שגיאה לא צפויה: {str(e)}")
        except:
            pass

@bot.tree.command(name="remove", description="הסרת webhook מהערוץ הנוכחי")
async def remove_webhook(interaction: discord.Interaction):
    """הסרת webhook"""
    try:
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ אין לך הרשאה לנהל ערוצים", ephemeral=True)
            return
        
        success = db.remove_channel_webhook(str(interaction.channel.id))
        
        if success:
            await interaction.response.send_message("✅ Webhook הוסר בהצלחה מהערוץ הזה", ephemeral=True)
        else:
            await interaction.response.send_message("❌ אין webhook מוגדר לערוץ הזה", ephemeral=True)
    except Exception as e:
        print(f"❌ Error in remove command: {e}")

@bot.tree.command(name="status", description="בדיקת סטטוס webhook לערוץ הנוכחי")
async def webhook_status(interaction: discord.Interaction):
    """בדיקת סטטוס webhook"""
    try:
        webhook_url = db.get_channel_webhook(str(interaction.channel.id))
        
        if not webhook_url:
            await interaction.response.send_message("❌ אין webhook מוגדר לערוץ הזה", ephemeral=True)
            return
        
        # בדיקה מהירה
        await interaction.response.send_message("⏳ בודק סטטוס...", ephemeral=True)
        is_valid = await test_webhook(webhook_url)
        
        embed = discord.Embed(
            title=f"📊 סטטוס Webhook - #{interaction.channel.name}",
            color=0x00ff00 if is_valid else 0xffaa00
        )
        embed.add_field(name="URL", value=webhook_url[:50] + "...", inline=False)
        embed.add_field(name="סטטוס", value="🟢 פעיל ומחובר" if is_valid else "🟡 מוגדר אבל לא מגיב", inline=True)
        embed.add_field(name="בדיקה", value="✅ Webhook מגיב" if is_valid else "❌ בדוק שn8n פעיל", inline=True)
        
        await interaction.edit_original_response(content=None, embed=embed)
    except Exception as e:
        print(f"❌ Error in status command: {e}")

@bot.tree.command(name="list", description="הצגת כל הwebhooks בשרת")
async def list_webhooks(interaction: discord.Interaction):
    """הצגת רשימת webhooks"""
    try:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ אין לך הרשאה לנהל שרת", ephemeral=True)
            return
        
        webhooks = db.get_all_webhooks(str(interaction.guild.id))
        
        if not webhooks:
            await interaction.response.send_message("❌ אין webhooks מוגדרים בשרת הזה", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📊 רשימת Webhooks בשרת",
            description=f"סה\"כ: {len(webhooks)} ערוצים",
            color=0x0099ff
        )
        
        for webhook in webhooks:
            channel = interaction.guild.get_channel(int(webhook["channel_id"]))
            if channel:
                status = "🟢" if webhook.get("active", True) else "🔴"
                embed.add_field(
                    name=f"{status} #{channel.name}",
                    value=f"URL: {webhook['webhook_url'][:30]}...",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"❌ Error in list command: {e}")

@bot.tree.command(name="test", description="בדיקת חיבור webhook")
async def test_webhook_command(interaction: discord.Interaction):
    """בדיקת webhook"""
    try:
        webhook_url = db.get_channel_webhook(str(interaction.channel.id))
        
        if not webhook_url:
            await interaction.response.send_message("❌ אין webhook מוגדר לערוץ הזה. השתמש ב-/setup כדי להגדיר", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ בודק חיבור...", ephemeral=True)
        is_valid = await test_webhook(webhook_url)
        
        if is_valid:
            await interaction.edit_original_response(content="✅ בדיקת webhook הצליחה! הנתונים נשלחו לn8n")
        else:
            await interaction.edit_original_response(content="❌ שגיאה בwebhook - בדוק את הURL ושn8n פעיל")
    except Exception as e:
        print(f"❌ Error in test command: {e}")

# פקודות רגילות (כתחליף לslash commands)
@bot.command(name='setup')
async def setup_command(ctx, webhook_url: str = None):
    """הגדרת webhook עם פקודה רגילה"""
    if not webhook_url:
        await ctx.send("❌ שימוש: `!setup https://your-webhook-url`")
        return
    
    if not ctx.author.guild_permissions.manage_channels:
        await ctx.send("❌ אין לך הרשאה לנהל ערוצים")
        return
    
    if not webhook_url.startswith('http'):
        await ctx.send("❌ URL לא תקין - חייב להתחיל ב-http או https")
        return
    
    msg = await ctx.send("⏳ בדיקת webhook ושמירת הגדרות...")
    
    is_valid = await test_webhook(webhook_url)
    success = db.add_channel_webhook(str(ctx.channel.id), webhook_url, str(ctx.guild.id))
    
    if success:
        status = "🟢 פעיל ומחובר" if is_valid else "🟡 נשמר אבל לא מגיב"
        await msg.edit(content=f"✅ Webhook הוגדר בהצלחה!\n**ערוץ:** #{ctx.channel.name}\n**סטטוס:** {status}")
    else:
        await msg.edit(content="❌ שגיאה בשמירת הwebhook")

@bot.command(name='info')
async def info(ctx):
    """מידע על הBot"""
    embed = discord.Embed(
        title="🤖 Discord n8n Trigger Bot",
        description="Bot that forwards Discord messages to n8n webhooks",
        color=0x00ff00
    )
    embed.add_field(name="📊 Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="📡 Active Webhooks", value=len(db.get_all_webhooks(str(ctx.guild.id))), inline=True)
    embed.add_field(name="🔧 Commands", value="**Slash Commands:**\n/setup, /remove, /status, /list, /test\n\n**Regular Commands:**\n!setup, !info, !ping", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='ping')
async def ping(ctx):
    """בדיקת חיבור"""
    latency = round(bot.latency * 1000)
    await ctx.send(f'🏓 Pong! Latency: {latency}ms')

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Error: DISCORD_TOKEN not found in .env file")
        exit(1)
    
    print("🚀 Starting Discord n8n Trigger Bot...")
    print(f"🔑 Using token: {token[:25]}...")
    
    try:
        bot.run(token)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error running bot: {e}")
