# Lecture 1B Homework Report

In 1A, `basic_completion_app.py` just printed `response.output_text` as free text, with no guarantee about its shape. That caused a real problem when all of my prompts asked the models to write their outputs to a new file, it couldn't actually do that, and just wrote out a description of writing a file instead of writing one.

For 1B I rebuilt the app around structured output. Instead of free text, I pass a JSON Schema into the API call:

```python
text={
    'format': {
        'type': 'json_schema',
        'name': schema_name,
        'schema': schema,
        'strict': True,
    }
}
```

With `strict: True`, the API guarantees the response matches the schema, so `json.loads(response.output_text)` always works. My code then decides what to do with the result and allows for writing files.

### Re-running the BOM and Connect 4 prompts

Both prompts now return structured fields (`filename`, `content`, `file_type`, plus problem-specific fields like `author` or `single_player_mode`) instead of free text, and my code writes the file:

```python
def write_output(result, model, usage, reasoning):
    file_type = result.get('file_type')
    filename = result.get('filename')
    writer = WRITERS.get(file_type)
    if not (filename and writer):
        return None
    ...
    path.write_text(text, encoding='utf-8')
    return path
```

At least in one observable way, this is better than my 1A results. The file actually gets written every time, on every model, regardless of reasoning level. Because of the structured output and the supporting code in my agent, the returned JSON responses are parsed and then written into newly created files every time.

### Devotional summarizer

I then used my `structured_output.py` agent for the devo experiment. This agent (`devotional_instructions.md` + `schemas/devotional_summary.schema.json` + `devotional.txt`) reads the devo I give it (I used "In Appreciation of Friction: Embracing the Awkward" by C. Shane Reese) and pulls out three things:

1. `key_takeaways`: the main points a listener should walk away with.
2. `speaker_emphasis`: what the speaker personally kept returning to, which is different from the general takeaways.
3. A custom criterion I picked, `outside quotations and citations`: every scripture, talk, article, or named person the speaker quoted. This address had 24 footnotes plus a handful of unattributed quotes, so this field ended up being the most interesting one to look at.

For formatting, my first version had the model write its own Markdown summary as an extra field alongside the structured data. That meant it was generating the same information twice. I removed that field and now build the `.md` file directly from the structured fields in code instead.

## Model and Reasoning Comparisons

All runs are on the same transcript (about 4,600 input tokens), same schema.

**`gpt-5.6-luna` at different reasoning levels:** at `low`, the run used 50 reasoning tokens and cost $0.0015. At `medium`, 281 reasoning tokens and $0.0028. At `high`, 516 reasoning tokens and $0.0032. Cost tracks reasoning tokens here, not quality. Going from `low` to `high` is a small cost bump for a slightly more thorough summary. `max` is a different story: reasoning tokens jumped to 19,421 and the cost went up to $0.0261, about 17 times the `high` run, without the summary actually getting noticeably better. It mostly just took longer to say the same thing.

**Different models, same prompt, medium reasoning where applicable:** `gpt-5.6-luna` cost $0.0028. `gpt-4.1` (not a reasoning model, so no reasoning tokens) cost $0.0162. `gpt-5.2` cost $0.0268. `gpt-5.4` cost $0.0602 with 1,552 reasoning tokens. `gpt-5` cost $0.0764 with 5,696 reasoning tokens. `luna` was the cheapest by a wide margin, and its summaries covered the same takeaways and citations as the pricier models. `gpt-5` in particular spent a lot of reasoning tokens without producing a meaningfully different result.

**`luna` vs `sol`, both at `max` reasoning:** `luna` used 19,421 reasoning tokens and cost $0.0261. `sol` used 15,538 reasoning tokens and cost $0.3640, about 14 times more than `luna` for the same reasoning setting. Its summary was a little more careful in places. It noted when a citation's source wasn't named in the transcript, and caught a couple of quotes `luna` missed. But the difference was small, not something that obviously justifies a 14 times cost difference for this kind of task.

One other difference showed up in the filenames themselves, not just cost or quality. My prompt told the model to prefix the output filename with `DEVO_` plus the date, but that instruction wasn't followed consistently across models and reasoning levels. Some runs matched it exactly (`DEVO_2026...`), one dropped the prefix entirely and just used the date (`2026-09-08...`), and another ignored my prefix altogether and generated its own based on the devotional's title (`In_2026...`). Nothing else about the schema or code changed between these runs, only the model or reasoning level did. It was a small reminder that "the schema guarantees the fields exist" is not the same as "the model will follow every instruction inside a field the same way every time," especially for a free-text field like a filename that isn't itself schema-constrained.

Overall, for a task like this, model and reasoning level choice matters a lot for cost and not that much for quality past a certain point. `luna` at low or medium reasoning got nearly all the value of the most expensive setup for a fraction of the price.

## Obstacles

Most of the time I spent debugging had nothing to do with the prompts themselves:

- Originally I wrote a `--write-file` CLI flag, but then realized it was pointless once every schema required `filename`/`content`/`file_type`. Whether to write a file is now decided by the schema itself.
- The header I was adding to every output file broke `.py` output, since plain text at the top of a Python file isn't valid Python. I fixed this by writing separate formatters for `.txt`, `.py`, and `.md` files, with the `.py` one using `#` comments.
- `Path.read_text()`/`write_text()` default to Windows' `cp1252` encoding, which crashed on emoji in generated code and on curly quotes in the devotional transcript. This I fixed by forcing UTF-8 everywhere.
- I asked the model to pick a filename that wouldn't collide with previous runs. That doesn't work, since each API call is stateless, so the model has no way to know what's already on my local file system, and it kept guessing the same number and overwriting earlier output. In order to fix this, I made it so the code stamped the current time onto the filename instead of asking the model to solve it.
- I generated Connect 4 code using raw terminal color codes that showed up as literal `←[` characters in GitBash instead of actual colors. I was very confused at first but then I swicthed over to Windows PowerShell and eveyrthing displayed correctly.
- The devotional schema originally asked for both the structured fields and a separate Markdown write-up of those same fields, which meant the model was writing everything out twice and roughly doubling output tokens for no new information. So I fixed this by generating the Markdown file from the structured fields in code instead of asking the model to restate itself.

## What I Learned

First, I learned that a schema with `strict: True` turns "the model says it did something" into "the code can verify it did something." This soryt of security and reliability for the ouput really make structyred output such a powerful tool and that's really the main upgrade from my 1A experience to this one. Also, reasoning effort and model choice are real cost chnagers, and the returns drop off fast. Cheapest vs. most expensive setup I tested was roughly a 140 times cost difference for output that wasn't even close to 140 times better. Most of the bugs I hit weren't the model's fault. They were encoding issues, file-writing logic, and formatting, meaning the code around the model rather than the model itself. It goes to show that a model is only as powerful as the code/ tool/ app that utilizes it.

An agent that only produces free text isn't something you can safely build on. You either trust its account of what it did, which can be wrong, or you check every response by hand. A schema fixes that, since the response is guaranteed to be usable and can feed into the next step without a person in the loop. Combined with the cost data above, the practical takeaway is to default to the cheapest model and lowest reasoning setting that reliably meets the schema, and only pay more once there's evidence it actually changes the output in a way that matters.

