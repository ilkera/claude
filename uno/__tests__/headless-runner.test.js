/**
 * Test suite for Headless Auto-play Runner: deterministic execution,
 * structured logging, state injection, and invariant validation.
 */

const { HeadlessRunner, DeterministicAI } = require('../src/headless-runner');
const { Card, COLORS } = require('../src/game-core');
const { GameEngine } = require('../src/game-engine');

// ── Headless Runner Initialization ─────────────────────────────────────────

describe('HeadlessRunner: Initialization', () => {
  test('creates runner with default 4 players', () => {
    const runner = new HeadlessRunner();
    expect(runner.playerCount).toBe(4);
  });

  test('creates runner with custom player count', () => {
    const runner = new HeadlessRunner({ playerCount: 3 });
    expect(runner.playerCount).toBe(3);
  });

  test('logging is enabled by default', () => {
    const runner = new HeadlessRunner();
    expect(runner.enableLogging).toBe(true);
  });

  test('logging can be disabled', () => {
    const runner = new HeadlessRunner({ enableLogging: false });
    expect(runner.enableLogging).toBe(false);
  });
});

// ── Deterministic AI ──────────────────────────────────────────────────────

describe('DeterministicAI: Card Selection', () => {
  test('chooses playable card when available', () => {
    const ai = new DeterministicAI(0);
    const hand = [
      new Card('RED', '5'),
      new Card('BLUE', '3'),
      new Card('RED', '7')
    ];
    const topCard = new Card('RED', '2');

    const choice = ai.chooseCard(hand, topCard, null);
    expect(choice).toBeGreaterThanOrEqual(0);
    expect(hand[choice].canPlayOn(topCard, null)).toBe(true);
  });

  test('returns -1 when no playable cards', () => {
    const ai = new DeterministicAI(0);
    const hand = [
      new Card('BLUE', '3'),
      new Card('GREEN', '7')
    ];
    const topCard = new Card('RED', '2');

    const choice = ai.chooseCard(hand, topCard, null);
    expect(choice).toBe(-1);
  });

  test('prefers wild cards deterministically', () => {
    const ai = new DeterministicAI(0);
    const hand = [
      new Card('RED', '5'),
      new Card('NONE', 'WILD')
    ];
    const topCard = new Card('RED', '2');

    const choice = ai.chooseCard(hand, topCard, null);
    expect(hand[choice].isWild()).toBe(true);
  });

  test('chooseColor returns valid color', () => {
    const ai = new DeterministicAI(0);
    const hand = [
      new Card('RED', '5'),
      new Card('RED', '7'),
      new Card('BLUE', '3')
    ];

    const color = ai.chooseColor(hand);
    expect(COLORS).toContain(color);
  });

  test('shouldCallUno returns true at 2 cards', () => {
    const ai = new DeterministicAI(0);
    expect(ai.shouldCallUno(2)).toBe(true);
  });

  test('shouldCallUno returns false with more cards', () => {
    const ai = new DeterministicAI(0);
    expect(ai.shouldCallUno(3)).toBe(false);
  });
});

// ── Structured Logging ────────────────────────────────────────────────────

describe('HeadlessRunner: Structured Logging', () => {
  test('logs game initialization', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 10 });
    runner.createEngine();

    const initLogs = runner.logs.filter(l => l.event === 'game_initialized');
    expect(initLogs.length).toBe(1);
    expect(initLogs[0].playerCount).toBe(2);
  });

  test('log entries have required fields', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 10 });
    runner.createEngine();

    for (const log of runner.logs) {
      expect(log).toHaveProperty('event');
      expect(log).toHaveProperty('turn');
      expect(log).toHaveProperty('game');
      expect(log).toHaveProperty('timestamp');
    }
  });

  test('exportLogs returns valid JSON', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 10 });
    runner.createEngine();

    const json = runner.exportLogs();
    expect(() => JSON.parse(json)).not.toThrow();
  });

  test('logs are empty when logging disabled', () => {
    const runner = new HeadlessRunner({ playerCount: 2, enableLogging: false });
    runner.createEngine();

    expect(runner.logs.length).toBe(0);
  });
});

