# Homework 1e – Reasoning

Well I think the main thing I learned from this homwork is that VS Code's terminal only saves about 1000 lines by default. Yeah... that was unfortunate. But we'll get to that later

## My new reasoning chatbot

To build my `chatbot_reasoning.py`, I started by taking the simple console chat loop from Lecture 1c (`chat.py`). And then I added the summary parameter to the api call, so reasoning . And then I got creative and decided to add some user commands that could be called while the chat was live, that would adjust various settings. And I just kept thinking of new commadns so I kept adding them lol. Here's roughly how it went:

1. First I just got it to print the reasoning summary before the answer (`summary: 'auto'` in the api call, then printing any `reasoning` items that came back).
2. Then I added command line flags for `--reasoning`, `--summary`, and `--model`, and stuck all the settings in dictionaries so I could change them in the middle of a chat.
3. Once I could change settings mid-chat I just kept adding more commands, and there got to be so many that I moved them all into one `handle_user_command` function so my main loop wasn't a giant mess.
4. I kept crashing the program with bad api requests, so I added some validation and error handling.
5. Then `/compare`. This was the big one, and it's what I ended up using for pretty much all my experiments.
6. And last I added `/schema` so I could do the structured output experiment (does the order of the fields matter).


## My baby, the `/compare` command

`/compare` is what I used for basically every experiment. You give it a question and it:

