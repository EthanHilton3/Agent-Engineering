Work only inside the current directory. Do not read or modify any files outside it.

Build a pixel-art platformer game that runs in the browser by opening index.html.

Character: a small, round, pink character named Kirby who is surprisingly strong.
He can run, jump, and fly by pressing jump repeatedly while in the air. He can
also inhale: holding the action key pulls in nearby enemies and objects in front
of him. Once he has swallowed something, pressing the action key again spits it
out as a projectile that can defeat other enemies.

Game:
- One side-scrolling level with platforms, gaps, and a clear goal at the end.
- At least two kinds of enemies with different behavior (for example one that
  walks and one that flies).
- Lives, a score, a game-over screen, a win screen, and a way to restart.
- Controls: arrow keys or A/D to move, Space to jump and fly, Enter to inhale and spit.
  Show the controls on screen.

Look and feel:
- Retro pixel-art style with crisp pixels, a limited color palette, and simple
  animations (idle, run, jump, fly, inhale).
- Draw all sprites in code, with no external image files or libraries.
- Movement should feel tight and fun: sensible gravity, a floaty-but-controllable
  fly, and a satisfying inhale.

Make it polished and fun to play.
Show more
Bash List files in current directory
IN
ls -la

OUT
total 8
drwxr-xr-x 1 Ethan 197121    0 Oct  9 16:14 ./
drwxr-xr-x 1 Ethan 197121    0 Oct  9 15:12 ../
-rw-r--r-- 1 Ethan 197121 1312 Oct  9 15:16 kirby_game_prompt.txt
4:36 PM
The directory is empty apart from the prompt, so I'll build the whole game as one index.html file.



Bash Read prompt and check for node/browser for testing
IN
cat kirby_game_prompt.txt; echo; which node; ls "/c/Program Files/Google/Chrome/Application/" 2>/dev/null | head -3; ls "/c/Program Files (x86)/Microsoft/Edge/Application/" 2>/dev/null | head -3

OUT
Work only inside the current directory. Do not read or modify any files outside it.

Build a pixel-art platformer game that runs in the browser by opening index.html.

Character: a small, round, pink character named Kirby who is surprisingly strong.
He can run, jump, and fly by pressing jump repeatedly while in the air. He can
also inhale: holding the action key pulls in nearby enemies and objects in front
of him. Once he has swallowed something, pressing the action key again spits it
out as a projectile that can defeat other enemies.

Game:
- One side-scrolling level with platforms, gaps, and a clear goal at the end.
- At least two kinds of enemies with different behavior (for example one that
  walks and one that flies).
- Lives, a score, a game-over screen, a win screen, and a way to restart.
- Controls: arrow keys or A/D to move, Space to jump and fly, Enter to inhale and spit.
  Show the controls on screen.

Look and feel:
- Retro pixel-art style with crisp pixels, a limited color palette, and simple
  animations (idle, run, jump, fly, inhale).
- Draw all sprites in code, with no external image files or libraries.
- Movement should feel tight and fun: sensible gravity, a floaty-but-controllable
  fly, and a satisfying inhale.

Make it polished and fun to play.

/c/nvm4w/nodejs/node
137.0.7151.120/
SetupMetrics/
chrome.VisualElementsManifest.xml
154.0.4258.62/
155.0.4283.45/
AppxSignature.p7x
4:36 PM
Node and Chrome are available, so I can test it headlessly after writing. Writing the game now.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\index.html
1889 lines
I'll test this now using headless Chrome to check for JS errors and capture screenshots, keeping any test files within this directory and removing them afterward.
Bash Check node version and WebSocket support
IN
node --version; node -e "console.log(typeof WebSocket)"

OUT
v22.23.3
function
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\drive.mjs
78 lines
Bash Run headless Chrome test driver
IN
cd "_test" && node drive.mjs 2>&1 | tail -20

