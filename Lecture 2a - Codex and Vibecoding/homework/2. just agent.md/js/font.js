// A 3x5 pixel font, so all text stays crisp at any scale.
var KB = (typeof KB !== 'undefined') ? KB : {};

KB.Font = (function () {
  // Each glyph is five rows of three pixels, top to bottom.
  const ROWS = {
    A: '.#. #.# ### #.# #.#', B: '##. #.# ##. #.# ##.', C: '.## #.. #.. #.. .##', D: '##. #.# #.# #.# ##.',
    E: '### #.. ##. #.. ###', F: '### #.. ##. #.. #..', G: '.## #.. #.# #.# .##', H: '#.# #.# ### #.# #.#',
    I: '### .#. .#. .#. ###', J: '..# ..# ..# #.# .#.', K: '#.# #.# ##. #.# #.#', L: '#.. #.. #.. #.. ###',
    M: '#.# ### ### #.# #.#', N: '##. #.# #.# #.# #.#', O: '.#. #.# #.# #.# .#.', P: '##. #.# ##. #.. #..',
    Q: '.#. #.# #.# ##. .##', R: '##. #.# ##. #.# #.#', S: '.## #.. .#. ..# ##.', T: '### .#. .#. .#. .#.',
    U: '#.# #.# #.# #.# ###', V: '#.# #.# #.# #.# .#.', W: '#.# #.# ### ### #.#', X: '#.# #.# .#. #.# #.#',
    Y: '#.# #.# .#. .#. .#.', Z: '### ..# .#. #.. ###',
    0: '### #.# #.# #.# ###', 1: '.#. ##. .#. .#. ###', 2: '##. ..# .#. #.. ###', 3: '##. ..# .#. ..# ##.',
    4: '#.# #.# ### ..# ..#', 5: '### #.. ##. ..# ##.', 6: '.## #.. ### #.# ###', 7: '### ..# .#. .#. .#.',
    8: '### #.# ### #.# ###', 9: '### #.# ### ..# ##.',
    ' ': '... ... ... ... ...', '.': '... ... ... ... .#.', ',': '... ... ... .#. #..', '!': '.#. .#. .#. ... .#.',
    '?': '##. ..# .#. ... .#.', ':': '... .#. ... .#. ...', '-': '... ... ### ... ...', '+': '... .#. ### .#. ...',
    '/': '..# ..# .#. #.. #..', "'": '.#. .#. ... ... ...', '(': '.#. #.. #.. #.. .#.', ')': '.#. ..# ..# ..# .#.',
    '<': '..# .#. #.. .#. ..#', '>': '#.. .#. ..# .#. #..', '=': '... ### ... ### ...', '*': '... #.# .#. #.# ...',
  };
  const GLYPHS = {};
  Object.keys(ROWS).forEach(k => { GLYPHS[k] = ROWS[k].replace(/ /g, ''); });

  const CW = 4;  // advance per character (3 wide + 1 space)
  const CH = 6;  // line height (5 tall + 1 space)

  function width(text, scale) { return Math.max(0, String(text).length * CW - 1) * (scale || 1); }

  function draw(ctx, text, x, y, color, scale, align) {
    scale = scale || 1;
    text = String(text).toUpperCase();
    if (align === 'center') x -= Math.floor(width(text, scale) / 2);
    else if (align === 'right') x -= width(text, scale);
    x = Math.round(x); y = Math.round(y);
    ctx.fillStyle = color;
    for (let i = 0; i < text.length; i++) {
      const glyph = GLYPHS[text[i]] || GLYPHS['?'];
      for (let p = 0; p < 15; p++) {
        if (glyph[p] === '#') ctx.fillRect(x + (i * CW + p % 3) * scale, y + Math.floor(p / 3) * scale, scale, scale);
      }
    }
  }

  // Text with a 1px dark drop shadow.
  function drawShadowed(ctx, text, x, y, color, scale, align, shadow) {
    const s = scale || 1;
    draw(ctx, text, x + s, y + s, shadow || KB.PAL.ink, s, align);
    draw(ctx, text, x, y, color, s, align);
  }

  // Big text: a 1px dark outline all round plus a deeper drop shadow, like a logo.
  function drawOutlined(ctx, text, x, y, color, scale, align, highlight) {
    const ink = KB.PAL.ink;
    for (let dy = -1; dy <= 2; dy++) {
      for (let dx = -1; dx <= 1; dx++) if (dx || dy) draw(ctx, text, x + dx, y + dy, ink, scale, align);
    }
    draw(ctx, text, x, y, color, scale, align);
    if (highlight) {
      ctx.save();
      ctx.beginPath(); ctx.rect(0, 0, ctx.canvas.width, y + scale); ctx.clip();
      draw(ctx, text, x, y, highlight, scale, align);
      ctx.restore();
    }
  }

  return { draw, drawShadowed, drawOutlined, width, CW, CH };
})();
