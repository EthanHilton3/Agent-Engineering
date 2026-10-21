"""Experiment 3: how does chunk size change similarity?

Same corpus (Book of Mormon), same queries, four chunk sizes:
  phrase  = a sentence-ish piece of a verse (split on , ; :)
  verse   = one verse
  window  = 5 consecutive verses
  chapter = whole chapter
For each query we know roughly where the answer lives, and we look at (a) the
top score at each size and (b) whether the top hit lands in the right place.

Run: python exp3_chunking.py
"""
import re
from collections import defaultdict

import numpy as np

from emb import embed, load_scriptures

verses = [v for v in load_scriptures() if v['book'] not in ('D&C',)][:]  # BoM + PoGP
bom = [v for v in verses if v['ref'].split(':')[0].rsplit(' ', 1)[0] in {
    '1 Nephi', '2 Nephi', 'Jacob', 'Enos', 'Jarom', 'Omni', 'Words of Mormon', 'Mosiah', 'Alma',
    'Helaman', '3 Nephi', '4 Nephi', 'Mormon', 'Ether', 'Moroni'}]
print(len(bom), 'BoM verses')

# chunk builders: each returns list of (label, text, [start_chapter_key])
by_chapter = defaultdict(list)
for v in bom:
    by_chapter[(v['book'], v['chapter'])].append(v)

chunks = {'verse': [], 'window5': [], 'chapter': [], 'phrase': []}
for (book, ch), vs in by_chapter.items():
    key = f'{book} {ch}'
    for v in vs:
        chunks['verse'].append((v['ref'], v['text'], key))
        for p in re.split(r'[;:]', v['text']):
            if len(p.split()) >= 4:
                chunks['phrase'].append((v['ref'], p.strip(), key))
    for i in range(0, len(vs), 5):
        w = vs[i:i + 5]
        chunks['window5'].append((f"{w[0]['ref']}+", ' '.join(x['text'] for x in w), key))
    # chapters can be long (Alma 32-ish is fine; the longest are ~ 6k tokens, under the 8k limit)
    chunks['chapter'].append((key, ' '.join(x['text'] for x in vs)[:24000], key))

for name, c in chunks.items():
    print(f'{name:8} {len(c):6} chunks, avg {np.mean([len(t.split()) for _, t, _ in c]):6.0f} words')

embs = {name: embed([t for _, t, _ in c]) for name, c in chunks.items()}

# (query, chapter where the answer really is)
QUERIES = [
    ('Nephi is commanded to build a ship', '1 Nephi 17'),
    ('compare the word of God to a seed that grows', 'Alma 32'),
    ('Christ visits the people and invites them to touch his wounds', '3 Nephi 11'),
    ('the people forget God when they are prosperous, then are humbled', 'Helaman 12'),
    ('a short question about God', None),   # vague on purpose: no right answer
]

for q, truth in QUERIES:
    qv = embed([q])[0]
    print(f'\n>> {q!r}   (answer lives in: {truth})')
    for name, c in chunks.items():
        s = embs[name] @ qv
        order = np.argsort(-s)
        top = order[0]
        hit = (c[top][2] == truth) if truth else None
        # rank of the first chunk inside the true chapter
        rank = next((r + 1 for r, i in enumerate(order) if c[i][2] == truth), None) if truth else None
        flag = {True: 'RIGHT', False: 'wrong', None: ''}[hit]
        print(f'  {name:8} top={s[top]:.3f}  mean-of-all={s.mean():.3f}  {flag:5} first-right-rank={rank}  -> {c[top][0]}')
