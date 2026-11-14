const A = require('./lib.js');
const { PEERS, solveAndCount } = A;
function rnd(n){return Math.floor(Math.random()*n);}
function shuf(a){for(let i=a.length-1;i>0;i--){const j=rnd(i+1);[a[i],a[j]]=[a[j],a[i]];}return a;}
function fullGrid(){
  const g=new Array(81).fill(0);
  function bt(i){ if(i===81) return true; if(g[i]) return bt(i+1);
    for(const d of shuf([1,2,3,4,5,6,7,8,9])){ if(PEERS[i].some(p=>g[p]===d)) continue; g[i]=d; if(bt(i+1)) return true; g[i]=0;} return false;}
  bt(0); return g;
}
function makePuzzle(){
  const sol=fullGrid(), g=sol.slice();
  for(const i of shuf([...Array(41).keys()])){
    const j=80-i; const a=g[i], b=g[j]; g[i]=0; g[j]=0;
    if(solveAndCount(g,2).count!==1){g[i]=a; g[j]=b;}
  }
  return {grid:g, sol};
}
module.exports={makePuzzle, shuf, rnd};
