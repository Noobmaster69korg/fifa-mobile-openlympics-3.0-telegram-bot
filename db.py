"""
SQLite database layer for the FIFA Mobile tournament bot.

Everything (players, matches, admins) lives in one SQLite file
(fifa.db by default). On first run the database is created and seeded
with the 11 players and the auto-generated round-robin schedule from
schedule_data.py. Knockout-stage matches (quarter-finals, semis, final,
etc.) are added later by an admin using bot commands, since those
pairings depend on league results.
"""

import os
import sqlite3
from contextlib import contextmanager

from schedule_data import PLAYERS, FIXTURES

DB_PATH = os.environ.get("DB_PATH", "fifa.db")

LEAGUE_STAGE = "league"

STAGE_LABELS = {
    "league": "League Table",
    "round16": "Round of 16",
    "quarterfinal": "Quarter-Final",
    "semifinal": "Semi-Final",
    "final": "Final",
    "third_place": "Third Place Play-off",
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
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage TEXT NOT NULL,
                round_label TEXT,
                label TEXT,
                player1 TEXT NOT NULL,
                player2 TEXT NOT NULL,
                player1_goals INTEGER,
                player2_goals INTEGER,
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

        for name in PLAYERS:
            conn.execute("INSERT OR IGNORE INTO players (name) VALUES (?)", (name,))

        for round_label, p1, p2 in FIXTURES:
            conn.execute(
                """INSERT INTO matches (stage, round_label, player1, player2, status)
                   VALUES (?, ?, ?, ?, 'scheduled')""",
                (LEAGUE_STAGE, round_label, p1, p2),
            )


def ensure_admin(user_id: int, name: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO admins (user_id, name) VALUES (?, ?)",
            (user_id, name),
        )


def is_admin(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone()
        return row is not None


def add_admin(user_id: int, name: str = "") -> bool:
    with get_conn() as conn:
        existing = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone()
        if existing:
            return False
        conn.execute("INSERT INTO admins (user_id, name) VALUES (?, ?)", (user_id, name))
        return True


def remove_admin(user_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        return cur.rowcount > 0


def list_admins():
    with get_conn() as conn:
        return conn.execute("SELECT user_id, name FROM admins").fetchall()


def find_player(name: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM players WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()


def add_player(name: str) -> bool:
    with get_conn() as conn:
        try:
            conn.execute("INSERT INTO players (name) VALUES (?)", (name,))
            return True
        except sqlite3.IntegrityError:
            return False


def all_players():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM players ORDER BY name").fetchall()


def create_match(stage: str, player1: str, player2: str, round_label: str = None,
                  label: str = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO matches (stage, round_label, label, player1, player2, status)
               VALUES (?, ?, ?, ?, ?, 'scheduled')""",
            (stage, round_label, label, player1, player2),
        )
        return cur.lastrowid


def find_pending_match(player1: str, player2: str):
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


def delete_match(match_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))
        return cur.rowcount > 0


def remove_player(name: str):
    """Deletes a player and every match (any stage, played or not) they're
    part of. Returns {'name': canonical_name, 'matches_deleted': n} or None
    if no such player exists."""
    with get_conn() as conn:
        player = conn.execute(
            "SELECT * FROM players WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        if not player:
            return None
        canonical = player["name"]
        cur = conn.execute(
            "DELETE FROM matches WHERE LOWER(player1)=LOWER(?) OR LOWER(player2)=LOWER(?)",
            (canonical, canonical),
        )
        matches_deleted = cur.rowcount
        conn.execute("DELETE FROM players WHERE id = ?", (player["id"],))
        return {"name": canonical, "matches_deleted": matches_deleted}


def set_result(match_id: int, goals1: int, goals2: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        if row is None:
            return None
        if goals1 > goals2:
            winner = row["player1"]
        elif goals2 > goals1:
            winner = row["player2"]
        else:
            winner = "DRAW"
        conn.execute(
            """UPDATE matches SET player1_goals=?, player2_goals=?, status='completed', winner=?
               WHERE id=?""",
            (goals1, goals2, winner, match_id),
        )
        return conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()


def matches_for_round(round_label: str = None):
    with get_conn() as conn:
        if round_label:
            return conn.execute(
                "SELECT * FROM matches WHERE stage=? AND round_label=? ORDER BY id",
                (LEAGUE_STAGE, round_label),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM matches WHERE stage=? ORDER BY id", (LEAGUE_STAGE,)
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


def pending_matches(round_label: str = None, stage: str = None):
    with get_conn() as conn:
        query = "SELECT * FROM matches WHERE status='scheduled'"
        params = []
        if stage:
            query += " AND LOWER(stage)=LOWER(?)"
            params.append(stage)
        if round_label:
            query += " AND round_label=?"
            params.append(round_label)
        query += " ORDER BY id"
        return conn.execute(query, params).fetchall()


def standings_for(stage: str):
    """
    Points table for a given stage (usually 'league'). Sorted by
    points desc, then goal difference desc, then goals scored desc.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM matches WHERE LOWER(stage)=LOWER(?) AND status='completed'",
            (stage,),
        ).fetchall()

    if stage.lower() == LEAGUE_STAGE:
        names = [p["name"] for p in all_players()]
    else:
        names = sorted({r["player1"] for r in rows} | {r["player2"] for r in rows})

    table = {n: {"player": n, "P": 0, "W": 0, "L": 0, "D": 0, "Pts": 0, "GS": 0, "GC": 0}
             for n in names}

    for r in rows:
        p1, p2 = r["player1"], r["player2"]
        g1, g2 = r["player1_goals"], r["player2_goals"]
        for p in (p1, p2):
            if p not in table:
                table[p] = {"player": p, "P": 0, "W": 0, "L": 0, "D": 0, "Pts": 0, "GS": 0, "GC": 0}
        table[p1]["P"] += 1
        table[p2]["P"] += 1
        table[p1]["GS"] += g1
        table[p1]["GC"] += g2
        table[p2]["GS"] += g2
        table[p2]["GC"] += g1
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
        row["GD"] = row["GS"] - row["GC"]
    result.sort(key=lambda x: (-x["Pts"], -x["GD"], -x["GS"]))
    return result
