"""
Static tournament data for Openlympics 3.0 - Hand Cricket.

GROUPS maps group letter -> list of player names (canonical spelling/casing).
GROUP_FIXTURES maps group letter -> list of (day, player1, player2) tuples,
exactly as published in the official schedule.

This file is only used once, to seed the database on first run. After that,
the database is the source of truth (so admins can edit/add matches for
Super 12 and the playoffs without touching this file).
"""

GROUPS = {
    "A": ["Vibhakar", "PKP", "Pranava", "Parth", "Sahoo", "Mohit", "Rounak", "MS", "Bojo"],
    "B": ["Navoneel", "Shivam", "Prasham", "Arko", "Chitransh", "Jai", "Ashish", "Molecule", "Karthick"],
    "C": ["Shamanth", "Ayush", "Pranav", "Aditya", "DominantR", "Rijul", "Noobmaster", "OmmS", "Akhil"],
}

# (day, player1, player2)
GROUP_FIXTURES = {
    "A": [
        ("14/09", "Vibhakar", "PKP"),
        ("14/09", "PKP", "Pranava"),
        ("14/09", "Pranava", "Parth"),
        ("14/09", "Parth", "Sahoo"),
        ("14/09", "Sahoo", "Mohit"),
        ("14/09", "Mohit", "Rounak"),
        ("14/09", "Rounak", "MS"),
        ("14/09", "MS", "Bojo"),
        ("14/09", "Bojo", "Vibhakar"),

        ("15/09", "Vibhakar", "Pranava"),
        ("15/09", "PKP", "Parth"),
        ("15/09", "Pranava", "Sahoo"),
        ("15/09", "Parth", "Mohit"),
        ("15/09", "Sahoo", "Rounak"),
        ("15/09", "Mohit", "MS"),
        ("15/09", "Rounak", "Bojo"),
        ("15/09", "MS", "Vibhakar"),
        ("15/09", "Bojo", "PKP"),

        ("16/09", "Vibhakar", "Parth"),
        ("16/09", "Rounak", "Vibhakar"),
        ("16/09", "PKP", "Sahoo"),
        ("16/09", "Sahoo", "MS"),
        ("16/09", "MS", "PKP"),
        ("16/09", "Pranava", "Mohit"),
        ("16/09", "Mohit", "Bojo"),
        ("16/09", "Bojo", "Pranava"),
        ("16/09", "Parth", "Rounak"),

        ("17/09", "Vibhakar", "Sahoo"),
        ("17/09", "Sahoo", "Bojo"),
        ("17/09", "Bojo", "Parth"),
        ("17/09", "Parth", "MS"),
        ("17/09", "MS", "Pranava"),
        ("17/09", "Pranava", "Rounak"),
        ("17/09", "Rounak", "PKP"),
        ("17/09", "PKP", "Mohit"),
        ("17/09", "Mohit", "Vibhakar"),
    ],
    "B": [
        ("14/09", "Navoneel", "Shivam"),
        ("14/09", "Shivam", "Prasham"),
        ("14/09", "Prasham", "Arko"),
        ("14/09", "Arko", "Chitransh"),
        ("14/09", "Chitransh", "Jai"),
        ("14/09", "Jai", "Ashish"),
        ("14/09", "Ashish", "Molecule"),
        ("14/09", "Molecule", "Karthick"),
        ("14/09", "Karthick", "Navoneel"),

        ("15/09", "Navoneel", "Prasham"),
        ("15/09", "Shivam", "Arko"),
        ("15/09", "Prasham", "Chitransh"),
        ("15/09", "Arko", "Jai"),
        ("15/09", "Chitransh", "Ashish"),
        ("15/09", "Jai", "Molecule"),
        ("15/09", "Ashish", "Karthick"),
        ("15/09", "Molecule", "Navoneel"),
        ("15/09", "Karthick", "Shivam"),

        ("16/09", "Navoneel", "Arko"),
        ("16/09", "Arko", "Ashish"),
        ("16/09", "Ashish", "Navoneel"),
        ("16/09", "Shivam", "Chitransh"),
        ("16/09", "Chitransh", "Molecule"),
        ("16/09", "Molecule", "Shivam"),
        ("16/09", "Prasham", "Jai"),
        ("16/09", "Jai", "Karthick"),
        ("16/09", "Karthick", "Prasham"),

        ("17/09", "Navoneel", "Chitransh"),
        ("17/09", "Chitransh", "Karthick"),
        ("17/09", "Karthick", "Arko"),
        ("17/09", "Arko", "Molecule"),
        ("17/09", "Molecule", "Prasham"),
        ("17/09", "Prasham", "Ashish"),
        ("17/09", "Ashish", "Shivam"),
        ("17/09", "Shivam", "Jai"),
        ("17/09", "Jai", "Navoneel"),
    ],
    "C": [
        ("14/09", "Shamanth", "Ayush"),
        ("14/09", "Ayush", "Pranav"),
        ("14/09", "Pranav", "Aditya"),
        ("14/09", "Aditya", "DominantR"),
        ("14/09", "DominantR", "Rijul"),
        ("14/09", "Rijul", "Noobmaster"),
        ("14/09", "Noobmaster", "OmmS"),
        ("14/09", "OmmS", "Akhil"),
        ("14/09", "Akhil", "Shamanth"),

        ("15/09", "Shamanth", "Pranav"),
        ("15/09", "Ayush", "Aditya"),
        ("15/09", "Pranav", "DominantR"),
        ("15/09", "Aditya", "Rijul"),
        ("15/09", "DominantR", "Noobmaster"),
        ("15/09", "Rijul", "OmmS"),
        ("15/09", "Noobmaster", "Akhil"),
        ("15/09", "OmmS", "Shamanth"),
        ("15/09", "Akhil", "Ayush"),

        ("16/09", "Shamanth", "Aditya"),
        ("16/09", "Aditya", "Noobmaster"),
        ("16/09", "Noobmaster", "Shamanth"),
        ("16/09", "Ayush", "DominantR"),
        ("16/09", "DominantR", "OmmS"),
        ("16/09", "OmmS", "Ayush"),
        ("16/09", "Pranav", "Rijul"),
        ("16/09", "Rijul", "Akhil"),
        ("16/09", "Akhil", "Pranav"),

        ("17/09", "Shamanth", "DominantR"),
        ("17/09", "DominantR", "Akhil"),
        ("17/09", "Akhil", "Aditya"),
        ("17/09", "Aditya", "OmmS"),
        ("17/09", "OmmS", "Pranav"),
        ("17/09", "Pranav", "Noobmaster"),
        ("17/09", "Noobmaster", "Ayush"),
        ("17/09", "Ayush", "Rijul"),
        ("17/09", "Rijul", "Shamanth"),
    ],
}