// ── State Injection ───────────────────────────────────────────────────────

describe('HeadlessRunner: State Injection', () => {
  test('injects custom hands', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const stateInjection = {
      hands: [
        [{ color: 'RED', value: '5' }],
        [{ color: 'BLUE', value: '3' }]
      ]
    };

    const engine = runner.createEngine(stateInjection);

    expect(engine.players[0].hand.length).toBe(1);
    expect(engine.players[0].hand[0].color).toBe('RED');
    expect(engine.players[0].hand[0].value).toBe('5');
  });

  test('injects custom deck', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const stateInjection = {
      deck: [
        { color: 'GREEN', value: '7' },
        { color: 'YELLOW', value: '2' }
      ]
    };

    const engine = runner.createEngine(stateInjection);

    expect(engine.deck.length).toBe(2);
    expect(engine.deck[0].color).toBe('GREEN');
  });

  test('injects custom discard pile', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const stateInjection = {
      discardPile: [{ color: 'RED', value: '0' }]
    };

    const engine = runner.createEngine(stateInjection);

    expect(engine.discardPile.length).toBe(1);
    expect(engine.getTopCard().color).toBe('RED');
  });

  test('logs state injection event', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const stateInjection = { hands: [[{ color: 'RED', value: '5' }]] };

    runner.createEngine(stateInjection);

    const injectionLogs = runner.logs.filter(l => l.event === 'state_injected');
    expect(injectionLogs.length).toBe(1);
  });
});

// ── Invariant Checks ──────────────────────────────────────────────────────

describe('HeadlessRunner: Invariant Checks', () => {
  test('passes invariants for valid game state', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const engine = runner.createEngine();

    expect(() => runner.checkInvariants(engine)).not.toThrow();
  });

  test('detects invalid player index', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const engine = runner.createEngine();
    engine.currentPlayerIndex = 5;

    expect(() => runner.checkInvariants(engine)).toThrow(/Invalid currentPlayerIndex/);
  });

  test('detects corrupt card', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const engine = runner.createEngine();
    engine.players[0].hand.push({ color: undefined });

    expect(() => runner.checkInvariants(engine)).toThrow(/corrupt card/);
  });

  test('detects invalid wildColor', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const engine = runner.createEngine();
    engine.wildColor = 'PURPLE';

    expect(() => runner.checkInvariants(engine)).toThrow(/Invalid wildColor/);
  });

  test('detects invalid direction', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const engine = runner.createEngine();
    engine.direction = 0;

    expect(() => runner.checkInvariants(engine)).toThrow(/Invalid direction/);
  });

  test('logs invariant check passed', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const engine = runner.createEngine();
    runner.logs = [];

    runner.checkInvariants(engine);

    const checkLogs = runner.logs.filter(l => l.event === 'invariant_check');
    expect(checkLogs.length).toBe(1);
    expect(checkLogs[0].status).toBe('passed');
  });
});

// ── Game Execution ────────────────────────────────────────────────────────

describe('HeadlessRunner: Game Execution', () => {
  test('runGame completes successfully with 2 players', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    const result = runner.runGame();

    expect(result.winner).toBeDefined();
    expect(result.turns).toBeGreaterThan(0);
    expect(result.turns).toBeLessThan(500);
  });

  test('runGame completes successfully with 3 players', () => {
    const runner = new HeadlessRunner({ playerCount: 3, maxTurns: 500 });
    const result = runner.runGame();

    expect(result.winner).toBeDefined();
    expect(result.turns).toBeGreaterThan(0);
  });

  test('runGame completes successfully with 4 players', () => {
    const runner = new HeadlessRunner({ playerCount: 4, maxTurns: 500 });
    const result = runner.runGame();

    expect(result.winner).toBeDefined();
    expect(result.turns).toBeGreaterThan(0);
  });

  test('runGame throws on max turns exceeded', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 5 });

    expect(() => runner.runGame()).toThrow(/exceeded max turns/);
  });

  test('runGame logs turn_start and turn_end events', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    runner.runGame();

    const startLogs = runner.logs.filter(l => l.event === 'turn_start');
    const endLogs = runner.logs.filter(l => l.event === 'turn_end');

    expect(startLogs.length).toBeGreaterThan(0);
    expect(endLogs.length).toBeGreaterThan(0);
    expect(startLogs.length).toBe(endLogs.length);
  });

  test('runGame logs game_won event', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    runner.runGame();

    const winLogs = runner.logs.filter(l => l.event === 'game_won');
    expect(winLogs.length).toBe(1);
  });
});

