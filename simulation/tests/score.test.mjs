import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scoreIncident } from '../src/drone_lab/web/score.mjs';
const fresh = decision => [{decision, age_s: 3}];
test('a camera cannot veto a fresh sensor alarm', () => {
  for(const visible of [true,false]) assert.equal(scoreIncident(fresh('ALARM'),visible).level,3);
});
test('visual-only evidence requests inspection, and stale evidence cannot clear a field', () => {
  assert.equal(scoreIncident(fresh('NO_ALARM'),true).level,2);
  assert.equal(scoreIncident([{decision:'ALARM',age_s:31}]).level,1);
  assert.equal(scoreIncident([]).level,1);
  assert.equal(scoreIncident(fresh('NO_ALARM')).level,0);
});