OUT
state {"x":126.15055876489036,"y":145,"st":"normal","hp":5}
after inhale {"x":221.56055876489035,"st":"normal","full":0,"hp":5,"score":300}
parade {"st":"normal","full":0}
final {"gs":"gameover"}
ERRORS: none
4:42 PM
No JS errors. Let me look at the screenshots.



Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\01_title.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\02_start.png
4:43 PM
The title and start screens look right. Two things to fix: the "SCORE" label overlaps its digits, and the small spinning pickup stars come out misshapen at some rotation angles. Checking the rest:



Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\04_inhale.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\07_fly.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\08_gate.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\09_parade.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\12_ride.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\14_clear2.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\15_gameover.png
Main flow works end-to-end, but I spotted issues: the win/hurt sprite arms look like cat ears, pickup stars are misshapen, the SCORE label overlaps its digits, and Kirby flickers out of view during the ride due to invulnerability flicker. Fixing all of these now.
Bash Apply sprite, pickup, HUD, and ride-visibility fixes
IN
cd .. && python - <<'EOF'
import re
p='index.html'
s=open(p,encoding='utf-8').read()
rep=[
("hurt: kirbyArt({ rx: 7.2, ry: 7.2, cy: 21.6, feet: FEET_IDLE, arms: [[8, 17], [24, 17]], eyes: 'x', mouth: 'o' }),",
 "hurt: kirbyArt({ rx: 7.2, ry: 7.2, cy: 21.6, feet: FEET_IDLE, arms: [[7, 19.5], [25, 19.5]], eyes: 'x', mouth: 'o' }),"),
("dead: kirbyArt({ cy: 16, rx: 7.4, ry: 7.4, feet: [[12, 22.6, 3, 1.8], [20, 22.6, 3, 1.8]], arms: [[8, 11], [24, 11]], eyes: 'x', mouth: 'o' }),",
 "dead: kirbyArt({ cy: 16, rx: 7.4, ry: 7.4, feet: [[12, 22.6, 3, 1.8], [20, 22.6, 3, 1.8]], arms: [[7, 13.5], [25, 13.5]], eyes: 'x', mouth: 'o' }),"),
("win: kirbyArt({ feet: FEET_IDLE, arms: [[8.6, 16.5], [23.4, 16.5]], eyes: 'happy', mouth: 'smile' }),",
 "win: kirbyArt({ feet: FEET_IDLE, arms: [[6.6, 18.5], [25.4, 18.5]], eyes: 'happy', mouth: 'smile' }),"),
# coin-spin pickups instead of rotating
("function starArt(size, rot, outline) {\n  return sprite(size, size, g => {\n    const c = size / 2, R = size / 2 - 1.5, r = R * 0.48, pts = [];\n    for (let i = 0; i < 10; i++) {\n      const a = -Math.PI / 2 + rot + i * Math.PI / 5, d = i % 2 ? r : R;\n      pts.push([c + Math.cos(a) * d, c + Math.sin(a) * d]);",
 "function starArt(size, rot, outline, sx = 1) {\n  return sprite(size, size, g => {\n    const c = size / 2, R = size / 2 - 1.5, r = R * 0.48, pts = [];\n    for (let i = 0; i < 10; i++) {\n      const a = -Math.PI / 2 + rot + i * Math.PI / 5, d = i % 2 ? r : R;\n      pts.push([c + Math.cos(a) * d * sx, c + Math.sin(a) * d]);"),
("pstar: [0, 1, 2, 3].map(i => starArt(12, i * Math.PI / 10)),",
 "pstar: [1, 0.7, 0.35, 0.7].map(k => starArt(12, 0, C.gold, k)),"),
# HUD score
("  drawText('SCORE ' + pad(G.score), 316, 2, C.white, 1, { align: 'right' });\n  drawText('SCORE', 264, 2, C.yellow);",
 "  const sx0 = drawText(pad(G.score), 316, 2, C.white, 1, { align: 'right' }) - textW(pad(G.score));\n  drawText('SCORE', sx0 - 4, 2, C.yellow, 1, { align: 'right' });"),
("  if (p.invuln > 0 && p.state !== 'dead' && p.state !== 'hurt' && ((p.invuln >> 2) & 1)) return;",
 "  if (p.invuln > 0 && p.state !== 'dead' && p.state !== 'hurt' && p.state !== 'ride' && ((p.invuln >> 2) & 1)) return;"),
]
for a,b in rep:
    assert s.count(a)==1, a[:60]
    s=s.replace(a,b)
