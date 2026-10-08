import json
import random

from tools import ToolBox

toolbox = ToolBox()

@toolbox.tool
def roll_dice(num_dice: int, sides: int) -> str:
    """Roll dice and return each roll plus the total. Use this for **all** dice rolls; never make up roll results."""
    if num_dice < 1 or sides < 2:
        raise ValueError("num_dice must be >= 1 and sides must be >= 2")
    rolls = [random.randint(1, sides) for _ in range(num_dice)]
    return json.dumps({"rolls": rolls, "total": sum(rolls)})


@toolbox.tool
def flip_coins(num_flips: int) -> str:
    """Flip coins and return the results. Use this for **all** coin flip requests; never make up flip results."""
    if num_flips < 1:
        raise ValueError("num_flips must be >= 1")
    flips = [random.choice(["heads", "tails"]) for _ in range(num_flips)]
    return json.dumps({"flips": flips})


@toolbox.tool
def random_integer(low: int, high: int) -> int:
    """Return a random integer in [low, high], inclusive. Use this for **all** random number integer requests; never make up random numbers."""
    if low > high:
        raise ValueError("low must be <= high")
    return random.randint(low, high)
