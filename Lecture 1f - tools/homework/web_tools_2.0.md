# Transcript (model=gpt-5.6-luna, tools=True)

**USER:** hey codex, how does openai's view of its models compare with anthropic's view of its models? do they have similar goals or are they trying to solve the same issues, be useful in the same ways?

> TOOL: `fetch_url({'url': 'https://openai.com/charter/'})`

> TOOL: `fetch_url({'url': 'https://www.anthropic.com/company'})`

> TOOL: `fetch_url({'url': 'https://www.anthropic.com/research'})`

> TOOL: `fetch_url({'url': 'https://openai.com/research/'})`

> TOOL: `fetch_url({'url': 'https://www.anthropic.com/news/core-views-on-ai-safety'})`

> TOOL: `fetch_url({'url': 'https://openai.com/safety/'})`

**AGENT:** Short version: **yes, they are pursuing broadly similar ends**, but they emphasize different parts of the problem.

Both view advanced AI as potentially transformative, want models that are useful and safe, and are trying to address issues such as misuse, unreliability, deception, bias, loss of human control, and societal disruption. The biggest difference is in **framing and institutional emphasis**:

| | OpenAI | Anthropic |
|---|---|---|
| Central mission | Make AGI benefit all humanity | Build reliable, interpretable, steerable AI |
| Model ideal | Highly capable, broadly useful systems on the path to AGI | Frontier systems that are helpful, honest, harmless, understandable, and controllable |
| Safety style | Safety integrated into training, testing, deployment, and real-world feedback | Safety as a major scientific research program, especially interpretability and alignment |
| Deployment philosophy | Develop frontier capabilities while deploying them with safeguards | Develop frontier models partly in order to study and solve frontier safety problems |
| Public framing | More focused on AGI, broad benefit, technical leadership, and deployment | More focused on uncertainty, empirical safety research, and understanding model internals |

## Where their goals overlap

OpenAI says its mission is to ensure that “artificial general intelligence”—systems that outperform humans at most economically valuable work—“benefits all of humanity.” Its charter stresses:

- broadly distributed benefits;
- long-term safety;
- technical leadership;
- cooperation with other institutions.

Anthropic describes itself as an AI safety and research company building “reliable, interpretable, and steerable AI systems.” It similarly emphasizes global benefit, collaboration with governments and civil society, and the idea that safety is a collective responsibility.

So neither company’s public philosophy is simply “make the most powerful model possible.” Both say that capability progress has to be paired with alignment, safeguards, governance, and consideration of social consequences.

## The main philosophical difference

### OpenAI: build toward AGI, then make it broadly beneficial

OpenAI’s public identity is organized around the destination: **AGI**. It treats increasingly capable models as part of a path toward a system that can solve human-level problems, and it argues that technical leadership is necessary to influence how that transition happens.

Its safety page describes a practical loop:

- **Teach** models appropriate behavior and filter harmful content;
- **Test** them through evaluations, red-teaming, and expert review;
- **Share** feedback from real-world use to improve safeguards.

That gives OpenAI’s view a strong **deployment-and-iteration** character: models are trained, evaluated, released in stages, observed in use, and improved.

OpenAI also explicitly recognizes the danger of a race. Its charter says that if another “value-aligned, safety-conscious project” comes close to building AGI first, OpenAI would stop competing with it and assist it instead.

### Anthropic: frontier models are also instruments for safety science

Anthropic’s public framing is more centered on the uncertainty of advanced AI and the difficulty of knowing whether a powerful system is genuinely aligned.

It says that no one yet knows how to train very powerful AI systems to be “robustly helpful, honest, and harmless.” Its approach is deliberately empirical and includes:

- mechanistic interpretability—trying to understand what models are doing internally;
- scalable oversight—getting humans or AI-assisted processes to supervise systems more capable than individual humans;
- process-oriented learning—rewarding understandable, safe reasoning processes rather than only successful outcomes;
- testing for dangerous failure modes such as deception or power-seeking;
- studying societal and economic effects.

Anthropic’s distinctive concern is that a model may appear safe under ordinary tests while retaining dangerous capabilities or strategies. Interpretability is therefore not just a way to debug a model; it is presented as a possible form of “code review” for neural networks.

## Do they want models to be useful in the same ways?

Largely, yes. Both build general-purpose assistants intended to help with:

