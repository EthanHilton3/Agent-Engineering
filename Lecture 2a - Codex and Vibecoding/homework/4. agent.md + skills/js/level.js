// Level data. A level is a list of sections laid side by side.
// Every section has solid ground at groundRow except in its gaps; then:
//   ceiling: [fromCol, toCol(excl), bottomRow]  stone from the top of the level down to bottomRow (a cave)
//   fill:    [col, row, width, height, char]   rectangle of one character
//   put:     [col, row, string]                 characters left to right; '.' leaves the cell alone
//   signs:   [col, text]                        a sign post standing on the ground
//   wind:    px/tick push (negative = headwind)
// Tiles:    # ground   = stone   - one-way platform   S star block (inhale or spit to break)   ^ spikes
// Things:   P start    C checkpoint   w walker   f flyer   h hopper   g spiky (bobs)   q spiky (patrols)
//           o point star   T tomato (full health)   1 extra life   A arena gate   B boss   W warp star
// Columns and rows are local to the section. Rows run 0 (top) to height-1.
var LEVEL_1 = {
  name: 'Dream Meadows',
  height: 22,
  groundRow: 18,
  sections: [
    {
      name: 'MEADOW', width: 64, gaps: [[28, 31], [60, 64]],
      fill: [[56, 15, 1, 3, 'S']],
      put: [
        [3, 17, 'P'], [9, 17, '###'], [10, 16, '#'], [15, 17, 'w'],
        [18, 14, '-----'], [18, 13, 'o.o.o'], [36, 17, 'w'], [40, 14, '---'], [40, 13, 'ooo'],
        [44, 17, 'w'], [46, 12, 'f'], [51, 17, 'h'], [61, 13, 'oo']
      ],
      signs: [[5, 'SPACE: JUMP'], [25, 'TAP SPACE IN AIR: FLY'], [33, 'HOLD ENTER: INHALE'],
        [47, 'ENTER: SPIT'], [54, 'INHALE BLOCKS!']]
    },
    {
      name: 'CLIFFS', width: 72, gaps: [[4, 10], [18, 26], [36, 42], [52, 62]],
      fill: [[12, 15, 4, 3, '#'], [28, 14, 5, 4, '#'], [44, 16, 4, 2, '#']],
      put: [
        [1, 17, 'C'], [13, 14, 'h'], [30, 13, 'w'], [46, 15, 'w'], [66, 17, 'w'], [69, 17, 'h'],
        [7, 12, 'f'], [21, 11, 'f'], [24, 14, 'f'], [39, 12, 'f'], [55, 11, 'f'], [59, 14, 'f'],
        [22, 13, 'g'], [57, 12, 'g'],
        [5, 13, 'o.o.o'], [19, 10, 'o.o.o.o'], [37, 11, 'o.o.o'], [53, 9, 'o.o.o.o.o'], [40, 2, '1']
      ],
      signs: [[2, 'FLY OVER THE GAPS']]
    },
    {
      name: 'STAR BLOCK FORT', width: 64, gaps: [[44, 47]],
      ceiling: [[8, 61, 10]],
      fill: [[20, 11, 1, 7, 'S'], [36, 11, 2, 7, 'S'], [56, 11, 1, 7, 'S']],
      put: [
        [2, 17, 'C'], [14, 17, 'w'], [17, 17, 'h'], [26, 17, 'h'], [30, 17, 'w'], [32, 18, '^^^'],
        [23, 16, 'ooo'], [40, 13, 'ooo'], [50, 13, 'f'], [52, 15, 'q'], [58, 17, 'h']
      ],
      signs: [[5, 'SPIT STARS AT WALLS'], [42, 'MOUTH FULL? NO FLYING']]
    },
    {
      name: 'THE CLIMB', width: 48,
      ceiling: [[4, 14, 11]],
      fill: [[22, 7, 26, 11, '#']],
      put: [
        [1, 17, 'C'], [7, 17, 'w'], [11, 17, 'h'],
        [19, 16, '---'], [14, 14, '---'], [19, 12, '---'], [14, 10, '---'], [19, 8, '---'],
        [17, 11, 'q'], [17, 3, 'f'],
        [24, 6, 'ooo'], [28, 6, 'w'], [32, 7, '^^'], [38, 6, 'h'], [44, 6, 'C']
      ]
    },
    {
      name: 'WINDY SKY', width: 72, gaps: [[0, 72]], wind: -0.45,
      fill: [[10, 9, 4, 2, '#'], [28, 7, 4, 2, '#'], [46, 10, 4, 2, '#'], [62, 8, 10, 2, '#']],
      put: [
        [4, 8, '---'], [19, 11, '---'], [22, 6, '---'], [37, 9, '---'], [40, 4, '---'], [55, 7, '---'],
        [8, 5, 'f'], [16, 8, 'f'], [22, 3, 'f'], [26, 11, 'f'], [34, 5, 'f'], [43, 8, 'f'], [51, 4, 'f'], [58, 11, 'f'],
        [18, 6, 'g'], [33, 10, 'g'], [38, 1, 'g'], [50, 7, 'g'], [60, 4, 'g'],
        [11, 8, 'h'], [64, 7, 'w'], [68, 7, 'h'], [25, 5, 'ooo'], [45, 3, 'ooo']
      ]
    },
    {
      name: 'GAUNTLET', width: 64, gaps: [[6, 9], [22, 25], [40, 44]],
      ceiling: [[26, 36, 12]],
      fill: [[30, 13, 1, 5, 'S'], [46, 15, 2, 3, '=']],
      put: [
        [2, 17, 'C'], [11, 17, 'h'], [10, 12, 'f'], [12, 13, 'ooooo'], [16, 16, 'q'], [18, 18, '^^'],
        [23, 13, 'f'], [28, 17, 'w'], [33, 17, 'w'], [37, 17, 'h'], [42, 14, 'g'], [42, 11, 'f'],
        [50, 17, 'h'], [52, 13, 'g'], [54, 17, 'w'], [57, 16, 'T'], [61, 17, 'C']
      ],
      signs: [[59, 'BOSS AHEAD!']]
    },
    {
      name: 'GNARLWOOD ARENA', width: 18,
      ceiling: [[0, 18, 4]],
      fill: [[16, 5, 2, 13, '=']],
      put: [[0, 17, 'A'], [4, 13, '---'], [8, 13, '---'], [12, 17, 'B'], [7, 11, 'W']]
    }
  ]
};

var LEVELS = [LEVEL_1];

if (typeof module !== 'undefined') module.exports = { LEVEL_1, LEVELS };
