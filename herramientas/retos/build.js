const fs=require('fs'); const {grade,A}=require('./grade.js');
const T=A.TECHNIQUE_ORDER; const pools={};
const add=(k,arr)=>{ for(const x of arr||[]) (pools[k]=pools[k]||[]).push(x); };
for(const f of ['out1','out2','out3','out4']){ const d=JSON.parse(fs.readFileSync(f+'.json')); for(const [k,v] of Object.entries(d)) add(k,v); }
for(const f of ['j1','j2']) add('7', JSON.parse(fs.readFileSync(f+'.json')));
function ranksFor(R){ if(R===7) return [0,1,2,3,4,7]; if(R>19) return [...Array(18).keys(),R]; return [...Array(R+1).keys()]; }
function shuf(a){a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function variant(b){ const rowMap=[],colMap=[]; for(const x of shuf([0,1,2])) for(const i of shuf([0,1,2])) rowMap.push(x*3+i); for(const x of shuf([0,1,2])) for(const i of shuf([0,1,2])) colMap.push(x*3+i);
  const dm=[0,...shuf([1,2,3,4,5,6,7,8,9])]; const tr=Math.random()<.5; let g='',s='';
  for(let r=0;r<9;r++)for(let c=0;c<9;c++){const rr=rowMap[r],cc=colMap[c];const k=tr?cc*9+rr:rr*9+cc;const gv=+b.g[k];g+=gv?dm[gv]:0;s+=dm[+b.s[k]];} return {g,s}; }
function ok(b,R){ const g=b.g.split('').map(Number), s=b.s.split('').map(Number); const rk=ranksFor(R);
  const below=grade(g,0,s,0,rk.filter(x=>x!==R)); if(below.solved||below.bad) return false;
  const w=grade(g,0,s,0,rk); return w.solved && !w.bad && w.used.has(R); }
const lib={}; const report=[];
T.forEach((t,R)=>{
  const key = R>19 ? 'x'+R : String(R);
  const seen=new Set(); const pool=shuf(pools[key]||[]).filter(x=>!seen.has(x.grid)&&seen.add(x.grid));
  const pick=[];
  for(const x of pool){ if(pick.length>=(R===22?12:8)) break; const b={g:x.grid,s:x.solution}; if(ok(b,R)) pick.push(b); }
  const bases=pick.slice(); let tries=0;
  while(pick.length<12 && bases.length && tries<80){ tries++; const v=variant(bases[tries%bases.length]); if(ok(v,R)) pick.push(v); }
  lib[t.id]=pick; report.push(`${t.id}: ${pick.length} (pool ${pool.length})`);
});
console.log(report.join('\n')); fs.writeFileSync('reto_lib.json', JSON.stringify(lib));
console.log('bytes', fs.statSync('reto_lib.json').size);
