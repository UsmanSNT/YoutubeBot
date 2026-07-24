# TODO (критически важные задачи для частного NAS-сценария)

- Валидация и логирование на старте: вызывать `setup_logger()` и `config.validate_all()` при запуске (например, в `run.py`/`bot.main`).
  Обоснование: раннее выявление ошибок конфигурации и корректные ротационные логи на NAS.

- Обновляемость yt-dlp: добавить make-таргет/скрипт для обновления yt-dlp или пересборки контейнера; задокументировать.
  Обоснование: YouTube часто меняет механики; редкое использование = высокий риск внезапных поломок без апдейта.

- Повторы и таймауты загрузок: настроить для yt-dlp `retries`, `fragment_retries`, `socket_timeout` и простой backoff.
  Обоснование: домашний интернет/NAS может быть нестабилен; снизит ложные ошибки.

- Очистка `data/temp` на старте и периодическая: удалять «висячие» файлы и всё старше N дней.
  Обоснование: после сбоев остаются остатки, место на NAS ограничено.

- Строгая валидация URL: парсить URL (urlparse) и проверять домены `*.youtube.*`/`youtu.be` вместо подстроки.
  Обоснование: избежать ложноположительных URL и бесполезных попыток скачивания.

- Экранирование HTML-разметки в сообщениях: экранировать динамические `title`/`URL` перед отправкой (ParseMode.HTML).
  Обоснование: предотвращает поломку разметки и нежелательные теги в сообщениях.

- Ограничение типов чатов: явно запрещать группы/супергруппы, работать только в приватных чатах.
  Обоснование: приватность данных для узкого круга пользователей.

- Бэкап и обслуживание SQLite: простой cron/скрипт — копия `data/bot.db` и `VACUUM` (например, при старте раз в неделю).
  Обоснование: снижает риск коррапции на NAS и неконтролируемого роста файла.

- Экспирация инвайтов: добавить TTL (например, 24–72 ч) и авто-деактивацию просроченных приглашений.
  Обоснование: утечка старой ссылки не должна давать постоянный доступ.

- Тюнинг лимитов очереди по умолчанию через `.env`: `MAX_QUEUE_SIZE=10`, `MAX_USER_TASKS=2` для домашней среды.
  Обоснование: ограниченные ресурсы NAS и редкое использование — меньше риск «забивания» очереди.

- Команда `/status`: показывать состояние (длина очереди, активность воркера, версия yt-dlp).
  Обоснование: быстрая диагностика без просмотра логов.

## Large File Support (>50MB)

### Current limitation:
- Maximum file size: 50MB due to Telegram Bot API limitation
- Files exceeding 50MB are blocked with user-friendly notification
- Users are guided to select lower quality formats (SD/HD) for large videos

### Future options to consider:

1. **Migration to Telethon/Pyrogram (MTProto)**
   - Support files up to 2GB using MTProto protocol
   - Pros: Native 2GB support, no additional infrastructure
   - Cons: Requires complete rewrite of bot logic from aiogram to telethon/pyrogram
   - Effort: High (complete refactoring)

2. **Local Bot API Server**
   - Support files up to 2GB with current aiogram framework
   - Pros: Minimal code changes, keeps existing aiogram logic
   - Cons: Requires additional server setup and maintenance
   - Effort: Medium (infrastructure + configuration changes)
   
3. **Hybrid approach**
   - Keep aiogram for commands and small files (<50MB)
   - Use telethon client for large file uploads only (50MB-2GB)
   - Pros: Best of both worlds, gradual migration
   - Cons: Added complexity, two Telegram clients
   - Effort: Medium-High

### Implementation priority:
Low - Current 50MB limit covers most use cases for personal NAS deployment.
Most YouTube videos in SD/HD quality are under 50MB for reasonable duration.