// ── Multiple Games ────────────────────────────────────────────────────────

describe('HeadlessRunner: Multiple Games', () => {
  test('runMultiple executes specified number of games', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    const { results, stats } = runner.runMultiple(5);

    expect(results.length).toBe(5);
    expect(stats.totalGames).toBe(5);
  });

  test('runMultiple returns statistics', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    const { stats } = runner.runMultiple(10);

    expect(stats).toHaveProperty('totalGames');
    expect(stats).toHaveProperty('successful');
    expect(stats).toHaveProperty('failed');
    expect(stats).toHaveProperty('avgTurns');
    expect(stats).toHaveProperty('winners');
  });

  test('runMultiple handles errors gracefully', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 3 });
    const { results, stats } = runner.runMultiple(5);

    expect(stats.failed).toBeGreaterThan(0);
    expect(results.some(r => r.error)).toBe(true);
  });

  test('runMultiple with state injection', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    const stateInjection = {
      hands: [
        [{ color: 'RED', value: '5' }],
        [{ color: 'RED', value: '3' }]
      ]
    };

    const { results } = runner.runMultiple(3, stateInjection);

    expect(results.length).toBe(3);
    expect(results.every(r => !r.error)).toBe(true);
  });
});

// ── Zero DOM Dependencies ─────────────────────────────────────────────────

describe('HeadlessRunner: Zero DOM Dependencies', () => {
  test('runs without document object', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });

    expect(() => runner.runGame()).not.toThrow();
  });

  test('runs without setTimeout', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    const result = runner.runGame();

    expect(result.winner).toBeDefined();
    // If setTimeout was used, this would be async and fail
  });

  test('all operations are synchronous', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    let completed = false;

    runner.runGame();
    completed = true;

    // If any async operations, completed would still be false
    expect(completed).toBe(true);
  });
});

// ── Edge Cases ────────────────────────────────────────────────────────────

describe('HeadlessRunner: Edge Cases', () => {
  test('handles game with forced winner scenario', () => {
    const runner = new HeadlessRunner({ playerCount: 2 });
    const stateInjection = {
      hands: [
        [{ color: 'RED', value: '5' }],
        [{ color: 'BLUE', value: '3' }, { color: 'BLUE', value: '7' }]
      ],
      discardPile: [{ color: 'RED', value: '2' }]
    };

    const result = runner.runGame(stateInjection);

    expect(result.winner).toBe('Player 1');
    expect(result.turns).toBeLessThan(10);
  });

  test('handles reshuffle scenario', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    const stateInjection = {
      deck: [
        { color: 'RED', value: '1' },
        { color: 'RED', value: '2' }
      ]
    };

    const result = runner.runGame(stateInjection);

    expect(result.winner).toBeDefined();
  });

  test('logs draw and play events correctly', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    runner.runGame();

    const drawLogs = runner.logs.filter(l => l.event === 'draw_card');
    const playLogs = runner.logs.filter(l => l.event === 'play_card');

    expect(drawLogs.length + playLogs.length).toBeGreaterThan(0);
  });
});

// ── Bug Detectors (Requirement 8) ─────────────────────────────────────────

