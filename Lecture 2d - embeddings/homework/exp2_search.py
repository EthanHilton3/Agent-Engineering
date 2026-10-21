"""Experiment 2: a tiny semantic search engine over BoM + D&C + PoGP verses,
and a hunt for failures (retrieved-but-shouldn't-have, or missed-but-should-have).

Run: python exp2_search.py
"""
import numpy as np

from emb import embed, load_scriptures, top_k

verses = load_scriptures()
texts = [v['text'] for v in verses]
labeled = [f"{v['ref']}: {v['text']}" for v in verses]
print(f'{len(verses)} verses')
vecs = embed(texts)
median = np.median(vecs, axis=0)


def show(query, k=4, centered=False):
    q = embed([query])[0]
    if centered:
        scores = (vecs - median) @ q
    else:
        scores = vecs @ q
    print(f'\n>> {query!r}' + ('  [median-centered]' if centered else ''))
    for i in np.argsort(-scores)[:k]:
        print(f'  {scores[i]:.3f}  {verses[i]["ref"]}: {texts[i][:110]}')


print('\n######## 1. does it work at all?')
for q in ['build a boat', 'he talked with God and learned', 'hable con dios',
          'forgiving people who wronged you', 'what to eat and drink for good health']:
    show(q)

print('\n######## 2. wording very different from the verse (paraphrase of a known verse)')
# 1 Nephi 3:7, but in modern words
show('God will never ask you to do something without giving you a way to do it')
show('and thus have I accomplished all that was accounted me before my teacher')  # from the live demo
show('and thus have I accomplished all that was accounted me before my teacher', centered=True)

print('\n######## 3. failures: things that are NOT in these books')
for q in ['airplane', 'computer programming', 'the Eiffel Tower', 'pizza recipe']:
    show(q, k=3)

print('\n######## 4. failures: negation and exact-word traps')
show('wicked people who were NOT destroyed')
show('verses that do not mention God')
show('Nephi')           # a bare name: does it find Nephi, or "Nephites"/"Lehi"?
show('the number 42')

print('\n######## 5. abbreviations / typos in the query')
for q in ['Doctrine and Covenants 89 word of wisdom', 'Wrd of Wisdum', 'WoW', 'JS-H first vision', 'Joseph Smith history angel Moroni']:
    show(q, k=3)