open(p,'w',encoding='utf-8').write(s)
EOF

OUT
(Bash completed with no output)
4:43 PM
Next I'll render a zoomed sprite sheet and run a scripted test of the mechanics: inhale → swallow → spit, mega star, inhaling blocks, and flying the big gap.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\mech.mjs
95 lines
Bash Run mechanics test in headless Chrome
IN
cd _test && node mech.mjs 2>&1 | tail -30

OUT
waddle ents [{"x":222,"y":148,"act":true}]
during inhale {"x":176,"y":145,"st":"normal","full":1,"hp":6,"score":0,"gs":"play"}
after inhale {"x":176,"y":145,"st":"normal","full":1,"hp":6,"score":0,"gs":"play"}
after spit {"x":264,"y":145,"st":"normal","full":0,"hp":6,"score":0,"gs":"play"} waddles left 2
parade pos [2519,2536,2552] {"x":2480,"y":145,"st":"normal","full":0,"hp":6,"score":0,"gs":"play"}
after parade inhale {"x":2480,"y":145,"st":"normal","full":2,"hp":6,"score":0,"gs":"play"}
after mega {"x":2451,"y":145,"st":"normal","full":0,"hp":5,"score":100,"gs":"play"}
after block inhale {"x":1088,"y":129,"st":"normal","full":1,"hp":5,"score":100,"gs":"play"} gate tiles row8: 4,4,4
after block spit {"x":1085,"y":129,"st":"normal","full":0,"hp":5,"score":150,"gs":"play"} gate tiles row8: 0,4,4
walked through gate? {"x":1124,"y":129,"st":"normal","full":0,"hp":5,"score":150,"gs":"play"}
after gap {"x":1083,"y":39,"st":"fly","full":0,"hp":5,"score":450,"gs":"play"}
ERRORS: none
Core mechanics check out, but I found a fairness issue: a stunned waddle gets released right next to Kirby's mouth, causing unavoidable damage. I'll make stunned enemies harmless and widen the gulp window, then check the sprites next.
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\20_sheet.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\22_inhaling.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\26_megastar.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\27_block_pull.png
I'll fix three issues: hide stars inside blocks until they break, revert the squashed spin frames back to a single upright star, and enlarge the inhale mouth for better readability.
Bash Apply pickup, hidden-item, stun, and inhale-mouth fixes
IN
cd .. && python - <<'EOF'
p='index.html'
s=open(p,encoding='utf-8').read()
rep=[
("pstar: [1, 0.7, 0.35, 0.7].map(k => starArt(12, 0, C.gold, k)),", "pstar: starArt(12, 0),"),
("      case 'pstar': ctx.drawImage(SPR.pstar[(G.t >> 3) & 3].r, cx - 6, cy - 6 + bob); break;",
 "      case 'pstar': ctx.drawImage(SPR.pstar.r, cx - 6, cy - 6 + bob); break;"),
# hide pickups buried inside solid tiles (revealed when blocks break)
("    if (G.state === 'title' && e.enemy) continue;\n",
 "    if (G.state === 'title' && e.enemy) continue;\n    if (e.pickup && !e.pulled && isSolid(tileAt(Math.floor((e.x + e.w / 2) / 16), Math.floor((e.y + e.h / 2) / 16)))) continue;\n"),
("    if (e.pickup && e.type === 'pstar' && Math.random() < 0.01) sparks(e.x + 5, e.y + 5, 1, C.white);",
 "    if (e.pickup && e.type === 'pstar' && Math.random() < 0.012 && !isSolid(tileAt(Math.floor((e.x + 5) / 16), Math.floor((e.y + 5) / 16)))) sparks(e.x + 5, e.y + 5, 1, C.white);"),
# stunned enemies are harmless
("    if (p.state === 'slide' && e.kill) { killEnemy(e, 150); continue; }\n    if (p.invuln > 0) continue;",
 "    if (p.state === 'slide' && e.kill) { killEnemy(e, 150); continue; }\n    if (p.invuln > 0 || e.stun > 0) continue;"),
# more forgiving multi-swallow window
("  if (p.gulpT === 0) p.gulpT = 9;", "  if (p.gulpT === 0) p.gulpT = 14;"),
("    const sp = 0.7 + k * k * 4.2 + (p.gulpT > 0 ? 2 : 0);", "    const sp = 0.7 + k * k * 4.2 + (p.gulpT > 0 ? 3.5 : 0);"),
# bigger inhale mouth
("  inhale: [0.55, 0.95, 1.15].map(s => kirbyArt({ rx: 7.8, feet: [[11, 28.6], [21.5, 28.6]], arms: [[8, 21], [23.8, 25]], eyes: 'shut', ex: -4, mouth: 'big', ms: s, cheeks: false })),",
 "  inhale: [0.7, 1.05, 1.25].map(s => kirbyArt({ rx: 7.8, feet: [[11, 28.6], [21.5, 28.6]], arms: [[8, 21], [23.8, 25]], eyes: 'shut', ex: -5, ey: -0.5, mouth: 'big', ms: s, cheeks: false })),"),
("    const s = o.ms || 1, mcx = cx + rx - 3 * s, mcy = cy + 1;\n    g.ell(mcx, mcy, 3.4 * s, 4.4 * s, C.mouth, SKINB);\n    g.ell(mcx - 0.6, mcy + 2.6 * s, 2.6 * s, 1.7 * s, C.tongue, [C.mouth]);",
 "    const s = o.ms || 1, mcx = cx + rx - 2.2, mcy = cy + 1.2;\n    g.ell(mcx, mcy, 3.3 * s, 4.4 * s, C.mouth, SKINB);\n    g.ell(mcx - 0.8, mcy + 2.8 * s, 2.4 * s, 1.6 * s, C.tongue, [C.mouth]);"),
]
for a,b in rep:
    assert s.count(a)==1, a[:70]
    s=s.replace(a,b)
