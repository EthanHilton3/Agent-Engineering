"""Experiment 4: auto-generated cross-references.

For a verse, find its nearest neighbours in OTHER chapters (so we don't just
get the verses sitting next to it). Compare raw vs. median-centered embeddings,
and look at how many neighbours are in a different book than the source.

Run: python exp4_crossrefs.py
"""
import numpy as np

from emb import embed, load_scriptures

verses = load_scriptures()
texts = [v['text'] for v in verses]
vecs = embed(texts)
centered = vecs - np.median(vecs, axis=0)
centered /= np.linalg.norm(centered, axis=1, keepdims=True)
chapter_of = [(v['book'], v['chapter']) for v in verses]
index = {v['ref']: i for i, v in enumerate(verses)}


def xrefs(ref, k=5, use=vecs):
    i = index[ref]
    scores = use @ use[i]
    out = []
    for j in np.argsort(-scores):
        if chapter_of[j] == chapter_of[i]:
            continue
        out.append((float(scores[j]), verses[j]['ref'], texts[j]))
        if len(out) == k:
            break
    return out


SEEDS = [
    'Moses 5:11',       # Adam & Eve, joy of redemption (cf. 2 Nephi 2:25)
    '2 Nephi 2:25',
    '1 Nephi 3:7',      # "I will go and do"
    'Alma 32:21',       # faith is not a perfect knowledge
    'D&C 89:18',        # promises of the Word of Wisdom
    'Mosiah 18:9',      # baptismal covenant: mourn with those that mourn
    'Moroni 10:4',      # ask God, the Holy Ghost will manifest the truth
]
for ref in SEEDS:
    print(f'\n### {ref}: {texts[index[ref]][:160]}')
    for label, use in [('raw', vecs), ('centered', centered)]:
        print(f'  [{label}]')
        for s, r, t in xrefs(ref, 5, use):
            print(f'    {s:.3f}  {r}: {t[:100]}')

# How "cross-book" do the neighbours get? Sample 500 verses.
rng = np.random.default_rng(0)
sample = rng.choice(len(verses), 500, replace=False)
for label, use in [('raw', vecs), ('centered', centered)]:
    same_book = total = 0
    for i in sample:
        for s, r, t in xrefs(verses[i]['ref'], 5, use):
            total += 1
            same_book += verses[index[r]]['book'] == verses[i]['book']
    print(f'\n{label}: {same_book / total:.0%} of top-5 neighbours are in the same book as the source verse')
