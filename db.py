"""
SQLite database layer for the Hand Cricket scheduling bot.

Everything the bot needs (players, matches, admins) lives in one SQLite
file (handcricket.db by default). On first run the database is created
and seeded with the 27 players and the fixed group-stage schedule from
schedule_data.py. Super 12 and playoff matches are added later by an
admin using bot commands, since they depend on group-stage results.
"""

import os
import sqlite3
from contextlib import contextmanager

from schedule_data import GROUPS, GROUP_FIXTURES

DB_PATH = os.environ.get("DB_PATH", "handcricket.db")

STAGE_LABELS = {
    "group": "Group Stage",
    "super12": "Super 12",
    "qualifier": "Qualifier",
    "semifinal": "Semi-Final",
    "final": "Final",
    "bronze": "Bronze Medal Match",
}


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                grp TEXT
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage TEXT NOT NULL,
                grp TEXT,
                match_day TEXT,
                label TEXT,
                player1 TEXT NOT NULL,
                player2 TEXT NOT NULL,
                player1_runs INTEGER,
                player2_runs INTEGER,
                status TEXT NOT NULL DEFAULT 'scheduled',
                winner TEXT
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                name TEXT
            );
            """
        )

    _seed_if_empty()


def _seed_if_empty():
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) c FROM players").fetchone()["c"]
        if count > 0:
            return

        for grp, names in GROUPS.items():
            for name in names:
                conn.execute(
                    "INSERT OR IGNORE INTO players (name, grp) VALUES (?, ?)",
                    (name, grp),
                )

        for grp, fixtures in GROUP_FIXTURES.items():
            for day, p1, p2 in fixtures:
                conn.execute(
                    """INSERT INTO matches (stage, grp, match_day, player1, player2, status)
                       VALUES ('group', ?, ?, ?, ?, 'scheduled')""",
                    (grp, day, p1, p2),
                )


def ensure_admin(user_id: int, name: str = ""):
    """Make sure a given telegram user id is registered as admin."""
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO admins (user_id, name) VALUES (?, ?)",
            (user_id, name),
        )


def is_admin(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM admins WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row is not None


def add_admin(user_id: int, name: str = "") -> bool:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM admins WHERE user_id = ?", (user_id,)
        ).fetchone()
        if existing:
            return False
        conn.execute(
            "INSERT INTO admins (user_id, name) VALUES (?, ?)", (user_id, name)
        )
        return True


def remove_admin(user_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        return cur.rowcount > 0


def list_admins():
    with get_conn() as conn:
        return conn.execute("SELECT user_id, name FROM admins").fetchall()


def find_player(name: str):
    """Case-insensitive exact lookup of a player's canonical name."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        return row


def add_player(name: str, grp: str = None) -> bool:
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO players (name, grp) VALUES (?, ?)", (name, grp)
            )
            return True
        except sqlite3.IntegrityError:
            return False


def players_in_group(grp: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM players WHERE LOWER(grp) = LOWER(?) ORDER BY name",
            (grp,),
        ).fetchall()


def all_groups():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT grp FROM players WHERE grp IS NOT NULL ORDER BY grp"
        ).fetchall()
        return [r["grp"] for r in rows]


