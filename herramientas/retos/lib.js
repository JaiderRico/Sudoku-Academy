// Carga el JS de la app (sin interfaz) dentro de Node para reutilizar el solucionador.
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(process.env.APP_HTML || require('path').join(__dirname, '..', '..', 'app', 'index.html'), 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
let code = m[1];
const cut = code.indexOf("const STORAGE_KEY");
code = code.slice(0, cut);
const ctx = { console, Math, JSON, Int32Array, Set, Map, Array, Object, Number, String };
vm.createContext(ctx);
vm.runInContext(code + `\n;this.API={TECHNIQUE_ORDER,initCandidates,solveAndCount,PEERS,UNITS,countBits,bitsToDigits,VERIFIED_LIBRARY,TECHNIQUE_META};`, ctx);
module.exports = ctx.API;
