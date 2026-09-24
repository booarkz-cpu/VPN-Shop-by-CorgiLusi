const fs = require("fs");
const path = require("path");

function assembleBase64(dir, dest) {
  const names = fs.readdirSync(dir).filter((name) => name.startsWith("part-")).sort();
  if (!names.length) throw new Error(`No parts in ${dir}`);
  const body = Buffer.concat(names.map((name) => Buffer.from(fs.readFileSync(path.join(dir, name), "utf8").trim(), "base64")));
  fs.writeFileSync(dest, body);
}

assembleBase64(".github/readme-b64", "README.md");
assembleBase64(".github/security-b64", "SECURITY.md");
