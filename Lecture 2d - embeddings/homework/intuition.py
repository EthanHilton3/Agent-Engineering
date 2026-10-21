"""Small experiments for building intuition about embeddings.

Run one at a time:  python intuition.py 1   (or 2, 3, 4, 5)
Before each one, read the comment and write down your guess.
"""
import sys

import numpy as np

from emb import embed, print_matrix, sim


def ex1_grid():
    # Guess first: which pairs score highest? Is 'hola' closer to 'hello' or to 'goodbye'?
    # --- Hi and Hello are probably closest, but since oppsites aren't represent well, they are still close to goodbye too. 
    # --- Hola is probably really close to, sicnce english and spanish are closely related too.
    # Does 'moose' score near 0 against everything?
    # --- moose is probably close to elk, but not close to the other words.

    print_matrix(['hi', 'hello', 'hola', 'goodbye', 'adios', 'moose', 'elk'])
    """
    $ python intuition.py 1 
                            0     1     2     3     4     5     6
    0 hi                    1.00  0.81  0.60  0.37  0.33  0.22  0.26
    1 hello                 0.81  1.00  0.61  0.47  0.39  0.24  0.30
    2 hola                  0.60  0.61  1.00  0.43  0.51  0.22  0.28
    3 goodbye               0.37  0.47  0.43  1.00  0.72  0.22  0.22
    4 adios                 0.33  0.39  0.51  0.72  1.00  0.21  0.22
    5 moose                 0.22  0.24  0.22  0.22  0.21  1.00  0.44
    6 elk                   0.26  0.30  0.28  0.22  0.22  0.44  1.00
    """
    # So i guess opposites are represented better than I thought, 
    # with goodbye and adios being quite unrealted to hello, hi, hola.


def ex2_dial():
    # Change the sentence one step at a time and watch the score.
    # Guess: which single step makes the biggest drop?
    # --- I dont think love and hate will have much difference and since cat and dog are both animals, 
    #       I think the biggest drop will be from "car" to "quarterly earnings beat expectations" since they are completely unrelated.
    base = 'I love my dog'
    steps = [
        'I love my dog',
        'I really love my dog',
        'I love my puppy',
        'I love my cat',
        'I hate my cat',
        'I hate my car',
        'The car needs new tires',
        'Quarterly earnings beat expectations',
    ]
    for s in steps:
        print(f'{sim(base, s):.3f}  {s}')

    """
    $ python intuition.py 2
    0.999  I love my dog
    0.890  I really love my dog
    0.912  I love my puppy
    0.769  I love my cat
    0.522  I hate my cat
    0.395  I hate my car
    0.117  The car needs new tires
    0.103  Quarterly earnings beat expectations
    """
    # Again, I were surprised that love and hate were decently disconnected, the gap from loving cat to hating it is significant, 
    # but since they are both about the same subject (a cat), they are still somewhat related. 
    # Towards the bottom, things that no longer are talking about emotions or dogs just become completely unrelated (so cars and finances)

def ex3_dilution():
    # One sentence that matches the query, buried in more and more unrelated text.
    # Guess: how fast does the score fall? Does it ever reach the 'unrelated' level?
    # --- I think the score will fall quickly and reach the unrelated level after 4 or 5 filler blocks.
    query = 'Nephi built a ship to cross the ocean'
    needle = 'Nephi built a ship to cross the ocean.'
    filler = ('The committee reviewed the budget and approved new parking rules. '
              'Rain is expected later this week. The printer on the third floor is jammed. ')
    for n in [0, 1, 2, 4, 8, 16, 32]:
        text = needle + ' ' + filler * n
        print(f'{sim(query, text):.3f}  needle + {n:>2} filler blocks  ({len(text.split())} words)')
    print(f'{sim(query, filler * 8):.3f}  filler only, no needle')
    """
    $ python intuition.py 3
    0.971  needle +  0 filler blocks  (8 words)
    0.629  needle +  1 filler blocks  (32 words)
    0.590  needle +  2 filler blocks  (56 words)
    0.478  needle +  4 filler blocks  (104 words)
    0.376  needle +  8 filler blocks  (200 words)
    0.301  needle + 16 filler blocks  (392 words)
    0.196  needle + 32 filler blocks  (776 words)
    0.022  filler only, no needle
    """
    # So score does fall quite quickly, going from 0.97 to .63 with just 1 filler block, but the score never goes to complete 0 
    # (whihc i assume means unrealted, im not sure where that threshold is). Choosing the proper chunk size is vital to have good vector searches


def ex4_arithmetic():
    # king - man + woman = ?  Then normalize to length 1 and see what it lands closest to.
    # Guess: does 'queen' actually win? By how much?
    # --- I think queen will win, but I think princess and monarch will be close too.
    words = ['king', 'man', 'woman', 'queen', 'princess', 'monarch', 'girl', 'throne']
    v = dict(zip(words, embed(words)))
    guess = v['king'] - v['man'] + v['woman']
    guess /= np.linalg.norm(guess)
    for w in sorted(words, key=lambda w: -(guess @ v[w])):
        print(f'{guess @ v[w]:.3f}  {w}')
    """
    $ python intuition.py 4
    0.764  king
    0.616  queen
    0.602  woman
    0.465  princess
    0.438  girl
    0.409  throne
    0.400  monarch
    0.192  man
    """
    # lol I should have realised that King would be the closest, but yeah, it makes sense that queen is next and even woman makes sense since that vector was added in
    # I was surprised that princess, girl, throne, and monarch were all fartehr away than I thought, though it does make sens that they are clustered together base donthe equation

def ex5_shared_direction():
    # Two RANDOM arrows of 1536 numbers vs two real (unrelated) embeddings.
    # Guess: which pair scores higher, and why would that be?
    # --- I think the real (albeit unrealted) embedding will score higher since they are still actual words and will have some shared context, 
    #       while the random arrows will be completely unrelated.
    rng = np.random.default_rng(0)
    a, b = rng.normal(size=(2, 1536))
    a /= np.linalg.norm(a)
    b /= np.linalg.norm(b)
    print(f'{a @ b:.3f}  two random arrows')
    for x, y in [('moose', 'thermodynamics'), ('pizza recipe', 'the Treaty of Versailles'),
                 ('qperqoweirupqweor', 'def foo(): return 7')]:
        print(f'{sim(x, y):.3f}  {x!r} vs {y!r}')
    """
    $ python intuition.py 5
    -0.001  two random arrows
    0.145  'moose' vs 'thermodynamics'
    0.020  'pizza recipe' vs 'the Treaty of Versailles'
    0.183  'qperqoweirupqweor' vs 'def foo(): return 7'
    """
    # Its craxy how the random arrows just cancel each other out (showing up as completely unrealted), yet unrealted words, maybe becasue they are actul english words and hopld some semsantic value, re more related
    # also why was the highest score the last one?? IS code that realted to gibberish?? lol

EXPERIMENTS = {'1': ex1_grid, '2': ex2_dial, '3': ex3_dilution, '4': ex4_arithmetic, '5': ex5_shared_direction}

if __name__ == '__main__':
    EXPERIMENTS[sys.argv[1] if len(sys.argv) > 1 else '1']()