- asks that question once at every effort level the model supports (for `gpt-5.6-luna` that's `none`, `low`, `medium`, `high`, `xhigh`)
- prints each answer plus a little stats line (time, tokens, reasoning tokens, cost)
- and then at the end prints a table like this:

```
Comparison on gpt-5.6-luna:
  effort      time  out tok  reasoning        cost   answer
  none       1.13s       22          0   $0.000039   Today is Tuesday, June 18, 2024, in Provo, Utah.
  low        3.21s      220        185   $0.000276   I can’t access a live clock, so I can’t reliably d
  medium     3.92s      286        238   $0.000355   I don’t have access to a live clock, so I can’t re
  high       6.38s      560        516   $0.000684   I can’t access a live clock, so I can’t reliably d
  xhigh      8.29s      737        691   $0.000897   I can’t access a live clock to verify today’s date
  compare total cost: $0.002251
```

This made it really easy to compare the effort levels in terms of time, tokens, and cost. The answer usually was longer so that wasn;t as effective in the table so I usually had to scroll back up to see the answers for each reasoning level, but it still worked very well. Also, every run gets added to the session's usage, so the total cost printed when I quit includes all the comparisons.

The one thing it can't do is use the ongoing conversation. Each effort level just gets the system prompt and the question, nothing else. So I couldn't do stuff like ask a follow up "are you sure?" and compare that across effort levels. (Which is kind of the point though, since that way every level gets the exact same question and it's a fair comparison.) To make it work with a real conversation I'd basically have to keep a separate chat history going for every effort level, and I just didn't have time to build that.


## A couple Obstacles I ran into

- **LaTeX in the terminal.** When I asked math questions, the answers came back full of raw LaTeX like `\sqrt{2048}`, since the model thinks it's in some chat app that will render it nicely. My terminal does not do that. So I made a little system prompt (`plaintext_prompt.md`) that basically says "you're in a plain text terminal, don't use LaTeX or markdown" and that fixed it.
- **Losing output.** The VS Code terminal only keeps so much scrollback, and I didn't configure my chatbot to log anything (since I was just planning on copying all of the terminal text and pasting it into a .txt file like I've done for all the past assignments). And so, after many many experiments with my chatbot, I checked the terminal and found I had lost a lot of my early results. RIP. After that I saved my output to `output.txt` and `output_structured.txt` and made sure to copy over the output periodically.
- **Chaining commands.** I tried `/schema answer-first.json /compare what is today?` on one line, but the command parser only reads the first argument, so the `/compare` part was silently ignored. I didn't have time so i didn't update my chatbot to handle multiple commands on one line, but it was something I considered.


## Some of my experiments

All runs used `gpt-5.6-luna`, mostly through `/compare`. And just an fyi, the real date during my testing was **September 29, 2026**.

- **Simple facts:** "Who is the president of the United States?", who the 48th president is, who the president of the Church of Jesus Christ of Latter-day Saints is
- **Date and time questions:** "what is today?", with and without a location and time
- **Logic puzzles:** the ring thief puzzle, the fish length puzzle, the two ropes, the two guards
- **Arithmetic:** big multiplication and division
- **Physical reasoning:** the stacking problem given as an exmaple for this assignment
- **Vague instructions:** "make this better"
- **Philosophy, emotional, and open-ended questions:** "what is life?", "is everything going to be alright?", why the Eagles didn't just fly Frodo to Mount Doom
- **Meta questions:** how much more reasoning costs, what the model's knowledge cutoff is
- **Structured output order:** the same questions with `answer-first.json` vs `reasoning-first.json`


## What I learned about reasoning

### 1. The "today" problem (reasoning doesn't make it smarter, it just makes it admit when it doesn't know... sometimes)

The date questions were probably the funnest and funniest examples to look at what reasoning actually does.

- When I just asked "what is today's date?" I got **five different dates from five effort levels** (Feb 14 2026, May 10 2025, Mar 24 2026, Jun 15 2026, May 2 2025). All wrong obviously. And the crazy part is every single one used **0 reasoning tokens, even `xhigh`**. So the model just decided it didn't need to think about it and made something up every time.
- Then I added "I am in Provo, Utah" and `none` very confidently told me it was **June 18, 2024**. But every level with reasoning said something like "I can't access a live clock so I can't know the date."
- When I also added "and the time is 8:59pm", `none` and `low` both made up **March 8, 2025**. `medium` and up refused.
- On just "what is today?" `medium` actually thought about it for 146 tokens and *still* made up a date, while `high` and `xhigh` refused.
- My favorite: in one run `none` said "the system date available to me is May 11, 2025." There is no system date. It made that up too! And with the answer-first schema its "reasoning" was literally just "Based on the current system date."

So reasoning can't give the model information it doesn't have. What it can do is make the model notice that it doesn't know, instead of confidently making something up. But that only happens if the model decides the question is worth thinking about. Whether it reasons at all seems to be a threshold, and a small change to the prompt (adding a location) was enough to push it over. Also, what's up with March 8th, 2025???

### 2. The prophet problem (more reasoning actually made it *worse*)

I asked who the president of the Church of Jesus Christ of Latter-day Saints is. The correct answer is, of course, Dallin H. Oaks, since President Russell M. Nelson died last year, shortly after his 101 birthday.

- When I asked it normally, every effort level said Russell M. Nelson.
- Then I asked it to "make sure to verify the actual current one" with the reasoning-first schema, and effort `none` got it **right**! Its reasoning even said Nelson died on September 27, 2025 and President Oaks became president. So the model *does* know this.
- But then `low` through `xhigh` all went back to **Nelson**. `xhigh` spent **33 seconds and 4,520 reasoning tokens** (about **34x the cost** of `none`) just to get it wrong.
- When I told it "for reference, today is 9/29/2026", most of the effort levels finally said **Oaks**, but `xhigh` still went back to Nelson.
- Also, the model's knowledge doesn't match what it says about itself. It says its knowledge cutoff is June 2024, but it knows about President Nelson's death. (And when I was asking about the current US president, it knew Trump was the current one too, so that's odd.)

My guess is that reasoning makes the model more careful (maybe too careful) about recent stuff it isn't super confident about, so it kind of talks itself out of what it actually knows and goes back to the "safe" older answer. And just giving it the date helped way more than cranking up the reasoning did. So thinking longer doesn't automatically mean getting it right.

