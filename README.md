# Плагин NextcloudTalk для osysHome

Интеграция с Nextcloud Talk:
- отправка `say(...)` в комнату (action `say`)
- отправка уведомлений `addNotify(...)` (action `notify`)
- приём и выполнение команд из комнаты (action `cycle`, long-poll)

Использует Talk OCS API. Внешних зависимостей, кроме `requests`, нет.

## Установка

1. Скопируйте папку `NextcloudTalk` в `/opt/osysHome/plugins/NextcloudTalk`
2. `pip install -r /opt/osysHome/plugins/NextcloudTalk/requirements.txt` (обычно не нужно)
3. Включите плагин и перезапустите osysHome

## Настройка

Админка плагина (раздел «Модули» → Nextcloud Talk).

Подключение: `host`, `user`, `password`/app-token, `room` (токен комнаты), `verify_ssl`.

Уведомления: пересылка `say()`, мин. уровень, пересылка `addNotify()`, мин. категория,
отдельная комната для уведомлений.

Команды: включение, комната для команд (пусто = основная), интервал опроса, список команд (JSON).

## Команды

Поле «Команды (JSON)» — список объектов:

```json
[
  {"name": "status", "description": "Последнее сообщение системы", "code": "print(getProperty('SystemVar.LastSay'))"},
  {"name": "light", "description": "Свет в туалете on/off", "code": "callMethod('R_tualet.turnOn' if args == 'on' else 'R_tualet.turnOff')\nprint('готово')"}
]
```

Вызов в комнате: `/status`, `/light on`.

В коде команды доступны: `self`/`plugin` (экземпляр плагина), `message` (dict сообщения Talk),
`room`, `user` (actorId), `args` (текст после команды), `logger`, а также автоматически
подмешиваемые `setProperty`, `getProperty`, `callMethod`, `updateProperty`, `say`, `addNotify`.
Всё, что команда печатает через `print(...)`, отправляется обратно в комнату.

Приём реализован long-poll опросом (`GET .../spreed/api/v1/chat/{token}`); сообщения самого
бота игнорируются.
