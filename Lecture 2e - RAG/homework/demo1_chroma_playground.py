"""Demo 1: a tiny Chroma playground.

Practice demo written by Claude to learn how Chroma works. Not part of the chatbot.

Part A: what number does Chroma return, and how does it relate to 2d's cosine?
Part B: what does a metadata filter (where=...) do?
Part C: reopen the collection WITHOUT giving it the embedding function. What happens?
"""
import math

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

ef = OpenAIEmbeddingFunction(model_name="text-embedding-3-small")

# EphemeralClient = in memory only, gone when the script ends.
# (The class code uses PersistentClient, which saves to a folder instead.)
client = chromadb.EphemeralClient()
col = client.create_collection(name="playground", embedding_function=ef)

# Chroma calls OpenAI for us here: 6 documents -> 6 vectors.
col.add(
    ids=["dog", "puppy", "hate", "cheese", "tires", "faith"],
    documents=[
        "I love my dog",
        "I love my puppy",
        "I hate my dog",
        "Me gusta el queso",
        "The car needs new tires",
        "Faith is a principle of action and power",
    ],
    metadatas=[
        {"topic": "pets"},
        {"topic": "pets"},
        {"topic": "pets"},
        {"topic": "food"},
        {"topic": "cars"},
        {"topic": "gospel"},
    ],
)
print(f"Collection has {col.count()} documents\n")


def dot(a, b):
    return sum(float(x) * float(y) for x, y in zip(a, b))


# ---------------------------------------------------------------- Part A
print("=" * 78)
print("PART A: Chroma distance vs. cosine computed by hand")
print("=" * 78)
query = "I love my dog"
q_vec = ef([query])[0]
print(f"Query vector: {len(q_vec)} numbers, length = {math.sqrt(dot(q_vec, q_vec)):.4f}\n")

q = col.query(
    query_texts=[query],
    n_results=6,
    include=["documents", "distances", "embeddings"],
)
# Lists of lists: [0] = results for our first (and only) query.
docs, dists, vecs = q["documents"][0], q["distances"][0], q["embeddings"][0]

print(f"{'document':<42} {'chroma':>7} {'cosine':>7} {'2-2cos':>7} {'sqrt(2-2cos)':>13}")
for doc, dist, vec in zip(docs, dists, vecs):
    cos = dot(q_vec, vec)
    print(f"{doc:<42} {dist:>7.3f} {cos:>7.3f} {2 - 2 * cos:>7.3f} {math.sqrt(max(2 - 2 * cos, 0)):>13.3f}")

# ---------------------------------------------------------------- Part B
print()
print("=" * 78)
print("PART B: metadata filters")
print("=" * 78)
for where in [{"topic": "pets"}, {"topic": "food"}]:
    q = col.query(query_texts=[query], n_results=3, where=where, include=["documents", "distances"])
    print(f"query={query!r}  where={where}")
    for doc, dist in zip(q["documents"][0], q["distances"][0]):
        print(f"    {dist:.3f}  {doc}")
    print()

# ---------------------------------------------------------------- Part C
print("=" * 78)
print("PART C: reopen the collection by name, with NO embedding_function passed")
print("=" * 78)
try:
    same = client.get_collection(name="playground")
    q = same.query(query_texts=[query], n_results=2, include=["documents", "distances"])
    print("It worked. Top 2:")
    for doc, dist in zip(q["documents"][0], q["distances"][0]):
        print(f"    {dist:.3f}  {doc}")
except Exception as exc:  # noqa: BLE001
    print(f"It failed: {type(exc).__name__}: {exc}")


"""
$ python "Lecture 2e - RAG/homework/demo1_chroma_playground.py"
Collection has 6 documents

==============================================================================
PART A: Chroma distance vs. cosine computed by hand
==============================================================================
Query vector: 1536 numbers, length = 0.9997

document                                    chroma  cosine  2-2cos  sqrt(2-2cos)
I love my dog                                0.000   0.999   0.001         0.032
I love my puppy                              0.088   0.912   0.175         0.419
I hate my dog                                0.267   0.733   0.535         0.731
Me gusta el queso                            0.714   0.286   1.429         1.195
The car needs new tires                      0.883   0.117   1.766         1.329
Faith is a principle of action and power     0.887   0.113   1.774         1.332

==============================================================================
PART B: metadata filters
==============================================================================
query='I love my dog'  where={'topic': 'pets'}
    0.000  I love my dog
    0.088  I love my puppy
    0.267  I hate my dog

query='I love my dog'  where={'topic': 'food'}
    0.714  Me gusta el queso

==============================================================================
PART C: reopen the collection by name, with NO embedding_function passed
==============================================================================
It worked. Top 2:
    0.000  I love my dog
    0.088  I love my puppy
"""

# ---------------------------------------------------------------- Findings
#
# PART A: what number does Chroma return?
#   My guess: 2 - 2cos (squared L2). Claude guessed the same.
#   Result: neither. Chroma returned 1 - cos ("cosine distance").
#     e.g. "I love my puppy": cosine 0.912 -> chroma 0.088 = 1 - 0.912
#   Why: OpenAIEmbeddingFunction tells Chroma its default_space() is "cosine",
#   so any collection made with it uses cosine distance. Chroma's general
#   default (squared L2) only applies when the embedding function doesn't say.
#   Takeaway: Chroma distance = 1 - (my 2d score). Lower = closer.
#     2d score 0.85 -> distance 0.15.
#   Side notes:
#     - The same sentence embedded twice gave cosine 0.999, not 1.000, and the
#       vector's length was 0.9997, not exactly 1. OpenAI embeddings are
#       *almost* unit length and *almost* deterministic. Fine for ranking,
#       just don't expect exact numbers.
#     - Ranking order is the same no matter which formula you use. Only the
#       numbers change.
#
# PART B: does a metadata filter act as a relevance check?
#   My guess: it returns only the one food sentence, even though I asked for 3.
#   Result: correct. Only "Me gusta el queso", at distance 0.714. No crash
#   for asking for more results than exist, and no "nothing relevant" either.
#   Takeaway: a where= filter shrinks the pool, then returns the closest
#   things in it no matter how far away they are (same as the 2d "airplane"
#   query). If the chatbot should ever say "the conference didn't cover that",
#   I need a distance cutoff or a system prompt that handles weak matches.
#   Bonus: the cheese scored cosine 0.29, higher than unrelated pairs in 2d
#   (~0.1-0.2). "Me gusta" = "I like", which is close to "I love". Meaning
#   beats language again.
#
# PART C: does the collection remember its embedding model?
#   My guess: yes, it will reuse OpenAI text-embedding-3-small.
#   Result: correct. get_collection(name) with no embedding_function still
#   worked, with the exact same distances as Part A.
#   Why: Chroma saves the embedding function's config (name, model, and the
#   NAME of the API key env var, not the key itself) with the collection.
#   Takeaway: ingest once, then query from a separate chatbot script without
#   re-specifying the model, like query_whole_documents does. OPENAI_API_KEY
#   still has to be set when the chatbot runs.