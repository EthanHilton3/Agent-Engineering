import argparse
import json
import time

from openai import OpenAI

from usage import print_usage


# -------------------------
# ReAct System Prompt
# -------------------------

SYSTEM_PROMPT = """
You are an agent navigating a text maze using the ReAct pattern.

Each turn, return ONLY a JSON object with:
- decision: a short explanation of why the next action is appropriate
- action: one of ["look", "go east", "go west", "go north", "go south",
                  "go up", "go down", "take note", "take key",
                  "take treasure", "read note", "unlock", "exit", "none"]
- final_answer: only filled if action == "none"

Example:
{"decision":"I should inspect the room","action":"look","final_answer":""}
{"decision":"I have the treasure and am back at the start","action":"exit","final_answer":""}

When you have the treasure and have returned to the start, you may exit the maze.
Do not output anything outside JSON.
"""


# -------------------------
# Setup
# -------------------------
# Make sure OPENAI_API_KEY is set in your environment.
client = OpenAI()


# -------------------------
# Simple Text Maze Environment
# -------------------------

MAZE = {
    "start": {
        "desc": "You are at the start. There is a door to the east and a table.",
        "items": ["note"],
        "exits": {"east": "hallway"},
    },
    "hallway": {
        "desc": "A narrow hallway with a door to the north and stairs down.",
        "items": [],
        "exits": {"west": "start", "north": "treasure_room", "down": "cellar"},
    },
    "cellar": {
        "desc": "A dark cellar. There is a key on the floor.",
        "items": ["key"],
        "exits": {"up": "hallway"},
    },
    "treasure_room": {
        "desc": "A room glittering with treasure.",
        "items": ["treasure"],
        "exits": {"south": "hallway"},
    },
}


ALLOWED_ACTIONS = {
    "look",
    "go east",
    "go west",
    "go north",
    "go south",
    "go up",
    "go down",
    "take note",
    "take key",
    "take treasure",
    "read note",
    "unlock",
    "exit",
    "none",
}


def make_initial_state(max_steps):
    return {
        "location": "start",
        "inventory": [],
        "door_locked": True,
        "steps": 0,
        "max_steps": max_steps,
        "done": False,
        "success": False,
    }


def describe_location(state, location):
    """Describe a location without revealing inspectable contents."""
    if location == "hallway":
        door_status = "locked" if state["door_locked"] else "unlocked"
        return (
            f"A narrow hallway with a {door_status} door to the north "
            "and stairs down."
        )
    return MAZE[location]["desc"]


def inspect_location(state, location):
    """Return the result of the explicit look action."""
    loc_data = MAZE[location]
    items = ", ".join(loc_data["items"]) if loc_data["items"] else "nothing"
    exits = ", ".join(loc_data["exits"].keys())
    return (
        f"{describe_location(state, location)} "
        f"You see: {items}. Exits: {exits}."
    )


def environment_step(state, action):
    loc = state["location"]
    loc_data = MAZE[loc]
    action = action.lower().strip()
    observation = ""

    if action == "look":
        observation = inspect_location(state, loc)

    elif action.startswith("take "):
        item = action.replace("take ", "", 1)
        if item in loc_data["items"]:
            loc_data["items"].remove(item)
            state["inventory"].append(item)
            observation = f"You picked up the {item}."
        else:
            observation = f"There is no {item} here."

    elif action == "read note":
        if "note" in state["inventory"]:
            observation = (
                "The note says you must find a key to unlock the room "
                "that holds the treasure."
            )
        else:
            observation = "You must pick up the note first."

    elif action.startswith("go "):
        direction = action.replace("go ", "", 1)
        if direction in loc_data["exits"]:
            if loc == "hallway" and direction == "north" and state["door_locked"]:
                observation = "The north door is locked."
            else:
                state["location"] = loc_data["exits"][direction]
                observation = (
                    f"You moved {direction}. "
                    f"{describe_location(state, state['location'])}"
                )
        else:
            observation = "You can't go that way."

    elif action == "unlock":
        if state["location"] == "hallway" and "key" in state["inventory"]:
            state["door_locked"] = False
            observation = "You unlocked the north door."
        else:
            observation = "You can't unlock anything here."

    elif action == "exit":
        if state["location"] != "start":
            observation = "You must return to the start before exiting."
        elif "treasure" in state["inventory"]:
            state["done"] = True
            state["success"] = True
            observation = "You exit successfully with the treasure!"
        else:
            observation = "You can't exit yet; you do not have the treasure."

    else:
        observation = "Invalid action."

    state["steps"] += 1
    if state["steps"] >= state["max_steps"] and not state["done"]:
        state["done"] = True
        observation += " (Max steps reached.)"

    return observation, state


