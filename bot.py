"""
Openlympics 3.0 - FIFA Mobile tournament scheduling & results bot.

Handles the league-stage schedule (auto-generated round robin), match
results (goals for/against), points table with goal-difference tiebreak,
and lets an admin create knockout-stage matches once the league concludes.

Run with:
    BOT_TOKEN=xxxx INITIAL_ADMIN_ID=123456789 python bot.py
"""

import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
INITIAL_ADMIN_ID = os.environ.get("INITIAL_ADMIN_ID")

STAGE_ALIASES = {
    "league": "league", "table": "league", "l": "league",
    "round16": "round16", "r16": "round16",
    "quarterfinal": "quarterfinal", "quarter": "quarterfinal", "qf": "quarterfinal",
    "semifinal": "semifinal", "semi": "semifinal", "sf": "semifinal",
    "final": "final",
    "third_place": "third_place", "thirdplace": "third_place", "bronze": "third_place",
}


# ---------------------------------------------------------------- helpers --

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not db.is_admin(user.id):
            await update.message.reply_text(
                "This command is for admins only. Ask an existing admin to add you "
                "with /addadmin (they'll need your user id — see /whoami)."
            )
            return
        return await func(update, context)
    return wrapper


def stage_display_name(stage: str) -> str:
    return db.STAGE_LABELS.get(stage, stage.replace("_", " ").title())


def format_match_line(m) -> str:
    if m["status"] == "completed":
        g1, g2 = m["player1_goals"], m["player2_goals"]
        if m["winner"] == "DRAW":
            result = f"— DRAW ({g1}-{g2})"
        else:
            result = f"— {m['winner']} won ({g1}-{g2})"
        return f"#{m['id']} {m['player1']} vs {m['player2']} {result}"
    round_label = f" [{m['round_label']}]" if m["round_label"] else ""
    label = f" ({m['label']})" if m["label"] else ""
    return f"#{m['id']} {m['player1']} vs {m['player2']}{round_label}{label} — not played yet"


def format_table(rows, title: str) -> str:
    if not rows:
        return f"{title}\n\nNo completed matches yet."
    header = f"{'Player':<12}{'P':>3}{'W':>3}{'L':>3}{'D':>3}{'Pts':>5}{'GS':>5}{'GC':>5}{'GD':>5}"
    lines = [header, "-" * len(header)]
    for r in rows:
        lines.append(
            f"{r['player'][:12]:<12}{r['P']:>3}{r['W']:>3}{r['L']:>3}{r['D']:>3}"
            f"{r['Pts']:>5}{r['GS']:>5}{r['GC']:>5}{r['GD']:>5}"
        )
    body = "\n".join(lines)
    return f"{title}\n<pre>{body}</pre>"


# -------------------------------------------------------------- commands --

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ Openlympics 3.0 — FIFA Mobile tournament bot\n\n"
        "This bot tracks the league schedule, results, and points table, "
        "then knockout-stage matches once the league concludes.\n\n"
        "Type /help to see all commands."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = db.is_admin(update.effective_user.id)
    bot_username = context.bot.username or "your_bot"
    tag = f"@{bot_username}"
    text = (
        "<b>Public commands</b>\n"
        f"/players{tag} — list all participants\n"
        f"/schedule{tag} [round] — league fixtures, optionally one round e.g. 'Round 3'\n"
        f"/myfixtures{tag} &lt;name&gt; — all fixtures for one player\n"
        f"/table{tag} [league|round16|quarterfinal|semifinal|final|third_place] — points table\n"
        f"/result{tag} &lt;player1&gt; &lt;player2&gt; — look up a completed result\n"
        f"/pending{tag} [round] — matches not yet played\n"
        f"/whoami{tag} — show your Telegram user id\n"
    )
    if is_admin:
        text += (
            "\n<b>Admin commands</b>\n"
            f"/setresult{tag} &lt;player1&gt; &lt;player2&gt; &lt;goals1&gt; &lt;goals2&gt; — record a result\n"
            f"/editresult{tag} &lt;player1&gt; &lt;player2&gt; &lt;goals1&gt; &lt;goals2&gt; — fix a recorded result\n"
            f"/creatematch{tag} &lt;stage&gt; &lt;player1&gt; &lt;player2&gt; [label] — add a knockout match\n"
            "  stages: round16, quarterfinal, semifinal, final, third_place\n"
            f"/addplayer{tag} &lt;name&gt; — add a player (e.g. a replacement)\n"
            f"/removeplayer{tag} &lt;name&gt; — remove a player and delete all their matches\n"
            f"/deletematch{tag} &lt;match_id&gt; — delete a wrongly-created match\n"
            f"/addadmin{tag} &lt;user_id&gt; — add another admin\n"
            f"/removeadmin{tag} &lt;user_id&gt; — remove an admin\n"
            f"/listadmins{tag} — list current admins\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")


