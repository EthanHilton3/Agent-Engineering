"""Shared helpers for the 2d embedding experiments.

embed() caches every text it has seen on disk, so re-running an experiment
costs nothing and I can tweak the printing without paying again.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import openai

sys.stdout.reconfigure(encoding='utf-8')  # Windows consoles default to cp1252

MODEL = 'text-embedding-3-small'
CACHE_DIR = Path(__file__).parent / '.cache'
CACHE_DIR.mkdir(exist_ok=True)
client = openai.OpenAI()


def _path(text: str, model: str) -> Path:
    return CACHE_DIR / (hashlib.sha256(f'{model}\n{text}'.encode()).hexdigest() + '.npy')


def _batches(texts: list[str], max_items: int = 256, max_chars: int = 200_000):
    """Group texts so no request goes over the API's per-request token cap (300k)."""
    cur, size = [], 0
    for t in texts:
        if cur and (len(cur) >= max_items or size + len(t) > max_chars):
            yield cur
            cur, size = [], 0
        cur.append(t)
        size += len(t)
    if cur:
        yield cur


def embed(texts: list[str], model: str = MODEL) -> np.ndarray:
    """Return an (n, dim) array of unit-length embeddings, one row per text."""
    missing = sorted({t for t in texts if not _path(t, model).exists()})
    for chunk in _batches(missing):
        resp = client.embeddings.create(model=model, input=chunk)
        for t, item in zip(chunk, resp.data):
            np.save(_path(t, model), np.array(item.embedding, dtype=np.float32))
    return np.stack([np.load(_path(t, model)) for t in texts])


def sim(a: str, b: str) -> float:
    """Cosine similarity of two strings (embeddings are unit length, so it's a dot product)."""
    va, vb = embed([a, b])
    return float(va @ vb)


def sim_matrix(texts: list[str]) -> np.ndarray:
    e = embed(texts)
    return e @ e.T


def print_matrix(texts: list[str], width: int = 22) -> None:
    m = sim_matrix(texts)
    labels = [t[:width] for t in texts]
    print(' ' * (width + 1) + ' '.join(f'{i:>5}' for i in range(len(texts))))
    for i, row in enumerate(m):
        print(f'{i:>2} {labels[i]:<{width - 2}} ' + ' '.join(f'{v:5.2f}' for v in row))


def top_k(query: str, texts: list[str], vecs: np.ndarray, k: int = 5):
    q = embed([query])[0]
    scores = vecs @ q
    order = np.argsort(-scores)[:k]
    return [(float(scores[i]), texts[i]) for i in order]


def load_scriptures(works=('book-of-mormon', 'doctrine-and-covenants', 'pearl-of-great-price')) -> list[dict]:
    """Every verse in the chosen works as {ref, book, chapter, text}.

    Defaults to BoM, D&C, and PoGP. Also available: 'old-testament', 'new-testament'.
    """
    data = Path(__file__).parent / 'data'
    verses = []
    for f in works:
        obj = json.loads((data / f'{f}.json').read_text(encoding='utf8'))
        if 'books' in obj:
            for b in obj['books']:
                for c in b['chapters']:
                    for v in c['verses']:
                        verses.append({'ref': v['reference'], 'book': b['book'], 'chapter': c['chapter'], 'text': v['text']})
        else:  # D&C is sections, not books
            for s in obj['sections']:
                for v in s['verses']:
                    verses.append({'ref': v['reference'], 'book': 'D&C', 'chapter': s['section'], 'text': v['text']})
    return verses