### 3. Where reasoning actually helps: problems with real steps

- **Arithmetic** is where it clearly paid off. `1829124142 × 129841` and `1829124142 ÷ 2398237` were **wrong at `none` with both schemas**, and **exactly right at every reasoning level**. No contest there.
- **The scheduling problem** from the class materials: with `none` it booked a 45 minute meeting from 2:00 to 2:45, even though one person was only free until 2:30. With reasoning on it caught that there's no 45 minute slot that works for everyone.

### 4. Reasoning also makes no difference on a lot of problems

- **Famous puzzles** (fish length, two ropes, two guards) were solved correctly even at `none`. I assuem this is because they're just memorized from training data, so reasoning just added the cost without improving the output.
- **Simple facts** ("who is the president?") got the same answer at every level, it just cost up to about 4x more.
- **"make this better"** got basically the same reply at every level: "send me the text you want improved."
- **Philosophy and emotional questions** ("what is life?", "is everything going to be alright?") barely used any reasoning (21 to 114 tokens) and the answers were all pretty similar.
- **The stacking problem** is an example of reasoning making things stranger. Several reasoning levels decided to put **all 9 eggs inside the bottle**. I don't know what kind of bottle we are talking about that can fit 9 full raw uncracked eggs inside, but okay. `xhigh` took **57 seconds and 5,178 reasoning tokens** (the most expensive single request I made, I believe) to get there. None of the levels found the classic answer (book -> eggs in a 3x3 grid -> laptop -> bottle -> nail).

### 5. The field order in structured output matters... sometimes

For this one I only looked at effort `none`, because that's the only level where the `reasoning` field in the JSON is the model's *only* chance to think. On any higher effort it already did its built-in reasoning before it even starts writing the JSON, so the order wouldn't really matter.

| Question | Answer first | Reasoning first |
|---|---|---|
| 1829124142 * 129841 | Wrong by ~60 billion. The "reasoning" just restated the answer | Wrong by 600,000. It showed its work and I could find the exact step it messed up |
| 1829124142 / 2398237 | 762.667 (wrong). The "reasoning" just restated the answer | 762.278 (wrong). Showed its work but dropped a digit in the remainder |
| LDS president ("verify") | Nelson (wrong), and then reasoning that backed that up | Oaks (correct). It remembered President Nelson's death first |
| US president | Trump (correct) | Reasoned from its "June 2024 cutoff" and hedged with Biden (wrong) |

- When the answer comes first, the "reasoning" is really just a justification. The model already committed to its answer and then just defends it.
- When the reasoning comes first you actually get real work, and when it's wrong you can see exactly where it went wrong, which would be super helpful for debugging.
- But reasoning first wasn't always more accurate. It fixed the prophet question but messed up the US president one.
- And neither one comes close to the built-in reasoning for the math. Every reasoning level got both of those exactly right.
- To be fair, I only ran each of these once, so I wouldn't call any of this proven.


## Why this matters for agent engineering

- **Reasoning costs** An agent that runs at `xhigh` on everything would be about x5 more expensive and a lot slower, often for identical answers. It makes more sense to choose the effort for each task: low or none for simple lookups and formatting, higher for multi-step math, planning, and constraint checking.
- **Reasoning can't replace context.** If an agent needs to know something current (like the date, or who's in charge of something), you have to actually give it that info, like in the system prompt or through a tool. Making it think harder won't fix it. Just telling it the date helped more than `xhigh` did.
- **Order matters in structured output.** If an agent's JSON output has a `reasoning` field, put it *before* the answer or decision fields. Otherwise the "reasoning" is just justifying something it already decided.
- **Test instead of assuming.** Using `/compare` really showed my the my intution that `more reasoning = better` turned out to be a pretty wrong generalization in many places. This homework, helped me figure out when its useful adn to what extent.


## Hours spent

I spent way too long on this assignment, almost 5 hours.