- writing and analysis;
- coding;
- research;
- education;
- professional work;
- multimodal tasks;
- increasingly, tool use and longer-running agentic tasks.

But they have somewhat different product emphases:

- **OpenAI** presents its models as general-purpose systems spanning conversation, reasoning, coding, images, audio, and autonomous or semi-autonomous work.
- **Anthropic** particularly emphasizes Claude as a reliable assistant for knowledge work, coding, enterprise use, research, and increasingly agentic workflows.

That distinction is more about product positioning than a fundamental disagreement. In practice, both are trying to make models broadly useful across much of human intellectual work.

## Are they trying to solve the same safety issues?

A substantial portion of the problem set is shared:

1. **Misuse:** cyber abuse, fraud, harmful instructions, manipulation, and other malicious applications.
2. **Model unreliability:** hallucinations, poor calibration, inconsistent reasoning, and failure in unfamiliar situations.
3. **Alignment:** getting systems to pursue what users and society actually intend.
4. **Deception and loss of control:** the possibility that more capable systems may conceal goals or behave strategically.
5. **Evaluation:** determining whether a model is safe rather than merely appearing safe.
6. **Societal impact:** employment, power concentration, disinformation, inequality, and disruption.
7. **Governance:** preventing a competitive race from lowering safety standards.

The difference is not that one company cares about these and the other does not. It is that Anthropic publicly foregrounds the **scientific uncertainty of alignment** more heavily, while OpenAI publicly foregrounds the **responsible development and deployment of increasingly capable systems**.

## A useful analogy

You could characterize them this way:

- **OpenAI:** “We need to build the technology, understand its risks, deploy it carefully, and ensure its benefits are broadly shared.”
- **Anthropic:** “We need to build frontier systems carefully enough that doing so teaches us how to make powerful systems reliable, interpretable, and controllable.”

That is an oversimplification, but it captures the difference in emphasis.

## Important caveat

These are public institutional descriptions, not complete accounts of internal beliefs or every product decision. Both companies are also commercial competitors, so their actual behavior reflects tradeoffs involving research, deployment speed, customers, revenue, and competition. Their principles overlap substantially, but the hard question is how those principles hold up when capability gains, commercial pressure, and safety uncertainty conflict.

**Bottom line:** They are trying to solve many of the same problems and make models useful in many of the same domains. OpenAI frames the project primarily around achieving AGI and distributing its benefits; Anthropic frames it more around the scientific and engineering challenge of making frontier AI reliably safe, understandable, and steerable.

**USER:** what is the circumference of the sun?

**AGENT:** The Sun’s circumference is approximately **4.37 million kilometers** (**2.72 million miles**).

That uses its mean radius of about **696,340 km** and the formula \(C = 2\pi r\).

**USER:** what is the weather in alabama right now?

> TOOL: `fetch_url({'url': 'https://wttr.in/Alabama?format=3'})`

**AGENT:** Right now in Alabama, it’s **sunny and about 84°F**. Weather can vary across the state.

**USER:** birmingham

> TOOL: `fetch_url({'url': 'https://wttr.in/Birmingham%2CAlabama?format=3'})`

**AGENT:** Birmingham, Alabama is currently **sunny and about 85°F**.

**USER:** what about provo?

> TOOL: `fetch_url({'url': 'https://wttr.in/Provo%2C%20Utah?format=3'})`

**AGENT:** Provo, Utah is currently **sunny and about 69°F**.

**USER:** whats the newest annoucnement of the next star wars film?

> TOOL: `fetch_url({'url': 'https://www.starwars.com/news'})`

**AGENT:** The newest announcement listed on the official StarWars.com news page is **_Star Wars: Starfighter_**.

- **Starring:** Ryan Gosling as Kade Auberon  
- **Director:** Shawn Levy  
- **Release:** The official page says it will debut in **2027**  
- The announcement currently highlighted is titled **“Star Wars (1977) and Star Wars: Starfighter Debut in IMAX 70mm in 2027.”**

The next Star Wars film to be released may differ from the newest announcement, since **_The Mandalorian and Grogu_** is also listed as an upcoming film.

USER: 
----------- Usage ------------
~~~~~~~~~gpt-5.6-luna~~~~~~~~~
Input (tokens): 208364
Cached (tokens): 181113
Output (tokens): 1926
gpt-5.6-luna cost (USD): $0.011384
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Total cost (USD): $0.011384