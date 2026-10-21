"""Experiment 5: find the Bible passages hidden inside the Book of Mormon (and PoGP).

The BoM quotes long stretches of the Bible (Isaiah, the Sermon on the Mount,
Malachi...), so we have a real answer key to grade a cross-reference system with.

Run one part at a time:  python exp5_hidden_copies.py A   (or B, C, D)
Before each part, read the comment and write down your guess.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

import numpy as np

from emb import CACHE_DIR, embed, load_scriptures

# Answer key: (BoM/PoGP chapter, Bible chapter(s), kind)
#   near    = almost word for word
#   added   = a copy, but with extra verses or an added intro
#   loose   = heavily rewritten / expanded
#   partial = the copy is only a slice of a longer chapter
KEY = [
    ('1 Nephi 20', ['Isaiah 48'], 'near'),
    ('1 Nephi 21', ['Isaiah 49'], 'near'),
    ('2 Nephi 7', ['Isaiah 50'], 'near'),
    ('2 Nephi 8', ['Isaiah 51', 'Isaiah 52'], 'added'),
    *[(f'2 Nephi {n}', [f'Isaiah {n - 10}'], 'near') for n in range(12, 25)],
    ('2 Nephi 27', ['Isaiah 29'], 'loose'),
    ('Mosiah 13', ['Exodus 20'], 'partial'),   # Ten Commandments are only verses 12-24
    ('Mosiah 14', ['Isaiah 53'], 'near'),
    ('3 Nephi 12', ['Matthew 5'], 'added'),
    ('3 Nephi 13', ['Matthew 6'], 'added'),
    ('3 Nephi 14', ['Matthew 7'], 'added'),
    ('3 Nephi 22', ['Isaiah 54'], 'near'),
    ('3 Nephi 24', ['Malachi 3'], 'near'),
    ('3 Nephi 25', ['Malachi 4'], 'near'),
    ('Moses 2', ['Genesis 1'], 'added'),
    ('Moses 3', ['Genesis 2'], 'added'),
    ('Moses 4', ['Genesis 3'], 'added'),
    ('Moses 5', ['Genesis 4'], 'loose'),
    ('Moses 8', ['Genesis 5', 'Genesis 6'], 'loose'),
    ('Abraham 4', ['Genesis 1'], 'loose'),
    ('Abraham 5', ['Genesis 2'], 'loose'),
    ('Joseph Smith—Matthew 1', ['Matthew 24'], 'loose'),
]
PARTIAL_VERSES = {'Mosiah 13': range(12, 25)}   # only these verses of a partial chapter count

BOM_BOOKS = {'1 Nephi', '2 Nephi', 'Jacob', 'Enos', 'Jarom', 'Omni', 'Words of Mormon', 'Mosiah',
             'Alma', 'Helaman', '3 Nephi', '4 Nephi', 'Mormon', 'Ether', 'Moroni'}

source = load_scriptures(('book-of-mormon', 'pearl-of-great-price'))
bible = load_scriptures(('old-testament', 'new-testament'))
bom = [v for v in source if v['book'] in BOM_BOOKS]


def chapter(v):
    return f"{v['book']} {v['chapter']}"


def chapters(verses):
    out = defaultdict(list)
    for v in verses:
        out[chapter(v)].append(v['text'])
    # cap very long chapters so each stays under the model's ~8k-token input limit
    return {k: ' '.join(t)[:24000] for k, t in out.items()}


def verse_truth(v):
    """The Bible chapters this BoM verse should match, or None if it isn't in the key."""
    for src, targets, kind in KEY:
        if chapter(v) == src and kind != 'loose':
            if src in PARTIAL_VERSES and int(v['ref'].split(':')[1]) not in PARTIAL_VERSES[src]:
                return None
            return targets
    return None


def _words(text):
    """Lowercase, no punctuation, so 'LORD,' and 'Lord;' compare equal."""
    return re.sub(r"[^a-z' ]", ' ', text.lower().replace('—', ' ')).split()


