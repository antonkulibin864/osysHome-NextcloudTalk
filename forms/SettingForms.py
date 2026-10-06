from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional


class SettingsForm(FlaskForm):
    host = StringField("Адрес Nextcloud", validators=[DataRequired()])
    user = StringField("Пользователь / бот", validators=[DataRequired()])
    password = StringField("Пароль или app-token", validators=[Optional()])
    room = StringField("Комната по умолчанию (токен)", validators=[DataRequired()])
    notify_room = StringField("Комната для уведомлений (пусто = основная)", validators=[Optional()])
    verify_ssl = BooleanField("Проверять SSL-сертификат")
    forward_say = BooleanField("Пересылать сообщения say()")
    min_say_level = IntegerField("Мин. уровень say", validators=[Optional(), NumberRange(min=0)], default=1)
    forward_notify = BooleanField("Пересылать уведомления addNotify()")
    min_notify_category = SelectField(
        "Мин. категория уведомлений",
        coerce=int,
        choices=[(0, "Debug"), (1, "Info"), (2, "Warning"), (3, "Error"), (4, "Fatal")],
        default=1,
    )
    command_enabled = BooleanField("Обрабатывать команды")
    command_room = StringField("Комната для команд (пусто = основная)", validators=[Optional()])
    command_poll_interval = IntegerField(
        "Интервал опроса, сек", validators=[Optional(), NumberRange(min=1, max=60)], default=3
    )
    commands = TextAreaField("Команды (JSON)", validators=[Optional()])
    submit = SubmitField("Сохранить")
