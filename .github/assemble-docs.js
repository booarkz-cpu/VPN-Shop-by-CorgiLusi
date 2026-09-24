const fs = require("fs");
const path = require("path");

function assemble(dir, dest) {
  const names = fs.readdirSync(dir).filter((name) => name.startsWith("part-")).sort();
  if (!names.length) throw new Error(`No parts in ${dir}`);
  const body = Buffer.concat(names.map((name) => fs.readFileSync(path.join(dir, name))));
  fs.writeFileSync(dest, body);
}

assemble(".github/readme-src", "README.md");
assemble(".github/security-src", "SECURITY.md");