def create_match(stage: str, player1: str, player2: str, grp: str = None,
                  match_day: str = None, label: str = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO matches (stage, grp, match_day, label, player1, player2, status)
               VALUES (?, ?, ?, ?, ?, ?, 'scheduled')""",
            (stage, grp, match_day, label, player1, player2),
        )
        return cur.lastrowid


def find_pending_match(player1: str, player2: str):
    """Find the most recent scheduled (not yet completed) match between two players."""
    with get_conn() as conn:
        return conn.execute(
            """SELECT * FROM matches
               WHERE status = 'scheduled'
               AND ((LOWER(player1)=LOWER(?) AND LOWER(player2)=LOWER(?))
                 OR (LOWER(player1)=LOWER(?) AND LOWER(player2)=LOWER(?)))
               ORDER BY id DESC LIMIT 1""",
            (player1, player2, player2, player1),
        ).fetchone()


def find_completed_match(player1: str, player2: str):
    with get_conn() as conn:
        return conn.execute(
            """SELECT * FROM matches
               WHERE status = 'completed'
               AND ((LOWER(player1)=LOWER(?) AND LOWER(player2)=LOWER(?))
                 OR (LOWER(player1)=LOWER(?) AND LOWER(player2)=LOWER(?)))
               ORDER BY id DESC LIMIT 1""",
            (player1, player2, player2, player1),
        ).fetchone()


def get_match(match_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()


def set_result(match_id: int, runs1: int, runs2: int):
    if runs1 > runs2:
        winner = None  # filled below using stored player names
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        if row is None:
            return None
        if runs1 > runs2:
            winner = row["player1"]
        elif runs2 > runs1:
            winner = row["player2"]
        else:
            winner = "DRAW"
        conn.execute(
            """UPDATE matches SET player1_runs=?, player2_runs=?, status='completed', winner=?
               WHERE id=?""",
            (runs1, runs2, winner, match_id),
        )
        return conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()


def matches_for_group(grp: str, day: str = None):
    with get_conn() as conn:
        if day:
            return conn.execute(
                """SELECT * FROM matches WHERE stage='group' AND LOWER(grp)=LOWER(?)
                   AND match_day=? ORDER BY id""",
                (grp, day),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM matches WHERE stage='group' AND LOWER(grp)=LOWER(?) ORDER BY id",
            (grp,),
        ).fetchall()


def matches_for_stage(stage: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM matches WHERE LOWER(stage)=LOWER(?) ORDER BY id", (stage,)
        ).fetchall()


def matches_for_player(name: str):
    with get_conn() as conn:
        return conn.execute(
            """SELECT * FROM matches
               WHERE LOWER(player1)=LOWER(?) OR LOWER(player2)=LOWER(?)
               ORDER BY id""",
            (name, name),
        ).fetchall()


def pending_matches(grp: str = None):
    with get_conn() as conn:
        if grp:
            return conn.execute(
                "SELECT * FROM matches WHERE status='scheduled' AND LOWER(grp)=LOWER(?) ORDER BY id",
                (grp,),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM matches WHERE status='scheduled' ORDER BY id"
        ).fetchall()


def standings_for(stage: str, grp: str = None):
    """
    Compute a points table for a given stage (e.g. 'group', 'super12'),
    optionally restricted to a group letter. Returns a list of dicts sorted
    by points desc, then run-margin desc (provisional tiebreak; the real
    tiebreak rule can be applied manually once it's confirmed).
    """
    with get_conn() as conn:
        if grp:
            rows = conn.execute(
                "SELECT * FROM matches WHERE LOWER(stage)=LOWER(?) AND LOWER(grp)=LOWER(?) AND status='completed'",
                (stage, grp),
            ).fetchall()
            players = players_in_group(grp)
            names = [p["name"] for p in players]
        else:
            rows = conn.execute(
                "SELECT * FROM matches WHERE LOWER(stage)=LOWER(?) AND status='completed'",
                (stage,),
            ).fetchall()
            names = sorted({r["player1"] for r in rows} | {r["player2"] for r in rows})

        table = {n: {"player": n, "P": 0, "W": 0, "L": 0, "D": 0,
                      "Pts": 0, "RS": 0, "RC": 0} for n in names}

        for r in rows:
            p1, p2 = r["player1"], r["player2"]
            r1, r2 = r["player1_runs"], r["player2_runs"]
            for p in (p1, p2):
                if p not in table:
                    table[p] = {"player": p, "P": 0, "W": 0, "L": 0, "D": 0, "Pts": 0, "RS": 0, "RC": 0}
            table[p1]["P"] += 1
            table[p2]["P"] += 1
            table[p1]["RS"] += r1
            table[p1]["RC"] += r2
            table[p2]["RS"] += r2
            table[p2]["RC"] += r1
            if r["winner"] == "DRAW":
                table[p1]["D"] += 1
                table[p2]["D"] += 1
                table[p1]["Pts"] += 1
                table[p2]["Pts"] += 1
            elif r["winner"] == p1:
                table[p1]["W"] += 1
                table[p2]["L"] += 1
                table[p1]["Pts"] += 2
            elif r["winner"] == p2:
                table[p2]["W"] += 1
                table[p1]["L"] += 1
                table[p2]["Pts"] += 2

        result = list(table.values())
        for row in result:
            row["RD"] = row["RS"] - row["RC"]
        result.sort(key=lambda x: (-x["Pts"], -x["RD"]))
        return result
