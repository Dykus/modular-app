# Установщики: как выкладывать изменения

## Цикл работы (одинаков дома и на работе)

**На Windows-ПК (мастерская):**
1. Начало сессии: GitHub Desktop -> Fetch origin -> Pull origin.
2. Полученный установщик сохранить как `tools/installers/install.py` (UTF-8).
3. (Необязательно) проверить локально: `python install.py`, затем `python run.py`.
4. GitHub Desktop -> Summary по-русски -> Commit to main -> Push origin.

**На сервере (виртуалка / малина) — одна команда:**
```bash
cd ~/modular-app && ./update.sh
```
Скрипт сам: бэкап базы -> создаст `.env` при отсутствии -> `git pull` ->
обновит зависимости -> скопирует установщик в корень и запустит ->
перезапустит службу -> проверит HTTP.

## Правила

- Боевая база живёт **только на сервере**. Между ПК её не копируем.
- Перед работой — Pull, после работы — Push.
- На сервере код руками не правим: только `git pull`.
- Установщик кладём именно в `tools/installers/` — тогда он едет через Git
  (корневые `/install.py` и `/sync_*.py` скрыты в `.gitignore`).

## Откат

```bash
git log --oneline -10                 # найти хороший коммит
git reset --hard <хеш>                # на сервере безопасно: ручных правок нет
sudo systemctl restart modular-app
```

База из копии:
```bash
sudo systemctl stop modular-app
cp data/backups/db_ГГГГММДД_ЧЧММСС.db data/database.db
sudo systemctl start modular-app
```

## Диагностика

| Задача | Команда |
|---|---|
| Живой лог | `journalctl -u modular-app -f` |
| Последние 50 строк | `journalctl -u modular-app -n 50 --no-pager` |
| Отвечает ли HTTP | `curl -I http://127.0.0.1:5000/` |
| Таблицы базы | `sqlite3 data/database.db ".tables"` |
| Колонки таблицы | `sqlite3 data/database.db "PRAGMA table_info(custom_table);"` |
| Текущий релиз | `sqlite3 data/database.db "SELECT version,is_current FROM release ORDER BY id DESC LIMIT 3;"` |