def extract_response_text(response):
    """Extract assistant text while ignoring non-message output items."""
    pieces = []
    for item in response.output:
        if item.type != "message":
            continue
        for content in item.content:
            if getattr(content, "type", None) == "output_text":
                pieces.append(content.text)
    return "".join(pieces).strip()


def parse_action(raw_text):
    """Parse and validate the model's JSON action."""
    if not raw_text:
        return None, "The model returned an empty response."

    candidates = [raw_text]
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw_text[start : end + 1])

    parsed = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue

    if not isinstance(parsed, dict):
        return None, "The response was not a JSON object."

    action = parsed.get("action")
    if not isinstance(action, str):
        return None, "The JSON object did not contain a string action."

    action = action.strip().lower()
    if action not in ALLOWED_ACTIONS:
        return None, f"Invalid action: {action!r}."

    parsed["action"] = action
    return parsed, None


def print_run_summary(state, action_history, usages, model, response_errors):
    print("\nRun summary")
    print("-----------")
    print("Result:", "SUCCESS" if state["success"] else "INCOMPLETE")
    print("Location:", state["location"])
    print("Inventory:", ", ".join(state["inventory"]) or "empty")
    print("Steps:", state["steps"])
    print("Response errors:", response_errors)
    print("Action trace:")
    if action_history:
        for index, item in enumerate(action_history, start=1):
            print(f"  {index}. {item['action']} -> {item['observation']}")
    else:
        print("  (no valid actions)")

    if usages:
        print_usage([(model, usage) for usage in usages])


# -------------------------
# ReAct Loop
# -------------------------

def run_text_maze(objective, model="gpt-5-mini", max_iters=20):
    state = make_initial_state(max_iters)
    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Objective: {objective}"},
        # The initial observation intentionally hides the table's contents.
        {"role": "system", "content": f"Observation: {describe_location(state, state['location'])}"},
    ]
    action_history = []
    usages = []
    response_errors = 0

    print("Agent instructions...")
    for message in history:
        print(f"\n{message['content']}")

    for step in range(max_iters):
        try:
            response = client.responses.create(
                model=model,
                input=history,
                max_output_tokens=400,
            )
        except Exception as error:
            response_errors += 1
            print(f"API request error: {error}")
            break

        if getattr(response, "usage", None):
            usages.append(response.usage)

        try:
            raw_text = extract_response_text(response)
        except Exception as error:
            raw_text = ""
            print(f"Response extraction error: {error}")

        parsed, parse_error = parse_action(raw_text)
        if parse_error:
            response_errors += 1
            print(f"Model response error: {parse_error}")
            history.append({
                "role": "system",
                "content": f"Observation: {parse_error} Return a valid JSON action.",
            })
            continue

        decision = parsed.get("decision", "")
        action = parsed["action"]
        final_answer = parsed.get("final_answer", "")

        print(f"\nStep {step + 1}")
        print("Decision:", decision)
        print("Action:", action)

        if action == "none" and state["done"]:
            print("\nFinal Answer:", final_answer)
            break

        observation, state = environment_step(state, action)
        print("Observation:", observation)
        action_history.append({"action": action, "observation": observation})

        history.append({"role": "assistant", "content": json.dumps(parsed)})
        history.append({"role": "system", "content": f"Observation: {observation}"})

        if state["done"]:
            print("\nSimulation ended.")
            break

        time.sleep(0.2)
    else:
        print("\n*** Simulation failed. Max iterations reached. ***")

    print_run_summary(
        state,
        action_history,
        usages,
        model,
        response_errors,
    )


# -------------------------
# Run Demo
# -------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Maze")
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--max_iters", type=int, default=20)
    args = parser.parse_args()
    run_text_maze(
        "Find the treasure and exit.",
        model=args.model,
        max_iters=args.max_iters,
    )
