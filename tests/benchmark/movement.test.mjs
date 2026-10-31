import test from 'node:test';
import assert from 'node:assert/strict';
import { movementControls } from '../../scripts/benchmark/lib/movement.mjs';

test('steady-world path repeats deterministically and cycles directions', () => {
  assert.deepEqual(movementControls('steady-world', 0, 1, 0), movementControls('steady-world', 0, 1, 0));
  assert.notDeepEqual(movementControls('steady-world', 0, 1, 0), movementControls('steady-world', 0, 1, 15_000));
});

test('exploration path sprints and staggers bots onto distinct phases', () => {
  assert.equal(movementControls('exploration', 0, 42, 0).sprint, true);
  assert.notDeepEqual(movementControls('exploration', 0, 3, 0), movementControls('exploration', 4, 3, 0));
});
