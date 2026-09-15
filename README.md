# Openlympics 3.0 — Hand Cricket Scheduling Bot

A Telegram bot that handles **scheduling, results, and points tables** for
the Openlympics 3.0 hand cricket tournament. It does **not** run matches —
that's still done on the dedicated Hand Cricket bot. This bot is the
"admin layer" around it: fixtures, scorecards, and standings, all via
commands.

The full 27-player, 3-group, 4-day group-stage schedule is pre-loaded into
the database on first run (see `schedule_data.py`). Super 12 and playoff
matches are added by an admin as the tournament progresses, since those
pairings depend on results.

## How it works

- **Group Stage**: fixed round-robin, already scheduled (108 matches total).
- **Super 12 / Qualifiers / Semi-Finals / Final / Bronze Match**: created
  on demand by an admin with `/creatematch` once qualification is known.
- Every match result is a simple scoreline (runs for player 1, runs for
  player 2) since each player bats one 3-over innings. Win = 2 pts,
  Draw (tie) = 1 pt each, Loss = 0 pts. Margin/scorecard is stored and
  shown for every match.
- Standings are currently sorted by **points, then run differential**
  as a placeholder. If/when the official tiebreak rule (NRR, head-to-head,
  etc.) is confirmed, tell me and I'll wire that in exactly — the run data
  needed for NRR is already being tracked either way.

## Commands

**Public**
| Command | Description |
|---|---|
| `/groups` | List all groups and players |
| `/players <A\|B\|C>` | List players in a group |
| `/schedule <A\|B\|C> [day]` | Fixtures for a group, optionally filtered to one day e.g. `14/09` |
| `/myfixtures <name>` | All fixtures (played + upcoming) for one player |
| `/table <A\|B\|C\|super12\|...>` | Points table |
| `/result <player1> <player2>` | Look up a completed result |
| `/pending [A\|B\|C]` | Matches not yet played |
| `/whoami` | Shows your Telegram user id (needed to become admin) |

**Admin only**
| Command | Description |
|---|---|
| `/setresult <p1> <p2> <runs1> <runs2>` | Record a result for a scheduled match |
| `/editresult <p1> <p2> <runs1> <runs2>` | Correct an already-recorded result |
| `/creatematch <stage> <p1> <p2> [label]` | Add a Super12/playoff match (`stage`: `super12`, `qualifier`, `semifinal`, `final`, `bronze`) |
| `/addplayer <name> [group]` | Add a player (e.g. a replacement) |
| `/addadmin <user_id>` | Promote another user to admin |
| `/removeadmin <user_id>` | Revoke admin |
| `/listadmins` | List current admins |

## Setup (local)

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. `python3 -m venv venv && source venv/bin/activate`
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in `BOT_TOKEN`. Get your own
   Telegram user id from `@userinfobot` (or run the bot once and DM it
   `/whoami`) and set `INITIAL_ADMIN_ID` — this account becomes the first
   admin automatically on startup, and can then `/addadmin` others.
5. Load the env vars and run:
   ```bash
   export $(cat .env | xargs)
   python bot.py
   ```

## Deployment

### Railway (easiest)
1. Push this folder to a GitHub repo.
2. On [railway.app](https://railway.app): **New Project → Deploy from GitHub repo**.
3. In the service's **Variables** tab, add `BOT_TOKEN` and `INITIAL_ADMIN_ID`.
4. Railway auto-detects Python and runs `python bot.py` (it reads
   `requirements.txt` automatically). If it doesn't pick a start command,
   add a `Procfile` with: `worker: python bot.py`.
5. **Persistence matters**: SQLite writes to a local file, and Railway's
   filesystem is ephemeral on redeploys. Add a **Volume** in the service
   settings, mount it at e.g. `/data`, and set `DB_PATH=/data/handcricket.db`
   in Variables so results survive restarts/redeploys.

### Render
1. Push to GitHub, then **New → Background Worker** on
   [render.com](https://render.com), pointing at the repo.
2. Build command: `pip install -r requirements.txt`. Start command: `python bot.py`.
3. Add `BOT_TOKEN` and `INITIAL_ADMIN_ID` under **Environment**.
4. Same persistence note as Railway — add a **Disk**, mount it (e.g. `/data`),
   set `DB_PATH=/data/handcricket.db`.

### VPS (any Linux box you control)
1. `git clone` the repo, `pip install -r requirements.txt` (a virtualenv
   is recommended).
2. Set `BOT_TOKEN` / `INITIAL_ADMIN_ID` / `DB_PATH` as environment variables
   (e.g. in a `.env` file loaded by your process manager).
3. Keep it running with `systemd` or `pm2`/`supervisor`, e.g. a simple
   systemd unit:
   ```ini
   [Unit]
   Description=Hand Cricket Bot
   After=network.target

   [Service]
   WorkingDirectory=/opt/handcricket_bot
   EnvironmentFile=/opt/handcricket_bot/.env
   ExecStart=/opt/handcricket_bot/venv/bin/python bot.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Then `systemctl enable --now handcricket-bot`.
   No volume/disk concerns here — the SQLite file just lives on disk
   normally.

## Notes / things you may want to tell me later
- The **tiebreak rule** for standings (NRR vs head-to-head vs manual) — easy
  to add once you have it, since run data per match is already stored.
- Whether `/setresult` should require **both players to confirm** rather
  than trusting the admin's single entry — currently it's admin-entered
  only, matching "host's decision is final."
- Super 12 qualification is manual right now (admin picks who advances
  and creates their matches with `/creatematch`) — if you want, I can add
  a `/promote` command that auto-creates Super 12 fixtures from the
  group-stage standings once you tell me exactly how the 12 are chosen
  (e.g. top 4 per group) and what the Super 12 format is (round robin? how
  many rounds?).
