"""
Openlympics 3.0 - Hand Cricket scheduling & results bot.

This bot does NOT run the matches themselves (a separate Hand Cricket bot
is used for that). It only handles: fixtures/schedule, recording and
correcting results, and points tables, across the Group Stage, Super 12,
and Playoffs.

Run with:
    BOT_TOKEN=xxxx INITIAL_ADMIN_ID=123456789 python bot.py
"""

import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import db
from schedule_data import GROUPS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
INITIAL_ADMIN_ID = os.environ.get("INITIAL_ADMIN_ID")

STAGE_ALIASES = {
    "group": "group", "groups": "group", "a": "group", "b": "group", "c": "group",
    "super12": "super12", "super 12": "super12", "s12": "super12",
    "qualifier": "qualifier", "qualifiers": "qualifier",
    "semifinal": "semifinal", "semi": "semifinal", "sf": "semifinal",
    "final": "final",
    "bronze": "bronze",
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


def format_match_line(m) -> str:
    if m["status"] == "completed":
        r1, r2 = m["player1_runs"], m["player2_runs"]
        if m["winner"] == "DRAW":
            result = f"— TIE ({r1}-{r2})"
        else:
            margin = abs(r1 - r2)
            result = f"— {m['winner']} won by {margin} run{'s' if margin != 1 else ''} ({r1}-{r2})"
        return f"#{m['id']} {m['player1']} vs {m['player2']} {result}"
    day = f" [{m['match_day']}]" if m["match_day"] else ""
    label = f" ({m['label']})" if m["label"] else ""
    return f"#{m['id']} {m['player1']} vs {m['player2']}{day}{label} — not played yet"


def format_table(rows, title: str) -> str:
    if not rows:
        return f"{title}\n\nNo completed matches yet."
    header = f"{'Player':<12}{'P':>3}{'W':>3}{'L':>3}{'D':>3}{'Pts':>5}{'RS':>6}{'RC':>6}{'RD':>6}"
    lines = [header, "-" * len(header)]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{r['player'][:12]:<12}{r['P']:>3}{r['W']:>3}{r['L']:>3}{r['D']:>3}"
            f"{r['Pts']:>5}{r['RS']:>6}{r['RC']:>6}{r['RD']:>6}"
        )
    body = "\n".join(lines)
    return f"{title}\n<pre>{body}</pre>"


# -------------------------------------------------------------- commands --

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏏 Openlympics 3.0 — Hand Cricket scheduling bot\n\n"
        "This bot tracks fixtures, results, and points tables.\n"
        "Matches themselves are played on the Hand Cricket bot.\n\n"
        "Type /help to see all commands."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = db.is_admin(update.effective_user.id)
    text = (
        "<b>Public commands</b>\n"
        "/groups — list groups and players\n"
        "/players &lt;A|B|C&gt; — list players in a group\n"
        "/schedule &lt;A|B|C&gt; [day] — fixtures for a group (day like 14/09)\n"
        "/myfixtures &lt;name&gt; — all fixtures for one player\n"
        "/table &lt;A|B|C|super12|...&gt; — points table for a stage/group\n"
        "/result &lt;player1&gt; &lt;player2&gt; — look up a completed result\n"
        "/pending [A|B|C] — matches not yet played\n"
        "/whoami — show your Telegram user id\n"
    )
    if is_admin:
        text += (
            "\n<b>Admin commands</b>\n"
            "/setresult &lt;player1&gt; &lt;player2&gt; &lt;runs1&gt; &lt;runs2&gt; — record a result\n"
            "/editresult &lt;player1&gt; &lt;player2&gt; &lt;runs1&gt; &lt;runs2&gt; — fix a recorded result\n"
            "/creatematch &lt;stage&gt; &lt;player1&gt; &lt;player2&gt; [label] — add a Super12/playoff match\n"
            "  stages: super12, qualifier, semifinal, final, bronze\n"
            "/addplayer &lt;name&gt; [group] — add a player (e.g. a replacement)\n"
            "/addadmin &lt;user_id&gt; — add another admin\n"
            "/removeadmin &lt;user_id&gt; — remove an admin\n"
            "/listadmins — list current admins\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")


async def whoami_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Your Telegram user id: {user.id}\nUsername: @{user.username or '(none)'}"
    )


