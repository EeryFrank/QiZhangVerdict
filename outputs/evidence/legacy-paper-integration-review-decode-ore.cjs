// Independent read-only decoding of retained synthetic chunk packets; no Minecraft process.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const base = path.resolve(__dirname, '..');
const modules = 'E:/CodexTemp/QiZhangVerdict/legacy-protocol-qa/node_modules';
const chunkPackage = require(path.join(modules, 'prismarine-chunk/package.json'));
const protocolPackage = require(path.join(modules, 'minecraft-protocol/package.json'));
const vecPackage = require(path.join(modules, 'vec3/package.json'));
assert.equal(chunkPackage.version, '1.41.0');
assert.equal(protocolPackage.version, '1.66.2');
const Chunk = require(path.join(modules, 'prismarine-chunk'))('1.16.5');
const { Vec3 } = require(path.join(modules, 'vec3'));
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const results = [];
for (const run of ['paper-1.16.5-grim-ore-01', 'paper-1.16.5-grim-ore-02']) {
  for (const name of ['QVGrimLinked', 'QVGrimMain']) {
    const file = path.join(base, run, `ore-chunk-${name}.json`);
    const bytes = fs.readFileSync(file), packet = JSON.parse(bytes);
    const payload = Buffer.from(packet.base64, 'base64');
    assert.equal(payload.length, packet.bytes); assert.equal(hash(payload), packet.sha256);
    assert.equal(packet.version, '1.16.5'); assert.equal(packet.x, 0); assert.equal(packet.z, 0);
    assert.equal(packet.groundUp, true);
    const chunk = new Chunk(); chunk.load(payload, packet.bitMap, packet.skyLightSent, packet.groundUp);
    const observed = {};
    for (const [label, coords] of Object.entries({hidden:[8,32,8], exposed:[12,32,8], stoneControl:[9,32,8]})) {
      observed[label] = chunk.getBlock(new Vec3(...coords)).name;
    }
    const expected = run.endsWith('-02')
      ? {hidden:'stone', exposed:'diamond_ore', stoneControl:'stone'}
      : {hidden:'air', exposed:'air', stoneControl:'air'};
    assert.deepEqual(observed, expected);
    results.push({run, player:name, file, fileSha256:hash(bytes), payloadSha256:hash(payload),
      payloadBytes:payload.length, bitMap:packet.bitMap, observed,
      interpretation:run.endsWith('-02') ? 'PASS controlled ore wire values independently reproduced'
        : 'Historical fixture failure reproduced: target area is air, not the required controlled stone volume'});
  }
}
const result = {passed:true, scope:'Offline independent decode only; preserves historical failure and final success separately',
  node:process.version, prismarineChunk:chunkPackage.version, minecraftProtocol:protocolPackage.version,
  vec3:vecPackage.version, executedScriptSha256:hash(fs.readFileSync(__filename)), results};
fs.writeFileSync(path.join(__dirname, 'decoded-ore-review.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({passed:true, payloads:results.length, finalSuccessPayloads:2, historicalFailedFixturePayloads:2}));
