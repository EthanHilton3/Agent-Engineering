"""Fixed game content for Talk Past the Guard.

Jev can't write text, so every scenario and every canned guard line lives here
as plain data. Both judges see exactly the same scenario facts.

guard_knows is what the judge sees. player_knows is shown only to the player, so
they have something to work with. It is never sent to the judge, because the
guard can't read the player's mind.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    guard: str
    setting: str
    goal: str
    guard_knows: str
    player_knows: str
    soft_spot: str  # the exception this guard will make; a winnable path besides lying
    opening_line: str
    hints: tuple[str, ...]  # guard lines for a "suspicious" verdict that nudge the player


SCENARIOS: dict[str, Scenario] = {
    "gate": Scenario(
        key="gate",
        title="The Night Gate of Highmoor",
        guard="Gate Captain Hroldan",
        setting=(
            "It is past midnight. The gates of Highmoor are barred, torches gutter "
            "in the wind, and a guard in a steel helm blocks the small postern door."
        ),
        goal="Get inside the city tonight.",
        guard_knows=(
            "- The gates closed at sundown because of bandit raids on the north road.\n"
            "- After dark, only city residents, or travelers carrying a writ or letters "
            "for the Jarl's steward, may enter.\n"
            "- The guard does not recognize the player.\n"
            "- A courier from Ashford is expected tonight with letters for the steward."
        ),
        player_knows=(
            "- At the last inn, a drunk courier complained he'd never reach Highmoor "
            "tonight with 'the steward's precious letters from Ashford.'\n"
            "- You came down the north road and saw a fresh bandit ambush: a burned "
            "wagon and tracks heading toward the old mill.\n"
            "- You carry a leather satchel, a bedroll, and a little coin."
        ),
        soft_spot=(
            "Hroldan's brother was killed by north-road bandits. He will let in anyone "
            "with credible, specific news about the bandits that the steward needs to hear tonight."
        ),
        opening_line="Halt. Gates are shut 'til dawn. State your business, or move along.",
        hints=(
            "Gates are for residents and the steward's business after dark. Which are you?",
            "Unless you've got letters for the steward, or news he needs, you're sleeping outside the walls.",
        ),
    ),
    "archive": Scenario(
        key="archive",
        title="The Sealed Archive",
        guard="Sentinel Maren",
        setting=(
            "A spiral stair in the court mage's tower ends at an iron-bound door. "
            "A sentinel with a halberd stands in front of it."
        ),
        goal="Get into the archive to read a forbidden tome.",
        guard_knows=(
            "- Court Mage Velothi is away at the capital for a week.\n"
            "- Only Velothi's apprentices, or someone carrying a letter under her "
            "personal seal, may enter the archive.\n"
            "- Velothi's apprentices always wear a blue sash. The player is not "
            "wearing one.\n"
            "- A fire in the lower library last week has made the guards jumpy."
        ),
        player_knows=(
            "- Everyone in the tower knows Velothi left for the capital a few days ago.\n"
            "- Her apprentices wear blue sashes. You don't have one.\n"
            "- Servants are still gossiping about last week's fire in the lower library.\n"
            "- You have a scrap of parchment in Velothi's handwriting: 'See that the "
            "archive wards are looked to while I am away.' It has no seal.\n"
            "- The archive's wards are protective enchantments on its door and shelves "
            "that keep the books safe from fire.\n"
            "- Sentinel Maren looked shaken when the fire was mentioned at supper."
        ),
        soft_spot=(
            "Maren knows Velothi's handwriting, and fears the archive's fire wards were "
            "damaged in last week's fire. She will allow a short visit to someone with a "
            "believable reason to check or repair the wards, especially if they carry "
            "Velothi's handwriting, even without her seal."
        ),
        opening_line="This archive is sealed by order of the Court Mage. Who sent you?",
        hints=(
            "No sash, no seal. Velothi's orders are clear... unless there's something about this door I should know.",
            "After that fire, I worry about what's behind this door. But I need a reason, not a story.",
        ),
    ),
    "amulet": Scenario(
        key="amulet",
        title="The Market Accusation",
        guard="Watchman Bryn",
        setting=(
            "In the crowded market square, a watchman steps into your path and "
            "stares at your chest."
        ),
        goal="Walk away without being arrested.",
        guard_knows=(
            "- A silver amulet with a wolf's-head clasp was reported stolen from "
            "Elda's jewelry stall this morning.\n"
            "- The player is wearing a silver amulet with a wolf's-head clasp.\n"
            "- Elda described the thief as someone in a hooded cloak.\n"
            "- The player is wearing a hooded cloak."
        ),
        player_knows=(
            "- You bought this amulet for ten gold from a hooded stranger behind the "
            "tavern this morning. It seemed too cheap.\n"
            "- You're wearing your hood because of the rain.\n"
            "- Elda's jewelry stall is just across the square."
        ),
        soft_spot=(
            "Bryn cares more about catching the real thief than about making an easy "
            "arrest. He will let go anyone who credibly helps him find the thief."
        ),
        opening_line="That's a fine amulet. Wolf's head, is it? Where'd you come by that?",
        hints=(
            "An amulet just like that went missing from Elda's stall this morning. Explain yourself.",
            "Hooded cloak, wolf's-head amulet... you can see how this looks. Help me find who really did it.",
        ),
    ),
    "checkpoint": Scenario(
        key="checkpoint",
        title="The Border Checkpoint",
        guard="Sergeant Coll",
        setting=(
            "At the river bridge, a sergeant waves your apple cart to a stop and "
            "walks slowly around it."
        ),
        goal="Get your cart across without the crates being searched.",
        guard_knows=(
            "- Dreamleaf is contraband, and smugglers often hide it in produce.\n"
            "- The player showed a valid merchant's trade seal.\n"
            "- The cart carries crates of apples.\n"
            "- One crate gives off a strong, sickly-sweet smell, like dreamleaf."
        ),
        player_knows=(
            "- A bundle of dreamleaf is hidden under the apples in your third crate.\n"
            "- Dreamleaf smells a lot like spiced honey.\n"
            "- The Harvest Fair in Dunmere, across the river, starts tomorrow, and "
            "honeyed apples sell well there.\n"
            "- A long line of carts is waiting behind you."
        ),
        soft_spot=(
            "Coll is overworked and the line of carts is long. He will wave through a "
            "merchant with a confident, believable explanation for the smell who offers "
            "a quick look at the top of the crate."
        ),
        opening_line="Trade seal checks out. But what's that smell coming off your third crate?",
        hints=(
            "Smells a lot like dreamleaf to me. Convince me it isn't.",
            "Seal's fine. It's the crate I'm worried about, and I haven't got all day.",
        ),
    ),
}


# Jev can't write dialogue, so the Jev version picks from these instead.
# "suspicious" uses the scenario's hints.
GUARD_LINES: dict[str, list[str]] = {
    "let_pass": [
        "Fine. Go on through, and keep out of trouble.",
        "Hmph. Your story holds. Move along.",
        "Alright. But I'll remember your face.",
    ],
    "arrest": [
        "Stop right there, criminal scum! You're coming with me.",
        "That's it. Hands where I can see them.",
    ],
}