async def groups_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = []
    for grp in sorted(db.all_groups()):
        players = db.players_in_group(grp)
        names = ", ".join(p["name"] for p in players)
        lines.append(f"<b>Group {grp}</b>: {names}")
    await update.message.reply_text("\n\n".join(lines), parse_mode="HTML")


async def players_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /players <A|B|C>")
        return
    grp = context.args[0]
    players = db.players_in_group(grp)
    if not players:
        await update.message.reply_text(f"No players found in group '{grp}'.")
        return
    names = "\n".join(f"• {p['name']}" for p in players)
    await update.message.reply_text(f"Group {grp.upper()} players:\n{names}")


async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /schedule <A|B|C> [day e.g. 14/09]")
        return
    grp = context.args[0]
    day = context.args[1] if len(context.args) > 1 else None
    matches = db.matches_for_group(grp, day)
    if not matches:
        await update.message.reply_text("No matches found for that group/day.")
        return
    lines = [format_match_line(m) for m in matches]
    title = f"Group {grp.upper()} schedule" + (f" — {day}" if day else "")
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
    if not context.args:
        await update.message.reply_text(
            "Usage: /table <A|B|C|super12|qualifier|semifinal|final|bronze>"
        )
        return
    key = context.args[0].lower()
    if key in ("a", "b", "c"):
        grp = key.upper()
        rows = db.standings_for("group", grp)
        title = f"Group {grp} points table"
    else:
        stage = STAGE_ALIASES.get(key, key)
        rows = db.standings_for(stage)
        title = f"{db.STAGE_LABELS.get(stage, stage.title())} points table"
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
    grp = context.args[0] if context.args else None
    matches = db.pending_matches(grp)
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
            "Usage: /setresult <player1> <player2> <runs1> <runs2>"
        )
        return
    p1, p2, r1s, r2s = context.args[0], context.args[1], context.args[2], context.args[3]
    try:
        r1, r2 = int(r1s), int(r2s)
    except ValueError:
        await update.message.reply_text("Runs must be numbers.")
        return

    match = db.find_pending_match(p1, p2)
    if not match:
        await update.message.reply_text(
            "No scheduled (unplayed) match found between those two players. "
            "If this is a new Super12/playoff match, create it first with /creatematch. "
            "If the result was already entered, use /editresult instead."
        )
        return

    # runs are given in the order the user typed the names
    if match["player1"].lower() == p1.lower():
        runs1, runs2 = r1, r2
    else:
        runs1, runs2 = r2, r1

    updated = db.set_result(match["id"], runs1, runs2)
    await update.message.reply_text("Result recorded:\n" + format_match_line(updated))


@admin_only
async def editresult_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text(
            "Usage: /editresult <player1> <player2> <runs1> <runs2>"
        )
        return
    p1, p2, r1s, r2s = context.args[0], context.args[1], context.args[2], context.args[3]
    try:
        r1, r2 = int(r1s), int(r2s)
    except ValueError:
        await update.message.reply_text("Runs must be numbers.")
        return

    match = db.find_completed_match(p1, p2)
    if not match:
        await update.message.reply_text(
            "No completed match found between those two players to edit."
        )
        return

    if match["player1"].lower() == p1.lower():
        runs1, runs2 = r1, r2
    else:
        runs1, runs2 = r2, r1

    updated = db.set_result(match["id"], runs1, runs2)
    await update.message.reply_text("Result updated:\n" + format_match_line(updated))


@admin_only
async def creatematch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /creatematch <stage> <player1> <player2> [label]\n"
            "stages: super12, qualifier, semifinal, final, bronze"
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
        await update.message.reply_text("Usage: /addplayer <name> [group]")
        return
    name = context.args[0]
    grp = context.args[1] if len(context.args) > 1 else None
    ok = db.add_player(name, grp)
    if ok:
        await update.message.reply_text(f"Added player: {name}" + (f" (Group {grp})" if grp else ""))
    else:
        await update.message.reply_text(f"A player named '{name}' already exists.")


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
    app.add_handler(CommandHandler("groups", groups_cmd))
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
    app.add_handler(CommandHandler("addadmin", addadmin_cmd))
    app.add_handler(CommandHandler("removeadmin", removeadmin_cmd))
    app.add_handler(CommandHandler("listadmins", listadmins_cmd))

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
