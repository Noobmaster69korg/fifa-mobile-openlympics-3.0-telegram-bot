"""
Static tournament data for the Openlympics 3.0 FIFA Mobile tournament.

Format: single round-robin, every player plays every other player exactly
once. With an odd number of players (11), one player gets a "bye" each
round (no match that round) so it works out evenly.

The schedule is generated with the standard round-robin "circle method"
rather than typed out by hand, so it's guaranteed correct and fair.
"""

PLAYERS = [
    "Navoneel", "Pranava", "Prasham", "Ayush", "Pranav",
    "Rounak", "MS", "Noobmaster", "OmmS", "DominantR", "Akhil",
]


def generate_round_robin(players):
    """
    Standard circle-method round robin scheduler.
    Returns a list of rounds; each round is a list of (player1, player2)
    tuples. Byes are dropped from the output (they just mean one fewer
    match that round for whoever sits out).
    """
    players = list(players)
    bye = None
    if len(players) % 2 == 1:
        players.append(bye)  # pad to even with a placeholder "bye" slot

    n = len(players)
    num_rounds = n - 1
    rounds = []

    arrangement = players[:]
    for _ in range(num_rounds):
        pairings = []
        for i in range(n // 2):
            p1 = arrangement[i]
            p2 = arrangement[n - 1 - i]
            if p1 is not None and p2 is not None:
                pairings.append((p1, p2))
        rounds.append(pairings)
        # rotate everyone except the first fixed player
        arrangement = [arrangement[0]] + [arrangement[-1]] + arrangement[1:-1]

    return rounds


# FIXTURES: list of (round_label, player1, player2), generated once here so
# it's the same every time the app starts (deterministic seeding).
_rounds = generate_round_robin(PLAYERS)
FIXTURES = [
    (f"Round {i}", p1, p2)
    for i, round_matches in enumerate(_rounds, start=1)
    for (p1, p2) in round_matches
]