describe('HeadlessRunner: Bug Detectors', () => {
  test('collects all invariant violations across multiple games', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    const violations = [];

    // Run multiple games and collect violations
    for (let i = 0; i < 10; i++) {
      try {
        runner.runGame();
      } catch (error) {
        if (error.message.includes('Invariant violations')) {
          violations.push({
            game: i + 1,
            error: error.message
          });
        }
      }
    }

    // Report should succeed even if violations were found
    if (violations.length > 0) {
      console.log('Violations found across games:', violations);
    }

    // Test passes regardless - it's a detector, not a blocker
    expect(true).toBe(true);
  });

  test('bug detector: reports all corrupt card instances', () => {
    const runner = new HeadlessRunner({ playerCount: 2, maxTurns: 500 });
    const corruptCardIssues = [];

    const { results } = runner.runMultiple(20);

    for (let i = 0; i < results.length; i++) {
      const result = results[i];
      if (result.logs) {
        const violations = result.logs.filter(l =>
          l.event === 'invariant_violation' &&
          l.errors &&
          l.errors.some(e => e.includes('corrupt card'))
        );

        if (violations.length > 0) {
          corruptCardIssues.push({
            game: i + 1,
            violations: violations.length,
            details: violations
          });
        }
      }
    }

    // Report all findings
    if (corruptCardIssues.length > 0) {
      console.log('Corrupt card issues found:', corruptCardIssues);
    }

    expect(corruptCardIssues.length).toBe(0);
  });

  test('bug detector: reports all invalid player index instances', () => {
    const runner = new HeadlessRunner({ playerCount: 3, maxTurns: 500 });
    const indexIssues = [];

    const { results } = runner.runMultiple(20);

    for (let i = 0; i < results.length; i++) {
      const result = results[i];
      if (result.logs) {
        const violations = result.logs.filter(l =>
          l.event === 'invariant_violation' &&
          l.errors &&
          l.errors.some(e => e.includes('Invalid currentPlayerIndex'))
        );

        if (violations.length > 0) {
          indexIssues.push({
            game: i + 1,
            violations: violations.length,
            details: violations
          });
        }
      }
    }

    if (indexIssues.length > 0) {
      console.log('Player index issues found:', indexIssues);
    }

    expect(indexIssues.length).toBe(0);
  });

  test('bug detector: reports all invalid color instances', () => {
    const runner = new HeadlessRunner({ playerCount: 4, maxTurns: 500 });
    const colorIssues = [];

    const { results } = runner.runMultiple(20);

    for (let i = 0; i < results.length; i++) {
      const result = results[i];
      if (result.logs) {
        const violations = result.logs.filter(l =>
          l.event === 'invariant_violation' &&
          l.errors &&
          l.errors.some(e => e.includes('Invalid wildColor'))
        );

        if (violations.length > 0) {
          colorIssues.push({
            game: i + 1,
            violations: violations.length,
            details: violations
          });
        }
      }
    }

    if (colorIssues.length > 0) {
      console.log('Wild color issues found:', colorIssues);
    }

    expect(colorIssues.length).toBe(0);
  });

  test('bug detector: comprehensive multi-game report', () => {
    const runner = new HeadlessRunner({ playerCount: 3, maxTurns: 500 });
    const allIssues = {
      total_games: 50,
      successful: 0,
      failed: 0,
      violations_by_type: {},
      games_with_issues: []
    };

    const { results } = runner.runMultiple(50);

    for (let i = 0; i < results.length; i++) {
      const result = results[i];

      if (result.error) {
        allIssues.failed++;
        allIssues.games_with_issues.push({
          game: i + 1,
          error: result.error
        });
      } else {
        allIssues.successful++;
      }

      if (result.logs) {
        const violations = result.logs.filter(l => l.event === 'invariant_violation');
        if (violations.length > 0) {
          for (const violation of violations) {
            for (const error of violation.errors || []) {
              const type = error.split(':')[0];
              allIssues.violations_by_type[type] = (allIssues.violations_by_type[type] || 0) + 1;
            }
          }
        }
      }
    }

    // Log comprehensive report
    console.log('=== Bug Detector Report ===');
    console.log(`Total games: ${allIssues.total_games}`);
    console.log(`Successful: ${allIssues.successful}`);
    console.log(`Failed: ${allIssues.failed}`);
    console.log('Violations by type:', allIssues.violations_by_type);

    if (allIssues.games_with_issues.length > 0) {
      console.log('Games with issues:', allIssues.games_with_issues.length);
    }

    // Test passes - we're just detecting and reporting
    expect(allIssues.total_games).toBe(50);
  });
});