open(p,'w',encoding='utf-8').write(s)
EOF
grep -n "pstar\[" index.html; grep -n "SPR.pstar" index.html

OUT
1600:      case 'pstar': ctx.drawImage(SPR.pstar.r, cx - 6, cy - 6 + bob); break;
Bash Rerun mechanics test with block-inhale isolation
IN
cd _test && python - <<'EOF'
p='mech.mjs'
s=open(p,encoding='utf-8').read()
s=s.replace("...SPR.pstar.map(s=>s.r)","SPR.pstar.r")
s=s.replace("""await ev(`__game.P.x=68*16; __game.P.y=9*16-15; __game.P.face=1; __game.P.invuln=600; __game.P.full=0; __game.P.state='normal';`);""",
"""await ev(`__game.ents.forEach(e=>{if(e.x>55*16&&e.x<75*16&&e.enemy)e.alive=false}); __game.P.x=68*16; __game.P.y=9*16-15; __game.P.face=1; __game.P.invuln=600; __game.P.full=0; __game.P.state='normal';`);""")
open(p,'w',encoding='utf-8').write(s)
EOF
node mech.mjs 2>&1 | tail -15

OUT
waddle ents [{"x":221,"y":148,"act":true}]
during inhale {"x":176,"y":145,"st":"normal","full":1,"hp":6,"score":0,"gs":"play"}
after inhale {"x":176,"y":145,"st":"normal","full":1,"hp":6,"score":0,"gs":"play"}
after spit {"x":264,"y":145,"st":"normal","full":0,"hp":6,"score":0,"gs":"play"} waddles left 2
parade pos [2520,2536,2553] {"x":2480,"y":145,"st":"normal","full":0,"hp":6,"score":0,"gs":"play"}
after parade inhale {"x":2480,"y":145,"st":"normal","full":3,"hp":6,"score":0,"gs":"play"}
after mega {"x":2477,"y":145,"st":"normal","full":0,"hp":6,"score":0,"gs":"play"}
after block inhale {"x":1088,"y":129,"st":"normal","full":2,"hp":6,"score":0,"gs":"play"} gate tiles row8: 0,4,0
after block spit {"x":1085,"y":129,"st":"normal","full":0,"hp":6,"score":0,"gs":"play"} gate tiles row8: 0,4,0
walked through gate? {"x":1124,"y":129,"st":"normal","full":0,"hp":6,"score":0,"gs":"play"}
after gap {"x":1085,"y":38,"st":"fly","full":0,"hp":6,"score":300,"gs":"play"}
ERRORS: none
Found a bug where the big star's 18px hitbox overlaps the floor tile and pops instantly when spawned from grounded Kirby. I'll inset the projectile's hitbox for tile checks to fix it.
Bash Inset projectile tile hitbox and retest
IN
cd .. && python - <<'EOF'
p='index.html'
s=open(p,encoding='utf-8').read()
a="    const l = Math.floor(s.x / 16), r = Math.floor((s.x + s.w - 1) / 16), t0 = Math.floor(s.y / 16), t1 = Math.floor((s.y + s.h - 1) / 16);"
b="    const ins = s.big ? 4 : 2;\n    const l = Math.floor((s.x + ins) / 16), r = Math.floor((s.x + s.w - 1 - ins) / 16), t0 = Math.floor((s.y + ins) / 16), t1 = Math.floor((s.y + s.h - 1 - ins) / 16);"
assert s.count(a)==1
s=s.replace(a,b)
open(p,'w',encoding='utf-8').write(s)
EOF
cd _test && node mech.mjs 2>&1 | grep -E "parade|mega|block|gate|ERR"

