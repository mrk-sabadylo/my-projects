import json
import os
from typing import Optional
from config import DATABASE_PATH


class Database:

    def __init__(self):
        self.db_path = DATABASE_PATH
        self._ensure_database()

    def _ensure_database(self):
        dir_path = os.path.dirname(self.db_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # якщо файла нема — створюємо
        if not os.path.exists(self.db_path):
            initial_data = {
                "max_slots": 50,
                "price": 0,
                "event_info": {"place": "", "time": "", "price": ""},
                "unregister_allowed": True,
                "registered_users": {},
                "blacklist": []
            }
            self._save_data(initial_data)
            return

        # якщо файл є — перевіряємо структуру
        data = self._load_data()
        changed = False

        if "price" not in data:
            data["price"] = 0
            changed = True

        if "event_info" not in data:
            data["event_info"] = {"place": "", "time": "", "price": ""}
            changed = True

        # 🔥 ФІКС СТАРОГО КЛЮЧА
        if "allow_unregister" in data and "unregister_allowed" not in data:
            data["unregister_allowed"] = data.pop("allow_unregister")
            changed = True

        if "unregister_allowed" not in data:
            data["unregister_allowed"] = True
            changed = True

        if "registered_users" not in data:
            data["registered_users"] = {}
            changed = True

        if "blacklist" not in data:
            data["blacklist"] = []
            changed = True

        if changed:
            self._save_data(data)

    def _load_data(self):
        with open(self.db_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_data(self, data):
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ===== EVENT INFO =====
    def get_event_info(self):
        return self._load_data().get("event_info", {"place": "", "time": "", "price": ""})

    def set_event_info(self, place, time, price):
        data = self._load_data()
        data["event_info"] = {"place": place, "time": time, "price": price}
        self._save_data(data)

    def clear_event_info(self):
        data = self._load_data()
        data["event_info"] = {"place": "", "time": "", "price": ""}
        self._save_data(data)

    # ===== REGISTRATION =====
    def is_user_registered(self, user_id: int) -> bool:
        return str(user_id) in self._load_data().get("registered_users", {})

    def register_user(self, user_id: int, name: str, username: Optional[str] = None) -> bool:
        data = self._load_data()

        if str(user_id) in data["registered_users"]:
            return False

        if user_id in data["blacklist"]:
            return False

        if len(data["registered_users"]) >= data["max_slots"]:
            return False

        from datetime import datetime
        data["registered_users"][str(user_id)] = {
            "name": name,
            "username": username,
            "registered_at": datetime.now().isoformat()
        }

        self._save_data(data)
        return True

    def unregister_user(self, user_id: int):
        data = self._load_data()
        data["registered_users"].pop(str(user_id), None)
        self._save_data(data)

    # ===== SLOTS =====
    def get_max_slots(self): return self._load_data()["max_slots"]
    def get_current_slots(self): return len(self._load_data()["registered_users"])
    def get_free_slots(self): return self.get_max_slots() - self.get_current_slots()
    def has_free_slots(self): return self.get_free_slots() > 0

    # ===== PRICE =====
    def get_price(self): return self._load_data()["price"]
    def set_price(self, price):
        data = self._load_data()
        data["price"] = price
        self._save_data(data)

    # ===== BLACKLIST =====

    def is_in_blacklist(self, user_id):
        return user_id in self._load_data()["blacklist"]

    def get_blacklist(self):
        return self._load_data().get("blacklist", [])

    # ===== UNREGISTER TOGGLE =====
    def is_unregister_allowed(self) -> bool:
        return self._load_data().get("unregister_allowed", True)

    def set_unregister_allowed(self, value: bool):
        data = self._load_data()
        data["unregister_allowed"] = value
        self._save_data(data)


    def get_all_registered(self):
        return self._load_data().get("registered_users", {})

    def clear_all_registrations(self):
        data = self._load_data()
        data["registered_users"] = {}
        self._save_data(data)

    def add_to_blacklist(self, user_id: int):
        data = self._load_data()
        if user_id not in data["blacklist"]:
            data["blacklist"].append(user_id)
            self._save_data(data)

    def remove_from_blacklist(self, user_id: int):
        data = self._load_data()
        if user_id in data["blacklist"]:
            data["blacklist"].remove(user_id)
            self._save_data(data)

db = Database()