def _grams(w, n=3):
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def text_key_v2():
    """Answer key v2, built WITHOUT embeddings so it can fairly grade them.

    For each BoM verse: find Bible candidates that share 3-word phrases, then score
    each with a word-by-word alignment (difflib, like `diff`) that tolerates added
    and changed words. Returns, per BoM verse, the Bible chapters it should match
    (or None if it isn't a quote).
      - alignment >= 0.7 with some Bible verse  -> a quote, wherever it is
        (every candidate chapter >= 0.7 counts, so Bible duplicates like Isaiah 2 / Micah 4 are fine)
      - in v1, and alignment >= 0.5             -> kept (an edited quote)
      - in v1, but under 6 words                -> kept (too short to measure: "Thou shalt not kill.")
      - in v1, alignment < 0.5                  -> dropped (new text with no Bible source)
    """
    path = CACHE_DIR / 'text_key_v2.json'
    if path.exists():
        return [set(t) if t is not None else None for t in json.loads(path.read_text())]
    bible_words = [_words(v['text']) for v in bible]
    index = defaultdict(set)
    for j, w in enumerate(bible_words):
        for g in _grams(w):
            index[g].add(j)
    key = []
    for v in bom:
        w = _words(v['text'])
        v1 = verse_truth(v)
        cands = Counter(j for g in _grams(w) for j in index.get(g, ())).most_common(5)
        ratios = [(SequenceMatcher(None, w, bible_words[j], autojunk=False).ratio(), j) for j, _ in cands]
        best = max((r for r, _ in ratios), default=0.0)
        if len(w) >= 6 and best >= 0.7:
            key.append({chapter(bible[j]) for r, j in ratios if r >= 0.7} | set(v1 or []))
        elif v1 is not None and (len(w) < 6 or best >= 0.5):
            key.append(set(v1))
        else:
            key.append(None)
    path.write_text(json.dumps([sorted(t) if t is not None else None for t in key]))
    return key


def best_bible_match(vecs, bible_vecs, block=500):
    """For each row of vecs, the index and score of its closest Bible verse."""
    idx, score = [], []
    for i in range(0, len(vecs), block):
        s = vecs[i:i + block] @ bible_vecs.T
        idx.append(s.argmax(axis=1))
        score.append(s.max(axis=1))
    return np.concatenate(idx), np.concatenate(score)


def part_a():
    # Chapter level: for each copied chapter, what rank does its Bible twin come back at (out of 1,189)?
    # Guess: do the 'near' copies all come back at rank 1? What about 'loose' rewrites and the
    # 'partial' one (Mosiah 13, where the Ten Commandments are only 13 of 35 verses)?
    # --- I think the near copies will come back at rank 1, the loose rewrites will be only slightly lower (still .85 or higher), adn the partial ones will come out closer to .5 or so
    # What score do you think a near-identical chapter gets: 0.99? 0.9? lower?
    # --- From what i've noticed, theres alwasy a little noise, so I think the near-identical chapters will be around 0.95 or so, but not quite 1.0
    src_ch = chapters(source)
    bib_ch = chapters(bible)
    bib_names = list(bib_ch)
    bib_vecs = embed([bib_ch[k] for k in bib_names])
    print(f'{len(bib_names)} Bible chapters\n')
    print(f'{"chapter":24} {"kind":8} {"twin":12} rank  score   (top match if wrong)')
    for src, targets, kind in KEY:
        q = embed([src_ch[src]])[0]
        s = bib_vecs @ q
        order = list(np.argsort(-s))
        rank = min(order.index(bib_names.index(t)) for t in targets) + 1
        top = bib_names[order[0]]
        best = max(s[bib_names.index(t)] for t in targets)
        extra = '' if rank == 1 else f'   (top: {top} {s[order[0]]:.3f})'
        print(f'{src:24} {kind:8} {targets[0]:12} {rank:>4}  {best:.3f}{extra}')

    """
    $ python exp5_hidden_copies.py A
    1189 Bible chapters

    chapter                  kind     twin         rank  score   (top match if wrong)
    1 Nephi 20               near     Isaiah 48       1  0.985
    1 Nephi 21               near     Isaiah 49       1  0.975
    2 Nephi 7                near     Isaiah 50       1  0.956
    2 Nephi 8                added    Isaiah 51       1  0.961
    2 Nephi 12               near     Isaiah 2        1  0.981
    2 Nephi 13               near     Isaiah 3        1  0.988
    2 Nephi 14               near     Isaiah 4        1  0.990
    2 Nephi 15               near     Isaiah 5        1  0.987
    2 Nephi 16               near     Isaiah 6        1  0.990
    2 Nephi 17               near     Isaiah 7        1  0.997
    2 Nephi 18               near     Isaiah 8        1  0.991
    2 Nephi 19               near     Isaiah 9        1  0.990
    2 Nephi 20               near     Isaiah 10       1  0.995
    2 Nephi 21               near     Isaiah 11       1  0.997
    2 Nephi 22               near     Isaiah 12       1  0.993
    2 Nephi 23               near     Isaiah 13       1  0.991
    2 Nephi 24               near     Isaiah 14       1  0.993
    2 Nephi 27               loose    Isaiah 29       1  0.886
    Mosiah 13                partial  Exodus 20     110  0.630   (top: Acts 7 0.748)
    Mosiah 14                near     Isaiah 53       1  0.970
    3 Nephi 12               added    Matthew 5       1  0.873
    3 Nephi 13               added    Matthew 6       1  0.986
    3 Nephi 14               added    Matthew 7       1  0.978
    3 Nephi 22               near     Isaiah 54       1  0.980
    3 Nephi 24               near     Malachi 3       1  0.943
    3 Nephi 25               near     Malachi 4       1  0.978
    Moses 2                  added    Genesis 1       1  0.942
    Moses 3                  added    Genesis 2       1  0.969
    Moses 4                  added    Genesis 3       1  0.898
    Moses 5                  loose    Genesis 4       1  0.832
    Moses 8                  loose    Genesis 5       1  0.885
    Abraham 4                loose    Genesis 1       1  0.845
    Abraham 5                loose    Genesis 2       1  0.920
    Joseph Smith—Matthew 1   loose    Matthew 24      1  0.965
    """
    # I guess with embedding the whole chapter, the semantic meaning is of the whole chapter anyways, so if the chapters are near duplicates or loose ones, its almost excatly the same.
    # Even the partial one scored higher than I imagined, though I guess since the Ten Commandments are a very well known passage, it makes sense that it would be more related to other chapters than I thought.