OUT
parade pos [2519,2536,2552] {"x":2480,"y":145,"st":"normal","full":0,"hp":6,"score":0,"gs":"play"}
after parade inhale {"x":2480,"y":145,"st":"normal","full":3,"hp":6,"score":0,"gs":"play"}
after mega {"x":2477,"y":145,"st":"normal","full":0,"hp":6,"score":400,"gs":"play"}
after block inhale {"x":1088,"y":129,"st":"normal","full":2,"hp":6,"score":400,"gs":"play"} gate tiles row8: 0,4,0
after block spit {"x":1085,"y":129,"st":"normal","full":0,"hp":6,"score":750,"gs":"play"} gate tiles row8: 0,0,0
walked through gate? {"x":1173,"y":129,"st":"normal","full":0,"hp":6,"score":750,"gs":"play"}
ERRORS: none
The core mechanics now pass the scripted tests—mega star pierces, star-block gate opens, and the gap is flyable. I'll check the final visuals next, then clean up the test files.
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\27_block_pull.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test\shots\20_sheet.png
The block-inhale shot is working correctly—Kirby just isn't visible due to the test's long invulnerability blink. I'll clean up the test files now.
Bash Remove temporary test directory and confirm contents
IN
cd .. && sleep 2; rm -rf _test && ls -la && git status --short . | head

OUT
Exit code 1
rm: cannot remove '_test': Device or resource busy
PowerShell Stop leftover headless test Chrome and delete test folder
IN
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -like '*1.2 one shot-v2*_test*profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -Confirm:$false }; Start-Sleep -Milliseconds 800; Remove-Item -Recurse -Force "C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2\_test"; Get-ChildItem "C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.2 one shot-v2" | Select-Object Name, Length

