# Restore from Backup

This guide explains how to restore your Music Tool Bot from the daily backups.

## Backup Contents

Each backup produces two files (per run):

| File                          | Contents                             |
|-------------------------------|--------------------------------------|
| `postgres_<timestamp>.sql.gz` | Full PostgreSQL database dump        |
| `bot_data_<timestamp>.tar.gz` | Bot data directory (`/data`) contents |

## Prerequisites

- Docker and Docker Compose installed
- The backup files you want to restore from (located in `./backups/`)
- The `DB_USERNAME` and `DB_DATABASE` values used by your deployment. The commands below read them from your shell, so
  export them first (e.g. `set -a; source .env; set +a`) or substitute the literal values.

## Restore PostgreSQL Database

### Step 1: Ensure the database service is running

```bash
docker compose up -d postgres
```

### Step 2: Find the backup file

```bash
ls -lh ./backups/postgres_*.sql.gz
```

### Step 3: Restore the database

```bash
gunzip -c ./backups/postgres_<timestamp>.sql.gz | \
  docker compose exec -T postgres \
    psql -U "${DB_USERNAME}" -d "${DB_DATABASE}"
```

**Note:** The dump includes `--clean --if-exists` flags, so it will drop existing tables before recreating them.

## Restore Bot Data

### Step 1: Stop the bot container

```bash
docker compose stop bot
```

### Step 2: Find the backup file

```bash
ls -lh ./backups/bot_data_*.tar.gz
```

### Step 3: Restore the data

```bash
docker run --rm \
  -v $(pwd)/backups:/backups:ro \
  -v music-tool-bot_bot_data:/data \
  alpine:latest \
  sh -c "tar -xzf /backups/bot_data_<timestamp>.tar.gz -C /data"
```

The archive holds the contents of `/data` at its root (`./persistence.pickle`, `./downloads/…`), so extracting with `-C /data` restores it in place.

Alternatively, if you're using a bind mount for the data directory:

```bash
tar -xzf ./backups/bot_data_<timestamp>.tar.gz -C ./data
```

### Step 4: Restart the bot

```bash
docker compose start bot
```

## Restore Everything (Full Disaster Recovery)

If you're setting up on a brand new machine:

```bash
git clone <your-repo-url> music-tool-bot
cd music-tool-bot

cp .env.example .env

docker compose up -d postgres

docker compose exec postgres pg_isready -U "${DB_USERNAME}"

docker compose up -d
```

## Verify the Restore

```bash
# Check that users exist
docker compose exec postgres psql -U "${DB_USERNAME}" -d "${DB_DATABASE}" -c "SELECT COUNT(*) FROM users;"

# Check that the bot starts without errors
docker compose logs bot