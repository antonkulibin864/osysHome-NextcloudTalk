# Плагин NextcloudTalk для osysHome

![NextcloudTalk ICON](static/NextcloudTalk.png)

Интеграция с Nextcloud Talk:
- отправка `say(...)` в комнату (action `say`)
- отправка уведомлений `addNotify(...)` (action `notify`)
- приём и выполнение команд из комнаты (action `cycle`, long-poll)

Использует Talk OCS API. Внешних зависимостей, кроме `requests`, нет.

## Настройка
Для работы модуля требуется работающий сервер Nexcloud и установленным расширением NextcloudTalk. На сервере регистрируется пользователь, и создается комната для сообщений.

Подключение: 

Адрес Nextcloud: https://192.168.1.1
Пользователь / бот -  имя пользователя зарегистрированного на сервере Nexscloud например: osyshome
Пароль или app-token - пароль зарегистрированного пользователя
Комната по умолчанию (токен) - fmza3yi6
Чтобы узнать токен комнаты  необходимо открыть чат комнаты из вебинтерфейса Nextcloud,  адрес чата комнаты будет выглядеть https://192.168.1.1/call/fmza3yi6. Токен  - fmza3yi6  

Уведомления: 
Пересылка `say()`, мин. уровень, 
Пересылка `addNotify()`, мин. категория,
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

