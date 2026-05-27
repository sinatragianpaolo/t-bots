# t-bots

Personal Telegram bots collection.

## Structure

Each bot lives in its own directory at the root of the repo:

```
t-bots/
├── docker-compose.yml
├── bot-name/
│   ├── .env.example   # variable names, no values — commit this
│   ├── .env           # real values — never commit this
│   └── main.py
└── ...
```

## Adding a new bot

1. Create a new directory: `mkdir bot-name`
2. Add a `.env.example` with the required variable names
3. Copy it to `.env` and fill in the real values
4. Add a service to `docker-compose.yml`

## Running

```bash
docker compose up -d
```

Stop all:

```bash
docker compose down
```

Logs for a specific bot:

```bash
docker compose logs -f bot-name
```
