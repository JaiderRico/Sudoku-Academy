const {makePuzzle}=require('./gen.js'); const {grade,A}=require('./grade.js'); const fs=require('fs');
const out=process.argv[2], secs=+process.argv[3];
const FC=19, ALS=17, BASIC=[...Array(ALS+1).keys()];
const found={}; const end=Date.now()+secs*1000; let n=0;
while(Date.now()<end){
  const p=makePuzzle(); n++;
  const r=grade(p.grid,22,p.sol,Date.now()+8000);
  if(r.bad){ console.error('BAD', p.grid.join('')); continue; }
  const rec={grid:p.grid.join(''),solution:p.sol.join(''),clues:p.grid.filter(x=>x).length};
  if(r.solved && r.used.size){ const h=Math.max(...r.used); (found[h]=found[h]||[]).push(rec); }
  // técnicas posteriores a las cadenas de forzado: básicas + la técnica
  if(r.solved && r.used.size){
    const b=grade(p.grid,0,p.sol,Date.now()+8000,BASIC);
    if(!b.solved && !b.timeout) for(const R of [20,21,22]){
      const w=grade(p.grid,0,p.sol,Date.now()+8000,[...BASIC,R]);
      if(w.solved && w.used.has(R)) (found['x'+R]=found['x'+R]||[]).push(rec);
    }
  }
}
fs.writeFileSync(out, JSON.stringify(found)); console.log(out,n, Object.fromEntries(Object.entries(found).map(([k,v])=>[k,v.length])));
