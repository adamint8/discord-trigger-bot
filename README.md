# Discord Trigger Bot for n8n

A simple Discord bot that listens to messages and reactions in your Discord server and forwards them to **n8n webhooks**.
Built with Python, Discord.py, and a lightweight JSON-based database.

## 🚀 Features

✅ Forward messages (text, images, videos, files) to n8n webhooks
✅ Forward reactions (emoji adds) to n8n
✅ Slash commands and regular commands (`/setup`, `/remove`, `/status`, `/list`, `/test`)
✅ Stores webhooks per channel in a local JSON database
✅ Easy to deploy on **Raspberry Pi** or any Linux server

---

## 📦 Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/adamint8/discord-trigger-bot.git
cd discord-trigger-bot
```

### 2️⃣ Install dependencies

Make sure you have Python 3.9+ installed.

```bash
sudo apt update && sudo apt install python3-pip -y
pip install -r requirements.txt
```

### 3️⃣ Configure environment variables

Create a `.env` file in the project root:

```ini
DISCORD_TOKEN=your_discord_bot_token
```

⚠️ **Make sure to update the `.env` file with your own Discord bot token and any other credentials if needed.**

---

## ▶️ Running the Bot

```bash
python main.py
```

You should see:

```
🚀 Starting Discord n8n Trigger Bot...
🔗 Bot connected to Discord!
✅ Bot is ready! Logged in as YourBotName
```

---

## ⚙️ Commands

| Command        | Description                                |
| -------------- | ------------------------------------------ |
| `/setup <url>` | Set a webhook URL for the current channel  |
| `/remove`      | Remove webhook from the current channel    |
| `/status`      | Check the webhook status for the channel   |
| `/list`        | List all webhooks configured in the server |
| `/test`        | Test the webhook connection                |
| `!setup <url>` | Regular command version of setup           |
| `!ping`        | Check bot latency                          |
| `!info`        | Show bot information                       |

---

## 💾 Local Database

Webhooks are stored in `webhooks.json` in the same folder.
Each entry contains:

```json
{
  "channel_id": "1234567890",
  "webhook_url": "https://your-n8n-webhook",
  "guild_id": "987654321",
  "created_at": "2025-07-27T12:34:56",
  "active": true
}
```

---

## 🔧 Deploying on Raspberry Pi

1. Follow the installation steps above.
2. Make sure Python 3 and pip are installed:

   ```bash
   sudo apt install python3 python3-pip -y
   ```
3. (Optional) Run the bot as a service or use `screen`/`tmux` to keep it running.

---

## 📄 Notes

* You **must update the `.env` file** with your **Discord bot token** and any required credentials.
* Make sure your bot has the proper **Intents enabled** in the Discord Developer Portal.
