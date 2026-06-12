"""
Character aliases for query expansion.
When a query matches a character name, these terms are also searched
to surface related lore not explicitly using the character's name.
"""

ALIASES: dict[str, list[str]] = {
    "Melina": ["maiden", "kindling", "accord", "Rold", "blade of Miquella"],
    "Ranni": ["Renna", "Lunar Princess", "witch", "Dark Moon", "two fingers"],
    "Fia": ["Deathbed", "deathbed companion", "Prince of Death", "Godwyn"],
    "Godrick": ["grafted", "grafting", "Stormveil"],
    "Rennala": ["Full Moon", "Carian", "amber egg"],
    "Marika": ["Erdtree", "Elden Ring", "Elden Lord", "Greater Will", "shattering"],
    "Radahn": ["Starscourge", "Caelid", "gravity", "Mohg"],
    "Morgott": ["Omen King", "Margit", "Fell Omen", "Leyndell"],
    "Malenia": ["Blade of Miquella", "Rot", "Scarlet Rot", "Elphael"],
    "Miquella": ["Haligtree", "kindly", "unalloyed gold", "Malenia"],
    "Patches": ["scoundrel", "prostrate", "merchant"],
    "Blaidd": ["Half-Wolf", "shadow", "Ranni"],
    "Gurranq": ["Beast Clergyman", "Deathroot", "Maliketh"],
    "Maliketh": ["Black Blade", "Destined Death", "Rune of Death"],
    "Godfrey": ["Hoarah Loux", "Elden Lord", "first Elden Lord", "Serosh"],
    "Hewg": ["Smithing Master", "prisoner", "forge"],
    "Boc": ["seamster", "demi-human", "needle"],
    "Alexander": ["Warrior Jar", "jar", "champion"],
    "Tanith": ["Volcano Manor", "assassination", "Rykard"],
    "Rykard": ["Volcano Manor", "serpent", "blasphemy"],
    "Varre": ["White Mask", "Bloody Finger", "Mohg", "Rose Church"],
    "Nepheli": ["warrior", "Godrick", "soldier of Godrick"],
    "Gideon": ["All-Knowing", "Roundtable", "Erdtree"],
}

# Normalize keys to lowercase for lookup
ALIASES_LOWER: dict[str, tuple[str, list[str]]] = {
    k.lower(): (k, v) for k, v in ALIASES.items()
}


def get_aliases(query: str) -> tuple[str, list[str]] | None:
    """Return (canonical_name, [aliases]) if query matches a character, else None."""
    return ALIASES_LOWER.get(query.strip().lower())
