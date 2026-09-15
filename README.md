# Openlympics 3.0 — FIFA Mobile Tournament Bot

A Telegram bot that handles **scheduling, results, and the points table**
for the Openlympics 3.0 FIFA Mobile tournament. It works the same way as
the Hand Cricket bot from the same event, adapted for goals/points/goal
difference instead of runs.

## Format

- **League stage**: single round-robin — all 11 players play each other
  exactly once (55 matches, 11 rounds of 5 matches each). The schedule is
  auto-generated with a standard round-robin algorithm on first run, so
  it doesn't need to be typed in by hand — see `schedule_data.py`.
- **Knockouts**: added later by an admin with `/creatematch` once the
  league concludes and the bracket is known (e.g. quarter-finals, semis,
  final, third-place playoff).
- **Points**: Win = 2, Draw = 1, Loss = 0.
- **Tiebreaker**: goal difference (goals scored − goals conceded), then
  goals scored, if points are level. This is applied automatically in
  `/table`.

## Commands

**Public**
| Command | Description |
|---|---|
| `/players` | List all participants |
| `/schedule [round]` | League fixtures, optionally one round e.g. `Round 3` |
| `/myfixtures <name>` | All fixtures (played + upcoming) for one player |
| `/table [league\|round16\|quarterfinal\|semifinal\|final\|third_place]` | Points table (defaults to league) |
| `/result <player1> <player2>` | Look up a completed result |
| `/pending [round]` | Matches not yet played |
| `/whoami` | Shows your Telegram user id (needed to become admin) |

**Admin only**
| Command | Description |
|---|---|
| `/setresult <p1> <p2> <goals1> <goals2>` | Record a result for a scheduled match |
| `/editresult <p1> <p2> <goals1> <goals2>` | Correct an already-recorded result |
| `/creatematch <stage> <p1> <p2> [label]` | Add a knockout match (`stage`: `round16`, `quarterfinal`, `semifinal`, `final`, `third_place`) |
| `/addplayer <name>` | Add a player (e.g. a replacement) |
| `/addadmin <user_id>` | Promote another user to admin |
| `/removeadmin <user_id>` | Revoke admin |
| `/listadmins` | List current admins |

All commands also work in groups as `/command@YourBotUsername`.

## Setup (local)

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. `python3 -m venv venv && source venv/bin/activate`
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`, fill in `BOT_TOKEN`, and get your own
   Telegram user id from `@userinfobot` (or run the bot once and DM it
   `/whoami`) for `INITIAL_ADMIN_ID` — this account becomes the first
   admin automatically, and can `/addadmin` others afterward.
5. `export $(cat .env | xargs)` then `python bot.py`

## Deployment (Railway — same steps as the Hand Cricket bot)

1. Push this folder to a new GitHub repo.
2. On [railway.app](https://railway.app): **New Project → Deploy from GitHub repo**.
3. Service → **Variables** tab → add `BOT_TOKEN` and `INITIAL_ADMIN_ID`
   (no quotes around the values).
4. Add a **persistent Volume** (via the canvas — Cmd/Ctrl+K → "Volume", or
   right-click the canvas → Add Volume), mount it at `/data`, then add
   `DB_PATH=/data/fifa.db` in Variables. Without this, results are wiped
   on every redeploy.
5. Check Deployments → latest → Deploy Logs for "Bot starting..." and
   an "Application started" line with no errors.
6. Message the bot `/start`, `/whoami`, `/players`, `/schedule Round 1`
   to confirm everything loaded.

Render and VPS deployment follow the same pattern as documented in the
Hand Cricket bot's README, just with this repo instead.

## Notes
- Knockout bracket structure (Round of 16 vs straight to quarters, etc.)
  isn't hardcoded — you create each match manually with `/creatematch`
  as the bracket is decided, which keeps it flexible to however many
  players actually qualify.
- If you'd like automatic qualification (e.g. "top 8 from the league
  table advance") wired in later, let me know the exact cutoff and I can
  add a command that generates the knockout matches for you.