def part_b():
    # Verse level: treat "best Bible match scores above X" as a quote detector, and grade it.
    #   flagged   = BoM verses whose best Bible match is above the threshold
    #   correct   = flagged AND the match lands in the right Bible chapter
    #   recall    = share of the quoted verses in the key that got correctly flagged
    # Guess: which threshold gives the best balance? Will 0.95 catch most quotes, or only the
    # word-for-word ones? At 0.70, how many verses that aren't quotes do you think get flagged?
    # --- I think 0.95 will catch most of the near-identical ones, but not the loose or partial ones, so it will have a low recall.
    # --- I think 0.70 will catch most of the quotes, but will also flag a lot of verses that aren't quotes, so it will have a low precision.
    #
    # Part B prints two tables: v1 (my hand-written chapter key) and v2 (the text-matching key).
    # v2 guess: with the key fixed, how many 'outside-key' flags are left at 0.85? Does recall go up or down?
    bom_vecs = embed([v['text'] for v in bom])
    bible_vecs = embed([v['text'] for v in bible])
    idx, score = best_bible_match(bom_vecs, bible_vecs)
    v1 = [verse_truth(v) for v in bom]
    v2 = text_key_v2()
    print(f'{len(bom)} BoM verses vs {len(bible)} Bible verses\n')
    for name, truth in [('v1: hand-written chapter key', v1), ('v2: text-matching key', v2)]:
        quoted = sum(t is not None for t in truth)
        print(f'== {name}  ({quoted} verses are quotes in this key)')
        # precision = correct / flagged  (when it fires, how often is it right?)
        # recall    = correct / quoted   (of all real quotes, how many did it catch?)
        print('threshold  flagged  correct  outside-key  precision  recall')
        for th in [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60]:
            flagged = correct = outside = 0
            for i, t in enumerate(truth):
                if score[i] < th:
                    continue
                flagged += 1
                if t is None:
                    outside += 1
                elif chapter(bible[idx[i]]) in t:
                    correct += 1
            print(f'   {th:.2f}   {flagged:6}   {correct:6}   {outside:9}   {correct / flagged:8.0%}   {correct / quoted:5.0%}')
        print()
    added = sum(a is None and b is not None for a, b in zip(v1, v2))
    dropped = sum(a is not None and b is None for a, b in zip(v1, v2))
    print(f'v2 vs v1: {added} quotes added, {dropped} non-quotes dropped')
    """
    $ python exp5_hidden_copies.py B
    6604 BoM verses vs 31102 Bible verses; 534 verses are quotes in the key

    threshold  flagged  correct  outside-key  recall
    0.95      474      431          42     81%
    0.90      537      481          55     90%
    0.85      568      501          66     94%
    0.80      601      513          87     96%
    0.75      679      521         156     98%
    0.70      966      523         439     98%
    0.60     3736      523        3202     98%
    """
    # I think .85 would be the best balance for these embeddings (i realize this can change based on embeddings, espcialy of differnt chunk sizes),
    #  getting 94% of the quotes but only 66 verse outside the key is really ideal in my eyes.
    # And any lower of a threshold didnt really improve the recall, but it did allow a crazy more amount of verses in than it should ahve


    """
    $ python exp5_hidden_copies.py B
    6604 BoM verses vs 31102 Bible verses

    == v1: hand-written chapter key  (534 verses are quotes in this key)
    threshold  flagged  correct  outside-key  precision  recall
    0.95      474      431          42        91%     81%
    0.90      537      481          55        90%     90%
    0.85      568      501          66        88%     94%
    0.80      601      513          87        85%     96%
    0.75      679      521         156        77%     98%
    0.70      966      523         439        54%     98%
    0.60     3736      523        3202        14%     98%

    == v2: text-matching key  (597 verses are quotes in this key)
    threshold  flagged  correct  outside-key  precision  recall
    0.95      474      474           0       100%     79%
    0.90      537      537           0       100%     90%
    0.85      568      562           6        99%     94%
    0.80      601      579          22        96%     97%
    0.75      679      589          87        87%     99%
    0.70      966      593         369        61%     99%
    0.60     3736      593        3139        16%     99%

    v2 vs v1: 71 quotes added, 8 non-quotes dropped
    """



