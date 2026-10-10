const fs = require('node:fs');
const assert = require('node:assert/strict');
const { createGeometry } = require('./skyroads-geometry.js');
const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const geometry = createGeometry(data.tables);
let checks = 0;
for (const [operation, args, expected] of data.cases) {
  assert.equal(geometry[operation](...args), expected, `${operation} ${args}`);
  checks++;
}
for (const [roadIndex, forward, lateral, height, expectedHit, expectedTunnel] of data.road_cases) {
  const rows = data.roads[roadIndex].rows_as_seven_uint16_le;
  assert.equal(geometry.positionHit(rows, forward, lateral, height), expectedHit, `positionHit ${roadIndex}/${forward}/${lateral}/${height}`);
  assert.equal(geometry.insideTunnel(rows, forward, lateral, height), expectedTunnel, `insideTunnel ${roadIndex}/${forward}/${lateral}/${height}`);
  checks += 2;
}
process.stdout.write(JSON.stringify({ verified: true, cases: checks, roads: data.roads.length }));
