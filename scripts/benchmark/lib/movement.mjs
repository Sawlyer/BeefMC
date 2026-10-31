const DIRECTIONS = ['forward', 'left', 'back', 'right'];

export function movementControls(scenario, botIndex, seed, elapsedMs) {
  const deterministicOffset = (Math.abs(seed) + botIndex * 7) * 1000;
  if (scenario === 'steady-world') {
    const phase = Math.floor((elapsedMs + deterministicOffset) / 15_000);
    return { [DIRECTIONS[phase % DIRECTIONS.length]]: true, sprint: false };
  }
  if (scenario === 'exploration') {
    const phase = (elapsedMs + deterministicOffset) % 66_000;
    const direction = phase < 30_000 || (phase >= 33_000 && phase < 63_000) ? 'forward' : phase < 33_000 ? 'left' : 'right';
    return { [direction]: true, sprint: true };
  }
  throw new Error('Unsupported movement scenario: ' + scenario);
}
