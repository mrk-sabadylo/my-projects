import json
import os
import uuid
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
                "blacklist": [],
                "known_users": {}
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

    # ===== CHECK REGISTRATION =====
    def is_user_registered(self, user_id: int) -> bool:
        return str(user_id) in self._load_data().get("registered_users", {})

    # ===== REGISTRATION =====
    def register_user(self, user_id: int, name: str, username: Optional[str] = None) -> bool:
        data = self._load_data()

        if str(user_id) in data["registered_users"]:
            return False

        if self.is_in_blacklist(user_id, username):
            return False

        if len(data["registered_users"]) >= data["max_slots"]:
            return False

        from datetime import datetime
        qr_token = str(uuid.uuid4())

        data["registered_users"][str(user_id)] = {
            "name": name,
            "username": username,
            "registered_at": datetime.now().isoformat(),
            "qr_token": qr_token
        }

        self._save_data(data)
        self.save_known_user(user_id, username)
        return True

    def unregister_user(self, user_id: int):
        data = self._load_data()
        data["registered_users"].pop(str(user_id), None)
        self._save_data(data)

    # ===== FRIENDS SYSTEM =====

    def get_max_friends(self):
        return self._load_data().get("max_friends_per_user", 0)

    def set_max_friends(self, count: int):
        data = self._load_data()
        data["max_friends_per_user"] = count
        self._save_data(data)

    def add_friend_to_user(self, user_id: int, name: str, username: str | None):
        data = self._load_data()
        user = data["registered_users"].get(str(user_id))
        if not user:
            return

        user.setdefault("friends", [])
        user["friends"].append({
            "name": name,
            "username": username
        })

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

    def is_in_blacklist(self, user_id: int, username: str | None = None) -> bool:
        data = self._load_data()
        bl = data.get("blacklist", [])

        if user_id in bl:
            return True

        if username and username.lower() in [str(x).lower() for x in bl]:
            return True

        if "known_users" not in data:
            data["known_users"] = {}

        return False

    def get_blacklist(self):
        return self._load_data().get("blacklist", [])


    # ===== KNOWN USERS (username → id) =====

    def save_known_user(self, user_id: int, username: Optional[str]):
        if not username:
            return
        data = self._load_data()
        data.setdefault("known_users", {})
        data["known_users"][username.lower()] = user_id
        self._save_data(data)

    def get_user_id_by_username(self, username: str):
        data = self._load_data()
        return data.get("known_users", {}).get(username.lower())


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

    def add_to_blacklist(self, value):
        data = self._load_data()
        if "blacklist" not in data:
            data["blacklist"] = []

        if value not in data["blacklist"]:
            data["blacklist"].append(value)
            self._save_data(data)

    def remove_from_blacklist(self, value):
        data = self._load_data()
        if value in data.get("blacklist", []):
            data["blacklist"].remove(value)
            self._save_data(data)


db = Database()