OUT
Remove-Item : Cannot remove the item at 'C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and 
Vibecoding\homework\1.2 one shot-v2\_test' because it is in use.
At line:1 char:540
+ ... econds 800; Remove-Item -Recurse -Force "C:\Users\ethan\Documents\Git ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : InvalidOperation: (:) [Remove-Item], PSInvalidOperationException
    + FullyQualifiedErrorId : InvalidOperation,Microsoft.PowerShell.Commands.RemoveItemCommand
 

Name                  Length
----                  ------
_test                       
index.html            90844 
kirby_game_prompt.txt 1312
4:46 PM
The folder is still in use, probably because the Bash shell's working directory is inside it. I'll move the shell out and try again.



Bash Move shell out of test folder and delete it
IN
cd "/c/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/1.2 one shot-v2" && rm -rf _test; ls -la

OUT
rm: cannot remove '_test': Device or resource busy
total 104
drwxr-xr-x 1 Ethan 197121     0 Oct  9 16:42 ./
drwxr-xr-x 1 Ethan 197121     0 Oct  9 16:34 ../
drwxr-xr-x 1 Ethan 197121     0 Oct  9 16:46 _test/
-rw-r--r-- 1 Ethan 197121 90844 Oct  9 16:46 index.html
-rw-r--r-- 1 Ethan 197121  1312 Oct  9 15:16 kirby_game_prompt.txt
Bash Inspect and retry deleting the empty test folder
IN
cd "/c/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/1.2 one shot-v2" && find _test | head; rm -rf _test && echo removed; ls

OUT
_test
removed
index.html
kirby_game_prompt.txt
4:47 PM
I've built the game as a single file, index.html. Open it in a browser and press Enter to start. It draws all its art and sound in code, with no image files or libraries.

What's in it

Kirby's moves: run, jump with a flip at the top, and fly by tapping Space in the air (holding Space keeps him flapping slowly). Enter while flying exhales a puff of air that defeats enemies.
Inhale and spit: holding Enter pulls enemies and pickups into his mouth, with wind streaks and a whooshing sound. "Surprisingly strong" shows up as Kirby inhaling solid star blocks: they shake loose and fly in. Pressing Enter again spits a star that defeats enemies and breaks blocks. Swallowing two or more things at once makes a bigger "mega star" that goes through several enemies. Down swallows what's in his mouth for points.
The level: one stage, "Puffy Plains", ending at a Warp Star that Kirby rides off-screen. On the way there are gaps, one-way platforms, a spike pit, floating islands, a wall of star blocks you have to break through, and two checkpoints. Signposts teach each move as you reach it.
Enemies:
a walker that turns around at ledges
a flyer that either moves in a wave or hovers back and forth
a hopper that jumps toward Kirby
a spiked ball that can't be inhaled
Lives, score and screens: a 6-point health bar, 3 lives, star pickups, a tomato that restores full health, and a 1-up. There's a title screen, pause (P), game over and a stage-clear tally with time and lives bonuses. Enter or R restarts. The high score is saved in the browser.
Look and sound: a fixed colour palette and a 320×218 canvas scaled up in whole steps so pixels stay sharp, with scrolling background layers and screen shake. Sound effects and an original background tune are generated in code; M mutes.
Controls on screen: the controls are listed on the title screen, in a strip along the bottom of the screen while you play, and on the pause screen.
I added a few extra keys: Up, W or Z also jump, X also inhales/spits, and Down+Space does a slide kick.

Testing: I played it through scripts in headless Chrome. There were no JavaScript errors, and these all worked:

the full sequence of title, play, ride, stage clear, and game over to restart
inhale, swallow and spit
swallowing three enemies at once
breaking through the star-block wall
flying across the big gap
Testing turned up a few bugs that I fixed:

Mega star: it popped the moment it spawned because it touched the floor.
Hidden pickups: stars buried inside blocks were drawn on top of them.
Unavoidable hit: an enemy let go mid-inhale could hurt Kirby straight away.
I couldn't hear the audio in headless Chrome, so sound is unchecked. How the movement feels was judged only from the numbers and screenshots, not real play, so gravity and fly speed may need tuning after you try it. I deleted the temporary test files, so only index.html was added to the folder.