def part_c():
    # The interesting cases.
    #   1. Highest-scoring verses OUTSIDE the key: is my answer key missing real quotes,
    #      or are these false alarms (common phrases like "And it came to pass")?
    #   2. Lowest-scoring verses INSIDE the key: which quoted verses look least like their source, and why?
    # Guess: what kind of verse do you think shows up in each list?
    # --- I think all the real quptes will be actual real quptes and none will be false alarms, and the lowest scoring ones will be the loose rewrites, since they are the most different from their source.
    # ---  And for list 2, I think the lowest scoring ones will justbe in the wrong chpater, but still the same verse (more or less)
    # --- I think when the embeddings and the answer key disagree, its because the answer key is wrong, not the embeddings. I have a hunch that the embeddings are more accurate than the answer key.
    bom_vecs = embed([v['text'] for v in bom])
    bible_vecs = embed([v['text'] for v in bible])
    idx, score = best_bible_match(bom_vecs, bible_vecs)
    truth = [verse_truth(v) for v in bom]

    print('== 1. Top 15 matches OUTSIDE the answer key')
    outside = [i for i, t in enumerate(truth) if t is None]
    for i in sorted(outside, key=lambda i: -score[i])[:15]:
        print(f'  {score[i]:.3f}  {bom[i]["ref"]:18} -> {bible[idx[i]]["ref"]}')
        print(f'         BoM:   {bom[i]["text"][:100]}')
        print(f'         Bible: {bible[idx[i]]["text"][:100]}')

    print('\n== 2. Bottom 10 matches INSIDE the answer key')
    inside = [i for i, t in enumerate(truth) if t is not None]
    for i in sorted(inside, key=lambda i: score[i])[:10]:
        ok = 'right chapter' if chapter(bible[idx[i]]) in truth[i] else 'WRONG chapter'
        print(f'  {score[i]:.3f}  {bom[i]["ref"]:18} -> {bible[idx[i]]["ref"]}  ({ok})')
        print(f'         BoM:   {bom[i]["text"][:100]}')
        print(f'         Bible: {bible[idx[i]]["text"][:100]}')

    """
    $ python exp5_hidden_copies.py C
    == 1. Top 15 matches OUTSIDE the answer key
    1.001  2 Nephi 27:35      -> Isaiah 29:24
            BoM:   They also that erred in spirit shall come to understanding, and they that murmured shall learn doctr
            Bible: They also that erred in spirit shall come to understanding, and they that murmured shall learn doctr
    1.001  2 Nephi 30:11      -> Isaiah 11:5
            BoM:   And righteousness shall be the girdle of his loins, and faithfulness the girdle of his reins.
            Bible: And righteousness shall be the girdle of his loins, and faithfulness the girdle of his reins.
    1.000  2 Nephi 30:14      -> Isaiah 11:8
            BoM:   And the sucking child shall play on the hole of the asp, and the weaned child shall put his hand on 
            Bible: And the sucking child shall play on the hole of the asp, and the weaned child shall put his hand on 
    0.997  2 Nephi 27:34      -> Isaiah 29:23
            BoM:   But when he seeth his children, the work of my hands, in the midst of him, they shall sanctify my na
            Bible: But when he seeth his children, the work of mine hands, in the midst of him, they shall sanctify my 
    0.997  3 Nephi 20:45      -> Isaiah 52:15
            BoM:   So shall he sprinkle many nations; the kings shall shut their mouths at him, for that which had not 
            Bible: So shall he sprinkle many nations; the kings shall shut their mouths at him: for that which had not 
    0.996  3 Nephi 20:43      -> Isaiah 52:13
            BoM:   Behold, my servant shall deal prudently; he shall be exalted and extolled and be very high.
            Bible: Behold, my servant shall deal prudently, he shall be exalted and extolled, and be very high.
    0.996  2 Nephi 30:13      -> Isaiah 11:7
            BoM:   And the cow and the bear shall feed; their young ones shall lie down together; and the lion shall ea
            Bible: And the cow and the bear shall feed; their young ones shall lie down together: and the lion shall ea
    0.995  3 Nephi 20:37      -> Isaiah 52:2
            BoM:   Shake thyself from the dust; arise, sit down, O Jerusalem; loose thyself from the bands of thy neck,
            Bible: Shake thyself from the dust; arise, and sit down, O Jerusalem: loose thyself from the bands of thy n
    0.995  2 Nephi 6:7        -> Isaiah 49:23
            BoM:   And kings shall be thy nursing fathers, and their queens thy nursing mothers; they shall bow down to
            Bible: And kings shall be thy nursing fathers, and their queens thy nursing mothers: they shall bow down to
    0.995  Mosiah 15:30       -> Isaiah 52:9
            BoM:   Break forth into joy, sing together, ye waste places of Jerusalem; for the Lord hath comforted his p
            Bible: Break forth into joy, sing together, ye waste places of Jerusalem: for the LORD hath comforted his p
    0.995  3 Nephi 16:19      -> Isaiah 52:9
            BoM:   Break forth into joy, sing together, ye waste places of Jerusalem; for the Lord hath comforted his p
            Bible: Break forth into joy, sing together, ye waste places of Jerusalem: for the LORD hath comforted his p
    0.995  3 Nephi 21:18      -> Micah 5:14
            BoM:   And I will pluck up thy groves out of the midst of thee; so will I destroy thy cities.
            Bible: And I will pluck up thy groves out of the midst of thee: so will I destroy thy cities.
    0.994  3 Nephi 16:18      -> Isaiah 52:8
            BoM:   Thy watchmen shall lift up the voice; with the voice together shall they sing, for they shall see ey
            Bible: Thy watchmen shall lift up the voice; with the voice together shall they sing: for they shall see ey
    0.993  2 Nephi 27:29      -> Isaiah 29:18
            BoM:   And in that day shall the deaf hear the words of the book, and the eyes of the blind shall see out o
            Bible: And in that day shall the deaf hear the words of the book, and the eyes of the blind shall see out o
    0.990  Mosiah 12:21       -> Isaiah 52:7
            BoM:   How beautiful upon the mountains are the feet of him that bringeth good tidings; that publisheth pea
            Bible: How beautiful upon the mountains are the feet of him that bringeth good tidings, that publisheth pea

    == 2. Bottom 10 matches INSIDE the answer key
    0.610  3 Nephi 12:19      -> John 15:10  (WRONG chapter)
            BoM:   And behold, I have given you the law and the commandments of my Father, that ye shall believe in me,
            Bible: If ye keep my commandments, ye shall abide in my love; even as I have kept my Father's commandments,
    0.610  3 Nephi 12:46      -> Luke 24:44  (WRONG chapter)
            BoM:   Therefore those things which were of old time, which were under the law, in me are all fulfilled.
            Bible: And he said unto them, These are the words which I spake unto you, while I was yet with you, that al
    0.619  3 Nephi 14:1       -> 2 Chronicles 19:6  (WRONG chapter)
            BoM:   And now it came to pass that when Jesus had spoken these words he turned again to the multitude, and
            Bible: And said to the judges, Take heed what ye do: for ye judge not for man, but for the LORD, who is wit
    0.642  3 Nephi 12:2       -> Matthew 3:11  (WRONG chapter)
            BoM:   And again, more blessed are they who shall believe in your words because that ye shall testify that 
            Bible: I indeed baptize you with water unto repentance: but he that cometh after me is mightier than I, who
    0.646  3 Nephi 12:29      -> Deuteronomy 6:6  (WRONG chapter)
            BoM:   Behold, I give unto you a commandment, that ye suffer none of these things to enter into your heart;
            Bible: And these words, which I command thee this day, shall be in thine heart:
    0.648  3 Nephi 12:1       -> Luke 3:16  (WRONG chapter)
            BoM:   And it came to pass that when Jesus had spoken these words unto Nephi, and to those who had been cal
            Bible: John answered, saying unto them all, I indeed baptize you with water; but one mightier than I cometh
    0.671  3 Nephi 12:30      -> 1 Peter 3:17  (WRONG chapter)
            BoM:   For it is better that ye should deny yourselves of these things, wherein ye will take up your cross,
            Bible: For it is better, if the will of God be so, that ye suffer for well doing, than for evil doing.
    0.707  3 Nephi 12:47      -> 2 Corinthians 5:17  (WRONG chapter)
            BoM:   Old things are done away, and all things have become new.
            Bible: Therefore if any man be in Christ, he is a new creature: old things are passed away; behold, all thi
    0.725  3 Nephi 12:20      -> Matthew 18:3  (WRONG chapter)
            BoM:   Therefore come unto me and be ye saved; for verily I say unto you, that except ye shall keep my comm
            Bible: And said, Verily I say unto you, Except ye be converted, and become as little children, ye shall not
    0.738  3 Nephi 24:1       -> Malachi 3:1  (right chapter)
            BoM:   And it came to pass that he commanded them that they should write the words which the Father had giv
            Bible: Behold, I will send my messenger, and he shall prepare the way before me: and the Lord, whom ye seek
    """
    # So my assumption of the first list was correct. There were no false alarms, all of the top 15 matched almost excatly, with just minor grmmatical or word changes.
    # I guess the embeddings are really good at finding exact matches, even if they are not in the answer key. How did the answer keyt miss these? Didn't Claude make it?
    # For the second list, the verses were not the same, they were all just vaugely related on topics such as baptism, or old vs new, judging others, etc
    # But overall, the embeddings were more correct and accurate than the key, since i guess theres literally no way to forget about a verse: all the math is done on everything embedded so nothign can be forgotten.


