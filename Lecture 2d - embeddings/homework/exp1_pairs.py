"""Experiment 1: what does 'similar' mean to an embedding model?

Run: python exp1_pairs.py
Each group is (title, [(a, b), ...]). Before you run it, write down your guess
for which group will score highest and which lowest. Then compare.
"""
from emb import sim

GROUPS = {
    'identical-ish (sanity check)': [
        ('hello', 'hello'),
        ('hello', 'Hello'),
        ('hello', 'hello!!!'),
    ],
    'same meaning, different words (paraphrase)': [
        ('The car is fast', 'The automobile moves quickly'),
        ('I am very happy', 'I feel joyful'),
        ('He passed away', 'He died'),
        ('Faith without works is dead', 'Believing means nothing if you do not act on it'),
    ],
    'same words, different meaning (negation / word sense)': [
        ('I love my dog', 'I do not love my dog'),
        ('I love my dog', 'I hate my dog'),
        ('The bank approved my loan', 'We had a picnic on the river bank'),
        ('The bat flew out of the cave', 'He swung the bat at the ball'),
    ],
    'related topic, different content': [
        ('The cat sat on the mat', 'Dogs are loyal pets'),
        ('baptism', 'repentance'),
        ('baptism', 'thermodynamics'),
        ('Utah', 'Salt Lake City'),
    ],
    'cross-language (spoken)': [
        ('I like cheese', 'Me gusta el queso'),
        ('I like cheese', 'J\'aime le fromage'),
        ('I like cheese', '我喜欢奶酪'),
        ('I like cheese', 'Me gusta el cielo azul'),   # Spanish, but wrong meaning
        ('I like cheese', 'I like the sky'),            # English, wrong meaning
    ],
    'typos': [
        ('The Book of Mormon', 'The Bok of Mormun'),
        ('Jesus Christ', 'Jesuss Chirst'),
        ('Jesus Christ', 'jesus christ'),
        ('Jesus Christ', 'JESUS CHRIST'),
        ('definitely', 'definately'),
    ],
    'abbreviations': [
        ('USA', 'United States of America'),
        ('USA', 'United States'),
        ('LDS', 'Latter-day Saints'),
        ('LDS', 'The Church of Jesus Christ of Latter-day Saints'),
        ('D&C 89', 'Doctrine and Covenants section 89'),
        ('NASA', 'National Aeronautics and Space Administration'),
        ('USA', 'Utah State Aggies'),
    ],
    'programming languages / code': [
        ('def add(a, b): return a + b', 'function add(a, b) { return a + b; }'),
        ('def add(a, b): return a + b', 'a function that adds two numbers'),
        ('def add(a, b): return a + b', 'def sub(a, b): return a - b'),
        ('def add(a, b): return a + b', 'The cat sat on the mat'),
        ('for i in range(10): print(i)', 'for (let i = 0; i < 10; i++) console.log(i)'),
    ],
    'garbage / nonsense': [
        ('hello', 'qperqoweirupqweor'),
        ('hello', '!@#$%^&*()_'),
        ('qperqoweirupqweor', '!@#$%^&*()_'),
        ('moose', 'qperqoweirupqweor'),
    ],
}

for title, pairs in GROUPS.items():
    print(f'\n== {title}')
    scores = []
    for a, b in pairs:
        s = sim(a, b)
        scores.append(s)
        print(f'  {s:5.3f}  {a!r}  <->  {b!r}')
    print(f'  (group mean {sum(scores) / len(scores):.3f})')
