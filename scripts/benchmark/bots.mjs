import { setTimeout as delay } from 'node:timers/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createInterface } from 'node:readline';
import { parseBotArgs } from './lib/bot-options.mjs';
import { movementControls } from './lib/movement.mjs';

function event(type, data = {}) {
  process.stdout.write(`${JSON.stringify({ time: new Date().toISOString(), type, ...data })}\n`);
}

export async function runBots(options, createBot) {
  const bots = [];
  let stopped = false;
  let finishStop;
  const stopRequested = new Promise(resolve => { finishStop = resolve; });
  let failBots;
  const botFailure = new Promise((_, reject) => { failBots = reject; });
  botFailure.catch(() => {});
  const stop = () => {
    if (stopped) return;
    stopped = true;
    for (const bot of bots) {
      try { bot.quit('benchmark complete'); } catch {}
    }
  };
  const onSignal = () => { stop(); finishStop(); };
  process.once('SIGINT', onSignal);
  process.once('SIGTERM', onSignal);
  const stdin = createInterface({ input: process.stdin });
  stdin.on('line', line => {
    if (line.trim() === 'stop') finishStop();
  });

  try {
    const joined = options.count === 0 ? Promise.resolve() : new Promise((resolve, reject) => {
      let joinedCount = 0;
      const timeout = setTimeout(() => reject(new Error('bot join timeout')), 60_000);
      const failJoin = error => {
        clearTimeout(timeout);
        reject(error);
        failBots(error);
      };
      for (let i = 0; i < options.count; i += 1) {
        const bot = createBot({
          host: options.host,
          port: options.port,
          username: `beefbench_${String(i + 1).padStart(3, '0')}`,
          auth: 'offline',
          version: options.clientVersion,
          hideErrors: false,
        });
        bots.push(bot);
        bot.once('login', () => event('login', { username: bot.username, index: i }));
        bot.once('spawn', () => {
          joinedCount += 1;
          event('spawn', { username: bot.username, index: i, joined: joinedCount });
          if (joinedCount === options.count) {
            clearTimeout(timeout);
            resolve();
          }
        });
        bot.on('error', error => failJoin(new Error(`${bot.username}: ${error.message}`)));
        bot.on('end', reason => {
          if (!stopped) failJoin(new Error(`${bot.username} disconnected unexpectedly: ${reason ?? 'unknown reason'}`));
        });
      }
    });

    await joined;
    event('all-spawned', { count: bots.length, version: options.version, clientVersion: options.clientVersion, bridgeRequired: options.bridgeRequired });
    const movementStart = Date.now();
    const directions = ['forward', 'left', 'back', 'right'];
    const movement = setInterval(() => {
      const elapsedMs = Date.now() - movementStart;
      bots.forEach((bot, index) => {
        const controls = movementControls(options.scenario, index, options.seed, elapsedMs);
        for (const direction of directions) bot.setControlState(direction, Boolean(controls[direction]));
        bot.setControlState('sprint', controls.sprint);
      });
    }, 250);
            let durationTimer;
            try {
              if (options.durationSeconds > 0) {
                const durationElapsed = new Promise(resolve => {
                  durationTimer = setTimeout(resolve, options.durationSeconds * 1000);
                });
                await Promise.race([durationElapsed, stopRequested, botFailure]);
              } else {
                await Promise.race([stopRequested, botFailure]);
              }
            } finally {
              clearTimeout(durationTimer);
              clearInterval(movement);
            }
    event('disconnecting', { count: bots.length });
  } finally {
    stop();
    stdin.close();
    process.removeListener('SIGINT', onSignal);
    process.removeListener('SIGTERM', onSignal);
    await delay(500);
  }
}

async function main() {
  try {
    const options = parseBotArgs(process.argv.slice(2));
    const { createBot } = await import('mineflayer');
    await runBots(options, createBot);
    process.exitCode = 0;
  } catch (error) {
    event('failure', { error: error.message });
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) await main();