async def whoami_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Your Telegram user id: {user.id}\nUsername: @{user.username or '(none)'}"
    )


async def players_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    players = db.all_players()
    names = "\n".join(f"• {p['name']}" for p in players)
    await update.message.reply_text(f"Participants:\n{names}")


async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    round_label = " ".join(context.args) if context.args else None
    matches = db.matches_for_round(round_label)
    if not matches:
        await update.message.reply_text("No matches found for that round.")
        return
    lines = [format_match_line(m) for m in matches]
    title = "League schedule" + (f" — {round_label}" if round_label else "")
    await update.message.reply_text(title + "\n" + "\n".join(lines))


async def myfixtures_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /myfixtures <name>")
        return
    name = " ".join(context.args)
    player = db.find_player(name)
    if not player:
        await update.message.reply_text(f"No player named '{name}' found.")
        return
    matches = db.matches_for_player(player["name"])
    if not matches:
        await update.message.reply_text(f"No fixtures found for {player['name']}.")
        return
    lines = [format_match_line(m) for m in matches]
    await update.message.reply_text(f"Fixtures for {player['name']}:\n" + "\n".join(lines))


async def table_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.args[0].lower() if context.args else "league"
    stage = STAGE_ALIASES.get(key, key)
    rows = db.standings_for(stage)
    title = f"{stage_display_name(stage)} points table"
    await update.message.reply_text(format_table(rows, title), parse_mode="HTML")


async def result_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /result <player1> <player2>")
        return
    p1, p2 = context.args[0], context.args[1]
    match = db.find_completed_match(p1, p2)
    if not match:
        await update.message.reply_text("No completed match found between those two players.")
        return
    await update.message.reply_text(format_match_line(match))


async def pending_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    round_label = " ".join(context.args) if context.args else None
    matches = db.pending_matches(round_label=round_label, stage=db.LEAGUE_STAGE if round_label else None)
    if not round_label:
        matches = db.pending_matches()
    if not matches:
        await update.message.reply_text("No pending matches 🎉")
        return
    lines = [format_match_line(m) for m in matches]
    await update.message.reply_text("Pending matches:\n" + "\n".join(lines))


# --------------------------------------------------------- admin commands --

@admin_only
async def setresult_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text(
            "Usage: /setresult <player1> <player2> <goals1> <goals2>"
        )
        return
    p1, p2, g1s, g2s = context.args[0], context.args[1], context.args[2], context.args[3]
    try:
        g1, g2 = int(g1s), int(g2s)
    except ValueError:
        await update.message.reply_text("Goals must be numbers.")
        return

    match = db.find_pending_match(p1, p2)
    if not match:
        await update.message.reply_text(
            "No scheduled (unplayed) match found between those two players. "
            "If this is a new knockout match, create it first with /creatematch. "
            "If the result was already entered, use /editresult instead."
        )
        return

    if match["player1"].lower() == p1.lower():
        goals1, goals2 = g1, g2
    else:
        goals1, goals2 = g2, g1

    updated = db.set_result(match["id"], goals1, goals2)
    await update.message.reply_text("Result recorded:\n" + format_match_line(updated))


@admin_only
async def editresult_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text(
            "Usage: /editresult <player1> <player2> <goals1> <goals2>"
        )
        return
    p1, p2, g1s, g2s = context.args[0], context.args[1], context.args[2], context.args[3]
    try:
        g1, g2 = int(g1s), int(g2s)
    except ValueError:
        await update.message.reply_text("Goals must be numbers.")
        return

    match = db.find_completed_match(p1, p2)
    if not match:
        await update.message.reply_text("No completed match found between those two players to edit.")
        return

    if match["player1"].lower() == p1.lower():
        goals1, goals2 = g1, g2
    else:
        goals1, goals2 = g2, g1

    updated = db.set_result(match["id"], goals1, goals2)
    await update.message.reply_text("Result updated:\n" + format_match_line(updated))


