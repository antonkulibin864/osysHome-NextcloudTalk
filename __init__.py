"""NextcloudTalk plugin for osysHome.

Sends osysHome say()/addNotify() messages to Nextcloud Talk and processes
slash commands received from a Talk room (long-poll).
"""

import json

import requests
import urllib3

from app.core.main.BasePlugin import BasePlugin
from app.core.lib.execute import execute_and_capture_output
from plugins.NextcloudTalk.forms.SettingForms import SettingsForm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CATEGORIES = {0: "Debug", 1: "Info", 2: "Warning", 3: "Error", 4: "Fatal"}
MAX_REPLY = 4000


class NextcloudTalk(BasePlugin):

    def __init__(self, app):
        super().__init__(app, "NextcloudTalk")
        self.title = "Nextcloud Talk"
        self.description = "Уведомления и команды osysHome через Nextcloud Talk"
        self.category = "App"
        self.author = "MCP"
        self.version = "0.2"
        self.actions = ["say", "notify", "cycle"]
        self._last_ids = {}

    def _base(self):
        return (self.config.get("host") or "").strip().rstrip("/")

    def _verify(self):
        return bool(self.config.get("verify_ssl", False))

    def _timeout(self):
        try:
            return int(self.config.get("timeout", 20) or 20)
        except (TypeError, ValueError):
            return 20

    def _headers(self):
        return {"OCS-APIRequest": "true", "Accept": "application/json"}

    def _auth(self):
        return (self.config.get("user") or "", self.config.get("password") or "")

    def _chat_url(self, room):
        return self._base() + "/ocs/v2.php/apps/spreed/api/v1/chat/" + str(room)

    def send_message(self, message, room=None):
        target = (room or self.config.get("room") or "").strip()
        if not self._base() or not self.config.get("user") or not target:
            self.logger.warning("NextcloudTalk: заполните host, user, password, room")
            return False
        text = str(message)
        if len(text) > MAX_REPLY:
            text = text[:MAX_REPLY] + "\n..."
        try:
            resp = requests.post(
                self._chat_url(target),
                headers=self._headers(),
                auth=self._auth(),
                data={"message": text},
                verify=self._verify(),
                timeout=self._timeout(),
            )
            if resp.status_code < 300:
                return True
            self.logger.error("NextcloudTalk: HTTP %s %s", resp.status_code, resp.text[:200])
            return False
        except Exception as ex:
            self.logger.exception("NextcloudTalk: ошибка отправки: %s", ex)
            return False

    def _get_messages(self, room, last_id, timeout):
        params = {
            "lookIntoFuture": 1,
            "limit": 50,
            "lastKnownMessageId": int(last_id or 0),
            "timeout": int(timeout),
            "includeLastKnown": 0,
            "setReadMarker": 0,
            "markNotificationsAsRead": 0,
        }
        resp = requests.get(
            self._chat_url(room),
            headers=self._headers(),
            auth=self._auth(),
            params=params,
            verify=self._verify(),
            timeout=int(timeout) + 15,
        )
        if resp.status_code >= 300:
            self.logger.error("NextcloudTalk: чтение чата HTTP %s %s", resp.status_code, resp.text[:200])
            return []
        try:
            data = (resp.json() or {}).get("ocs", {}).get("data", [])
        except ValueError:
            return []
        return data if isinstance(data, list) else []

    def _get_last_message_id(self, room):
        try:
            resp = requests.get(
                self._chat_url(room),
                headers=self._headers(),
                auth=self._auth(),
                params={"lookIntoFuture": 0, "limit": 1, "setReadMarker": 0, "markNotificationsAsRead": 0},
                verify=self._verify(),
                timeout=self._timeout(),
            )
            data = (resp.json() or {}).get("ocs", {}).get("data", []) or []
            if data:
                return max(int(m.get("id", 0)) for m in data)
        except Exception as ex:
            self.logger.exception("NextcloudTalk: не удалось получить последний id: %s", ex)
        return 0

    def initialization(self):
        self._last_ids = {}
        if not (self._base() and self.config.get("user") and self.config.get("room")):
            self.logger.warning("NextcloudTalk: задайте host, user, password и room в настройках")

    def say(self, message, level=0, args=None):
        if not self.config.get("forward_say", True):
            return
        try:
            min_level = int(self.config.get("min_say_level", 1))
        except (TypeError, ValueError):
            min_level = 1
        if level < min_level:
            return
        self.send_message(message)

    def notify(self, data):
        if not self.config.get("forward_notify", True):
            return
        if not isinstance(data, dict) or data.get("operation") != "new_notify":
            return
        info = data.get("data") or {}
        try:
            cat = int(info.get("category", 1))
        except (TypeError, ValueError):
            cat = 1
        try:
            min_cat = int(self.config.get("min_notify_category", 1))
        except (TypeError, ValueError):
            min_cat = 1
        if cat < min_cat:
            return
        text = "[" + CATEGORIES.get(cat, "Info") + "] " + str(info.get("name") or "Notification")
        description = info.get("description")
        if description:
            text += "\n" + str(description)
        source = info.get("source")
        if source:
            text += "\n[" + str(source) + "]"
        room = (self.config.get("notify_room") or "").strip() or None
        self.send_message(text, room=room)

    def _commands(self):
        raw = self.config.get("commands", [])
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return []
        result = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and item.get("name") and item.get("code"):
                    result.append({
                        "name": str(item.get("name")).lstrip("/").strip().lower(),
                        "description": str(item.get("description") or ""),
                        "code": str(item.get("code")),
                    })
        return result

    def _command_room(self):
        return (self.config.get("command_room") or "").strip() or (self.config.get("room") or "").strip()

    def cyclic_task(self):
        interval = 3
        try:
            interval = int(self.config.get("command_poll_interval", 3))
        except (TypeError, ValueError):
            interval = 3
        interval = max(1, min(60, interval))

        room = self._command_room()
        if not self.config.get("command_enabled", False) or not room or not self._base():
            self.event.wait(5.0)
            return

        if room not in self._last_ids:
            self._last_ids[room] = self._get_last_message_id(room)

        try:
            messages = self._get_messages(room, self._last_ids[room], interval)
        except Exception as ex:
            self.logger.exception("NextcloudTalk: ошибка чтения чата: %s", ex)
            self.event.wait(interval)
            return

        for msg in messages:
            try:
                mid = int(msg.get("id", 0))
            except (TypeError, ValueError):
                mid = 0
            if mid > self._last_ids[room]:
                self._last_ids[room] = mid
            self._handle_message(room, msg)

    def _handle_message(self, room, msg):
        if str(msg.get("messageType")) == "system":
            return
        actor_id = str(msg.get("actorId") or "")
        if actor_id and actor_id == str(self.config.get("user") or ""):
            return
        text = str(msg.get("message") or "").strip()
        if not text.startswith("/"):
            return
        parts = text[1:].split(None, 1)
        if not parts:
            return
        name = parts[0].split("@")[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        command = next((c for c in self._commands() if c["name"] == name), None)
        if not command:
            self.send_message("Неизвестная команда: /" + name, room=room)
            return
        self.logger.info("NextcloudTalk: команда /%s от %s", name, actor_id or "?")
        variables = {
            "self": self,
            "plugin": self,
            "message": msg,
            "room": room,
            "user": actor_id,
            "args": args,
            "logger": self.logger,
        }
        try:
            output, error = execute_and_capture_output(command["code"], variables)
        except Exception as ex:
            self.logger.exception("NextcloudTalk: ошибка выполнения команды: %s", ex)
            self.send_message("Ошибка выполнения команды (см. лог)", room=room)
            return
        reply = (output or "").strip()
        if error:
            reply = "Ошибка:\n" + reply if reply else "Ошибка выполнения команды"
        if not reply:
            reply = "OK"
        self.send_message(reply, room=room)

    def admin(self, request):
        settings = SettingsForm()
        message = None
        if request.method == "GET":
            settings.host.data = self.config.get("host", "")
            settings.user.data = self.config.get("user", "")
            settings.password.data = self.config.get("password", "")
            settings.room.data = self.config.get("room", "")
            settings.notify_room.data = self.config.get("notify_room", "")
            settings.verify_ssl.data = bool(self.config.get("verify_ssl", False))
            settings.forward_say.data = bool(self.config.get("forward_say", True))
            settings.min_say_level.data = int(self.config.get("min_say_level", 1))
            settings.forward_notify.data = bool(self.config.get("forward_notify", True))
            settings.min_notify_category.data = int(self.config.get("min_notify_category", 1))
            settings.command_enabled.data = bool(self.config.get("command_enabled", False))
            settings.command_room.data = self.config.get("command_room", "")
            settings.command_poll_interval.data = int(self.config.get("command_poll_interval", 3))
            settings.commands.data = json.dumps(self.config.get("commands", []), ensure_ascii=False, indent=2)
        else:
            action = request.form.get("action", "save")
            if action == "test":
                ok = self.send_message(request.form.get("test_text") or "osysHome: тестовое сообщение")
                message = "Сообщение отправлено" if ok else "Ошибка отправки (см. лог плагина)"
            elif settings.validate_on_submit():
                try:
                    commands = json.loads(settings.commands.data or "[]")
                    if not isinstance(commands, list):
                        raise ValueError("должен быть список")
                except (json.JSONDecodeError, ValueError) as ex:
                    message = "Ошибка в JSON команд: " + str(ex)
                    return self.render("admin.html", {"form": settings, "message": message})
                self.config["host"] = (settings.host.data or "").strip()
                self.config["user"] = (settings.user.data or "").strip()
                self.config["password"] = settings.password.data or ""
                self.config["room"] = (settings.room.data or "").strip()
                self.config["notify_room"] = (settings.notify_room.data or "").strip()
                self.config["verify_ssl"] = bool(settings.verify_ssl.data)
                self.config["forward_say"] = bool(settings.forward_say.data)
                self.config["min_say_level"] = settings.min_say_level.data if settings.min_say_level.data is not None else 1
                self.config["forward_notify"] = bool(settings.forward_notify.data)
                self.config["min_notify_category"] = settings.min_notify_category.data if settings.min_notify_category.data is not None else 1
                self.config["command_enabled"] = bool(settings.command_enabled.data)
                self.config["command_room"] = (settings.command_room.data or "").strip()
                self.config["command_poll_interval"] = settings.command_poll_interval.data if settings.command_poll_interval.data is not None else 3
                self.config["commands"] = commands
                self._last_ids = {}
                self.saveConfig()
                message = "Настройки сохранены"
            else:
                message = "Проверьте поля формы"
        return self.render("admin.html", {"form": settings, "message": message})
