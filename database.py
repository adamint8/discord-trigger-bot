import json
import os
from datetime import datetime
from typing import Dict, List, Optional

DB_FILE = 'webhooks.json'

class WebhookDatabase:
    def __init__(self):
        self.db_file = DB_FILE
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """יצירת קובץ DB אם לא קיים"""
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump({"channels": {}}, f, indent=2)
    
    def _load_data(self) -> Dict:
        """טעינת נתונים מהקובץ"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"channels": {}}
    
    def _save_data(self, data: Dict) -> bool:
        """שמירת נתונים לקובץ"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return False
    
    def add_channel_webhook(self, channel_id: str, webhook_url: str, guild_id: str) -> bool:
        """הוספת webhook לערוץ"""
        try:
            data = self._load_data()
            data["channels"][channel_id] = {
                "webhook_url": webhook_url,
                "guild_id": guild_id,
                "created_at": datetime.now().isoformat(),
                "active": True
            }
            return self._save_data(data)
        except Exception as e:
            print(f"❌ Error adding webhook: {e}")
            return False
    
    def get_channel_webhook(self, channel_id: str) -> Optional[str]:
        """קבלת webhook URL לערוץ"""
        try:
            data = self._load_data()
            channel_data = data["channels"].get(channel_id)
            if channel_data and channel_data.get("active", True):
                return channel_data["webhook_url"]
            return None
        except Exception as e:
            print(f"❌ Error getting webhook: {e}")
            return None
    
    def remove_channel_webhook(self, channel_id: str) -> bool:
        """הסרת webhook מערוץ"""
        try:
            data = self._load_data()
            if channel_id in data["channels"]:
                del data["channels"][channel_id]
                return self._save_data(data)
            return False
        except Exception as e:
            print(f"❌ Error removing webhook: {e}")
            return False
    
    def get_all_webhooks(self, guild_id: str) -> List[Dict]:
        """קבלת כל הwebhooks של שרת"""
        try:
            data = self._load_data()
            results = []
            for channel_id, config in data["channels"].items():
                if config["guild_id"] == guild_id:
                    results.append({
                        "channel_id": channel_id,
                        "webhook_url": config["webhook_url"],
                        "guild_id": config["guild_id"],
                        "created_at": config["created_at"],
                        "active": config.get("active", True)
                    })
            return results
        except Exception as e:
            print(f"❌ Error getting all webhooks: {e}")
            return []
    
    def toggle_webhook(self, channel_id: str) -> bool:
        """הפעלה/כיבוי webhook"""
        try:
            data = self._load_data()
            if channel_id in data["channels"]:
                current = data["channels"][channel_id].get("active", True)
                data["channels"][channel_id]["active"] = not current
                return self._save_data(data)
            return False
        except Exception as e:
            print(f"❌ Error toggling webhook: {e}")
            return False