@admin_only
async def creatematch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /creatematch <stage> <player1> <player2> [label]\n"
            "stages: round16, quarterfinal, semifinal, final, third_place"
        )
        return
    stage_key = context.args[0].lower()
    stage = STAGE_ALIASES.get(stage_key, stage_key)
    p1, p2 = context.args[1], context.args[2]
    label = " ".join(context.args[3:]) if len(context.args) > 3 else None

    for name in (p1, p2):
        if not db.find_player(name):
            await update.message.reply_text(
                f"'{name}' isn't a known player. Add them first with /addplayer if needed."
            )
            return

    match_id = db.create_match(stage, p1, p2, label=label)
    await update.message.reply_text(
        f"Created match #{match_id}: {p1} vs {p2} "
        f"({db.STAGE_LABELS.get(stage, stage)}{', ' + label if label else ''})"
    )


@admin_only
async def addplayer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /addplayer <name>")
        return
    name = context.args[0]
    ok = db.add_player(name)
    if ok:
        await update.message.reply_text(f"Added player: {name}")
    else:
        await update.message.reply_text(f"A player named '{name}' already exists.")


@admin_only
async def removeplayer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /removeplayer <name>\n"
            "This deletes the player AND every match they're in (league + any "
            "knockout stage, played or not) — this can't be undone."
        )
        return
    name = " ".join(context.args)
    result = db.remove_player(name)
    if not result:
        await update.message.reply_text(f"No player named '{name}' found.")
        return
    await update.message.reply_text(
        f"Removed {result['name']} and deleted {result['matches_deleted']} "
        f"associated match(es)."
    )


@admin_only
async def deletematch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /deletematch <match_id>\n(match ids show as #123 in /schedule, /pending, etc.)"
        )
        return
    try:
        match_id = int(context.args[0].lstrip("#"))
    except ValueError:
        await update.message.reply_text("match_id must be a number, e.g. /deletematch 42")
        return
    match = db.get_match(match_id)
    if not match:
        await update.message.reply_text(f"No match found with id #{match_id}.")
        return
    db.delete_match(match_id)
    await update.message.reply_text(
        f"Deleted match #{match_id}: {match['player1']} vs {match['player2']} "
        f"({stage_display_name(match['stage'])})."
    )


@admin_only
async def addadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("user_id must be a number. Ask them to run /whoami.")
        return
    ok = db.add_admin(user_id)
    if ok:
        await update.message.reply_text(f"Added admin: {user_id}")
    else:
        await update.message.reply_text(f"{user_id} is already an admin.")


@admin_only
async def removeadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("user_id must be a number.")
        return
    ok = db.remove_admin(user_id)
    await update.message.reply_text("Removed." if ok else "That user id wasn't an admin.")


@admin_only
async def listadmins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = db.list_admins()
    if not admins:
        await update.message.reply_text("No admins registered.")
        return
    lines = [f"• {a['user_id']}" + (f" ({a['name']})" if a["name"] else "") for a in admins]
    await update.message.reply_text("Admins:\n" + "\n".join(lines))


# ------------------------------------------------------------------ main --

def main():
    if not BOT_TOKEN:
        raise SystemExit("Set the BOT_TOKEN environment variable before running the bot.")

    db.init_db()

    if INITIAL_ADMIN_ID:
        db.ensure_admin(int(INITIAL_ADMIN_ID), "initial admin")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("whoami", whoami_cmd))
    app.add_handler(CommandHandler("players", players_cmd))
    app.add_handler(CommandHandler("schedule", schedule_cmd))
    app.add_handler(CommandHandler("myfixtures", myfixtures_cmd))
    app.add_handler(CommandHandler("table", table_cmd))
    app.add_handler(CommandHandler("result", result_cmd))
    app.add_handler(CommandHandler("pending", pending_cmd))

    app.add_handler(CommandHandler("setresult", setresult_cmd))
    app.add_handler(CommandHandler("editresult", editresult_cmd))
    app.add_handler(CommandHandler("creatematch", creatematch_cmd))
    app.add_handler(CommandHandler("addplayer", addplayer_cmd))
    app.add_handler(CommandHandler("removeplayer", removeplayer_cmd))
    app.add_handler(CommandHandler("deletematch", deletematch_cmd))
    app.add_handler(CommandHandler("addadmin", addadmin_cmd))
    app.add_handler(CommandHandler("removeadmin", removeadmin_cmd))
    app.add_handler(CommandHandler("listadmins", listadmins_cmd))

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
