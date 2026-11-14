const A = require('./lib.js');
const { TECHNIQUE_ORDER, initCandidates, PEERS, UNITS, countBits, bitsToDigits } = A;
function place(g, c, i, d) { g[i] = d; c[i] = 0; for (const p of PEERS[i]) c[p] &= ~(1 << d); }
function findSingle(g, c) {
  for (let i = 0; i < 81; i++) if (!g[i] && countBits(c[i]) === 1) return [i, bitsToDigits(c[i])[0]];
  for (const u of UNITS) for (let d = 1; d <= 9; d++) {
    let n = 0, at = -1, done = false;
    for (const x of u.cells) { if (g[x] === d) { done = true; break; } if (!g[x] && (c[x] & (1 << d))) { n++; at = x; } }
    if (!done && n === 1) return [at, d];
  }
  return null;
}
function grade(grid, maxRank, sol, deadline, allowed) {
  const ranks = allowed || [...Array(maxRank + 1).keys()];
  const g = grid.slice(), c = initCandidates(g); const used = new Set();
  for (let it = 0; it < 2000; it++) {
    if (deadline && Date.now() > deadline) return { solved: false, timeout: true, used };
    if (g.every(v => v)) return { solved: true, used };
    const s = findSingle(g, c);
    if (s) { if (sol && sol[s[0]] !== s[1]) return { solved: false, bad: true, used }; place(g, c, s[0], s[1]); continue; }
    let ok = false;
    for (const r of ranks) {
      const st = TECHNIQUE_ORDER[r].fn(g, c);
      if (!st || !st.eliminations || !st.eliminations.length) continue;
      let ch = false;
      for (const e of st.eliminations) if (c[e.cell] & (1 << e.digit)) { if (sol && sol[e.cell] === e.digit) return { solved: false, bad: true, used, by: r }; c[e.cell] &= ~(1 << e.digit); ch = true; }
      if (ch) { used.add(r); ok = true; break; }
    }
    if (!ok) return { solved: false, used };
  }
  return { solved: false, used };
}
module.exports = { grade, A };