def part_d():
    # Like Part C, but graded against the corrected v2 key: what disagreements are left?
    #   1. Embedding says "quote" (>= 0.85) but v2 says no: paraphrased quotes the text key can't see,
    #      or real embedding false alarms?
    #   2. v2 says "quote" but the embedding scored < 0.85 or matched the wrong chapter:
    #      what kind of copy does the embedding struggle with?
    # Guess: how long is each list, and which side is wrong this time?
    bom_vecs = embed([v['text'] for v in bom])
    bible_vecs = embed([v['text'] for v in bible])
    idx, score = best_bible_match(bom_vecs, bible_vecs)
    v2 = text_key_v2()

    def show(i, note=''):
        print(f'  {score[i]:.3f}  {bom[i]["ref"]:18} -> {bible[idx[i]]["ref"]}{note}')
        print(f'         BoM:   {bom[i]["text"][:100]}')
        print(f'         Bible: {bible[idx[i]]["text"][:100]}')

    false_alarms = [i for i, t in enumerate(v2) if t is None and score[i] >= 0.85]
    print(f'== 1. Embedding >= 0.85 but NOT a quote in v2 ({len(false_alarms)} verses)')
    for i in sorted(false_alarms, key=lambda i: -score[i]):
        show(i)

    misses = [i for i, t in enumerate(v2) if t is not None and (score[i] < 0.85 or chapter(bible[idx[i]]) not in t)]
    print(f'\n== 2. Quote in v2 but the embedding missed it ({len(misses)} verses)')
    for i in sorted(misses, key=lambda i: score[i]):
        wrong = chapter(bible[idx[i]]) not in v2[i]
        show(i, f'  (WRONG chapter, wanted {", ".join(sorted(v2[i]))})' if wrong else '  (right chapter, low score)')


    """
    $ python exp5_hidden_copies.py D
    == 1. Embedding >= 0.85 but NOT a quote in v2 (6 verses)
    0.897  3 Nephi 20:39      -> Isaiah 52:6
            BoM:   Verily, verily, I say unto you, that my people shall know my name; yea, in that day they shall know 
            Bible: Therefore my people shall know my name: therefore they shall know in that day that I am he that doth
    0.885  3 Nephi 27:29      -> Matthew 7:7
            BoM:   Therefore, ask, and ye shall receive; knock, and it shall be opened unto you; for he that asketh, re
            Bible: Ask, and it shall be given you; seek, and ye shall find; knock, and it shall be opened unto you:
    0.875  2 Nephi 26:4       -> Malachi 4:1
            BoM:   Wherefore, all those who are proud, and that do wickedly, the day that cometh shall burn them up, sa
            Bible: For, behold, the day cometh, that shall burn as an oven; and all the proud, yea, and all that do wic
    0.874  2 Nephi 9:51       -> Isaiah 55:2
            BoM:   Wherefore, do not spend money for that which is of no worth, nor your labor for that which cannot sa
            Bible: Wherefore do ye spend money for that which is not bread? and your labour for that which satisfieth n
    0.852  3 Nephi 9:18       -> Revelation 22:13
            BoM:   I am the light and the life of the world. I am Alpha and Omega, the beginning and the end.
            Bible: I am Alpha and Omega, the beginning and the end, the first and the last.
    0.851  3 Nephi 20:23      -> Acts 7:37
            BoM:   Behold, I am he of whom Moses spake, saying: A prophet shall the Lord your God raise up unto you of 
            Bible: This is that Moses, which said unto the children of Israel, A prophet shall the Lord your God raise 

    == 2. Quote in v2 but the embedding missed it (35 verses)
    0.722  3 Nephi 20:35      -> Isaiah 52:10  (right chapter, low score)
            BoM:   The Father hath made bare his holy arm in the eyes of all the nations; and all the ends of the earth
            Bible: The LORD hath made bare his holy arm in the eyes of all the nations; and all the ends of the earth s
    0.725  3 Nephi 12:20      -> Matthew 18:3  (WRONG chapter, wanted Matthew 5)
            BoM:   Therefore come unto me and be ye saved; for verily I say unto you, that except ye shall keep my comm
            Bible: And said, Verily I say unto you, Except ye be converted, and become as little children, ye shall not
    0.732  3 Nephi 20:24      -> Acts 3:24  (right chapter, low score)
            BoM:   Verily I say unto you, yea, and all the prophets from Samuel and those that follow after, as many as
            Bible: Yea, and all the prophets from Samuel and those that follow after, as many as have spoken, have like
    0.738  3 Nephi 24:1       -> Malachi 3:1  (right chapter, low score)
            BoM:   And it came to pass that he commanded them that they should write the words which the Father had giv
            Bible: Behold, I will send my messenger, and he shall prepare the way before me: and the Lord, whom ye seek
    0.749  1 Nephi 21:1       -> Isaiah 49:1  (right chapter, low score)
            BoM:   And again: Hearken, O ye house of Israel, all ye that are broken off and are driven out because of t
            Bible: Listen, O isles, unto me; and hearken, ye people, from far; The LORD hath called me from the womb; f
    0.752  1 Nephi 20:22      -> Isaiah 48:22  (right chapter, low score)
            BoM:   And notwithstanding he hath done all this, and greater also, there is no peace, saith the Lord, unto
            Bible: There is no peace, saith the LORD, unto the wicked.
    0.756  3 Nephi 12:24      -> Matthew 5:24  (right chapter, low score)
            BoM:   Go thy way unto thy brother, and first be reconciled to thy brother, and then come unto me with full
            Bible: Leave there thy gift before the altar, and go thy way; first be reconciled to thy brother, and then 
    0.758  Helaman 14:8       -> John 3:36  (WRONG chapter, wanted Acts 2)
            BoM:   And it shall come to pass that whosoever shall believe on the Son of God, the same shall have everla
            Bible: He that believeth on the Son hath everlasting life: and he that believeth not the Son shall not see 
    0.775  3 Nephi 21:14      -> Micah 5:10  (right chapter, low score)
            BoM:   Yea, wo be unto the Gentiles except they repent; for it shall come to pass in that day, saith the Fa
            Bible: And it shall come to pass in that day, saith the LORD, that I will cut off thy horses out of the mid
    0.778  Helaman 10:7       -> Matthew 16:19  (WRONG chapter, wanted Matthew 18)
            BoM:   Behold, I give unto you power, that whatsoever ye shall seal on earth shall be sealed in heaven; and
            Bible: And I will give unto thee the keys of the kingdom of heaven: and whatsoever thou shalt bind on earth
    0.781  3 Nephi 12:38      -> Matthew 5:38  (right chapter, low score)
            BoM:   And behold, it is written, an eye for an eye, and a tooth for a tooth;
            Bible: Ye have heard that it hath been said, An eye for an eye, and a tooth for a tooth:
    0.787  3 Nephi 12:23      -> Matthew 5:23  (right chapter, low score)
            BoM:   Therefore, if ye shall come unto me, or shall desire to come unto me, and rememberest that thy broth
            Bible: Therefore if thou bring thy gift to the altar, and there rememberest that thy brother hath ought aga
    0.791  3 Nephi 12:35      -> Matthew 5:35  (right chapter, low score)
            BoM:   Nor by the earth, for it is his footstool;
            Bible: Nor by the earth; for it is his footstool: neither by Jerusalem; for it is the city of the great Kin
    0.793  3 Nephi 12:43      -> Matthew 5:43  (right chapter, low score)
            BoM:   And behold it is written also, that thou shalt love thy neighbor and hate thine enemy;
            Bible: Ye have heard that it hath been said, Thou shalt love thy neighbour, and hate thine enemy.
    0.794  3 Nephi 13:13      -> 1 Peter 5:11  (WRONG chapter, wanted Matthew 6)
            BoM:   For thine is the kingdom, and the power, and the glory, forever. Amen.
            Bible: To him be glory and dominion for ever and ever. Amen.
    0.796  3 Nephi 13:25      -> Matthew 6:25  (right chapter, low score)
            BoM:   And now it came to pass that when Jesus had spoken these words he looked upon the twelve whom he had
            Bible: Therefore I say unto you, Take no thought for your life, what ye shall eat, or what ye shall drink; 
    0.796  2 Nephi 13:11      -> Isaiah 3:11  (right chapter, low score)
            BoM:   Wo unto the wicked, for they shall perish; for the reward of their hands shall be upon them!
            Bible: Woe unto the wicked! it shall be ill with him: for the reward of his hands shall be given him.
    0.799  3 Nephi 21:8       -> Isaiah 52:15  (right chapter, low score)
            BoM:   And when that day shall come, it shall come to pass that kings shall shut their mouths; for that whi
            Bible: So shall he sprinkle many nations; the kings shall shut their mouths at him: for that which had not 
    0.803  Mosiah 14:1        -> Isaiah 53:1  (right chapter, low score)
            BoM:   Yea, even doth not Isaiah say: Who hath believed our report, and to whom is the arm of the Lord reve
            Bible: Who hath believed our report? and to whom is the arm of the LORD revealed?
    0.813  3 Nephi 13:12      -> Matthew 6:13  (right chapter, low score)
            BoM:   And lead us not into temptation, but deliver us from evil.
            Bible: And lead us not into temptation, but deliver us from evil: For thine is the kingdom, and the power, 
    0.814  3 Nephi 20:19      -> Micah 4:13  (right chapter, low score)
            BoM:   For I will make my people with whom the Father hath covenanted, yea, I will make thy horn iron, and 
            Bible: Arise and thresh, O daughter of Zion: for I will make thine horn iron, and I will make thy hoofs bra
    0.819  2 Nephi 27:31      -> Isaiah 29:20  (right chapter, low score)
            BoM:   For assuredly as the Lord liveth they shall see that the terrible one is brought to naught, and the 
            Bible: For the terrible one is brought to nought, and the scorner is consumed, and all that watch for iniqu
    0.821  3 Nephi 12:14      -> Matthew 5:14  (right chapter, low score)
            BoM:   Verily, verily, I say unto you, I give unto you to be the light of this people. A city that is set o
            Bible: Ye are the light of the world. A city that is set on an hill cannot be hid.
    0.822  2 Nephi 12:10      -> Isaiah 2:10  (right chapter, low score)
            BoM:   O ye wicked ones, enter into the rock, and hide thee in the dust, for the fear of the Lord and the g
            Bible: Enter into the rock, and hide thee in the dust, for fear of the LORD, and for the glory of his majes
    0.838  1 Nephi 20:15      -> Isaiah 48:15  (right chapter, low score)
            BoM:   Also, saith the Lord; I the Lord, yea, I have spoken; yea, I have called him to declare, I have brou
            Bible: I, even I, have spoken; yea, I have called him: I have brought him, and he shall make his way prospe
    0.839  Moroni 10:11       -> 1 Corinthians 12:9  (right chapter, low score)
            BoM:   And to another, exceedingly great faith; and to another, the gifts of healing by the same Spirit;
            Bible: To another faith by the same Spirit; to another the gifts of healing by the same Spirit;
    0.839  3 Nephi 20:32      -> Isaiah 52:8  (right chapter, low score)
            BoM:   Then shall their watchmen lift up their voice, and with the voice together shall they sing; for they
            Bible: Thy watchmen shall lift up the voice; with the voice together shall they sing: for they shall see ey
    0.842  3 Nephi 13:32      -> Matthew 6:32  (right chapter, low score)
            BoM:   For your heavenly Father knoweth that ye have need of all these things.
            Bible: (For after all these things do the Gentiles seek:) for your heavenly Father knoweth that ye have nee
    0.843  2 Nephi 27:28      -> Isaiah 29:17  (right chapter, low score)
            BoM:   But behold, saith the Lord of Hosts: I will show unto the children of men that it is yet a very litt
            Bible: Is it not yet a very little while, and Lebanon shall be turned into a fruitful field, and the fruitf
    0.845  2 Nephi 12:13      -> Isaiah 2:13  (right chapter, low score)
            BoM:   Yea, and the day of the Lord shall come upon all the cedars of Lebanon, for they are high and lifted
            Bible: And upon all the cedars of Lebanon, that are high and lifted up, and upon all the oaks of Bashan,
    0.845  3 Nephi 12:26      -> Matthew 5:26  (right chapter, low score)
            BoM:   Verily, verily, I say unto thee, thou shalt by no means come out thence until thou hast paid the utt
            Bible: Verily I say unto thee, Thou shalt by no means come out thence, till thou hast paid the uttermost fa
    0.846  2 Nephi 23:15      -> Isaiah 13:15  (right chapter, low score)
            BoM:   Every one that is proud shall be thrust through; yea, and every one that is joined to the wicked sha
            Bible: Every one that is found shall be thrust through; and every one that is joined unto them shall fall b
    0.847  3 Nephi 12:6       -> Matthew 5:6  (right chapter, low score)
            BoM:   And blessed are all they who do hunger and thirst after righteousness, for they shall be filled with
            Bible: Blessed are they which do hunger and thirst after righteousness: for they shall be filled.
    0.849  3 Nephi 12:27      -> Matthew 5:27  (right chapter, low score)
            BoM:   Behold, it is written by them of old time, that thou shalt not commit adultery;
            Bible: Ye have heard that it was said by them of old time, Thou shalt not commit adultery:
    0.849  3 Nephi 12:4       -> Matthew 5:4  (right chapter, low score)
            BoM:   And again, blessed are all they that mourn, for they shall be comforted.
            Bible: Blessed are they that mourn: for they shall be comforted.
    """

PARTS = {'A': part_a, 'B': part_b, 'C': part_c, 'D': part_d}

if __name__ == '__main__':
    PARTS[(sys.argv[1] if len(sys.argv) > 1 else 'A').upper()]()
