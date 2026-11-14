const {makePuzzle}=require('./gen.js'); const {grade}=require('./grade.js'); const fs=require('fs');
const out=process.argv[2], secs=+process.argv[3]; const found=[]; const end=Date.now()+secs*1000; let n=0;
const NOJ=[0,1,2,3,4], J=[0,1,2,3,4,7];
while(Date.now()<end){ const p=makePuzzle(); n++;
  const a=grade(p.grid,0,p.sol,0,NOJ); if(a.solved) continue;
  const b=grade(p.grid,0,p.sol,0,J); if(b.solved && b.used.has(7)) found.push({grid:p.grid.join(''),solution:p.sol.join(''),clues:p.grid.filter(x=>x).length, sw:grade(p.grid,6,p.sol).solved});
}
fs.writeFileSync(out, JSON.stringify(found)); console.log(out,n,found.length, found.filter(f=>!f.sw).length);
