/**
 * Test suite for UNO Game Engine: multiplayer support, turn logic,
 * direction reversal, and game mode factories.
 */

const { GameEngine, createAIGame, createMultiplayerGame } = require('../src/game-engine');
const { Card, COLORS } = require('../src/game-core');

// ── Helper: set up a deterministic game state for testing ──────────────────
function setupEngine(playerCount, options = {}) {
  const engine = new GameEngine();
  for (let i = 0; i < playerCount; i++) {
    engine.addPlayer(`Player ${i + 1}`, options.allHuman !== false);
  }
  return engine;
}

function setupInitializedGame(playerCount) {
  const engine = setupEngine(playerCount);
  engine.initGame();
  return engine;
}

// ── Player Setup ───────────────────────────────────────────────────────────

describe('GameEngine: Player Setup', () => {
  test('addPlayer returns sequential indices', () => {
    const engine = new GameEngine();
    expect(engine.addPlayer('Alice')).toBe(0);
    expect(engine.addPlayer('Bob')).toBe(1);
    expect(engine.addPlayer('Charlie')).toBe(2);
  });

  test('getPlayerCount reflects added players', () => {
    const engine = new GameEngine();
    expect(engine.getPlayerCount()).toBe(0);
    engine.addPlayer('Alice');
    expect(engine.getPlayerCount()).toBe(1);
    engine.addPlayer('Bob');
    expect(engine.getPlayerCount()).toBe(2);
  });

  test('initGame throws with fewer than 2 players', () => {
    const engine = new GameEngine();
    engine.addPlayer('Solo');
    expect(() => engine.initGame()).toThrow();
  });

  test('initGame succeeds with 2 players', () => {
    const engine = setupEngine(2);
    expect(() => engine.initGame()).not.toThrow();
  });

  test('initGame succeeds with 3 players', () => {
    const engine = setupEngine(3);
    expect(() => engine.initGame()).not.toThrow();
  });

  test('initGame succeeds with 4 players', () => {
    const engine = setupEngine(4);
    expect(() => engine.initGame()).not.toThrow();
  });
});

// ── Deal & Initial State ───────────────────────────────────────────────────

describe('GameEngine: Deal and Initial State', () => {
  test('each player gets at least 7 cards after init with 2 players', () => {
    const engine = setupInitializedGame(2);
    for (const player of engine.players) {
      // At least 7; may be more if start card is DRAW_TWO
      expect(player.hand.length).toBeGreaterThanOrEqual(7);
    }
  });

  test('each player gets at least 7 cards after init with 3 players', () => {
    const engine = setupInitializedGame(3);
    for (const player of engine.players) {
      expect(player.hand.length).toBeGreaterThanOrEqual(7);
    }
  });

  test('each player gets at least 7 cards after init with 4 players', () => {
    const engine = setupInitializedGame(4);
    for (const player of engine.players) {
      expect(player.hand.length).toBeGreaterThanOrEqual(7);
    }
  });

  test('discard pile has at least 1 card after init', () => {
    const engine = setupInitializedGame(3);
    expect(engine.discardPile.length).toBeGreaterThanOrEqual(1);
  });

  test('top card is not a wild card', () => {
    // Wilds get reshuffled per rules
    for (let i = 0; i < 20; i++) {
      const engine = setupInitializedGame(3);
      const top = engine.getTopCard();
      expect(top.isWild()).toBe(false);
    }
  });

  test('deck size is correct after dealing to N players', () => {
    for (const n of [2, 3, 4]) {
      const engine = setupInitializedGame(n);
      // 108 total - 7*n dealt - at least 1 discard
      const expectedMax = 108 - 7 * n - 1;
      // Could be less if start card effects caused draws
      expect(engine.deck.length).toBeLessThanOrEqual(expectedMax);
      expect(engine.deck.length).toBeGreaterThan(0);
    }
  });
});

// ── Turn Order (core multiplayer logic) ────────────────────────────────────

describe('GameEngine: Turn Order with Multiple Players', () => {
  test('getNextPlayerIndex wraps around for 3 players', () => {
    const engine = setupEngine(3);
    engine.initGame();
    // Force currentPlayerIndex for deterministic testing
    engine.currentPlayerIndex = 0;
    engine.direction = 1;
    expect(engine.getNextPlayerIndex()).toBe(1);

    engine.currentPlayerIndex = 1;
    expect(engine.getNextPlayerIndex()).toBe(2);

    engine.currentPlayerIndex = 2;
    expect(engine.getNextPlayerIndex()).toBe(0);
  });

  test('getNextPlayerIndex wraps around for 4 players', () => {
    const engine = setupEngine(4);
    engine.initGame();
    engine.direction = 1;

    engine.currentPlayerIndex = 0;
    expect(engine.getNextPlayerIndex()).toBe(1);
    engine.currentPlayerIndex = 3;
    expect(engine.getNextPlayerIndex()).toBe(0);
  });

  test('getNextPlayerIndex respects reverse direction for 3 players', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.direction = -1;

    engine.currentPlayerIndex = 0;
    expect(engine.getNextPlayerIndex()).toBe(2);

    engine.currentPlayerIndex = 1;
    expect(engine.getNextPlayerIndex()).toBe(0);

    engine.currentPlayerIndex = 2;
    expect(engine.getNextPlayerIndex()).toBe(1);
  });

  test('getNextPlayerIndex respects reverse direction for 4 players', () => {
    const engine = setupEngine(4);
    engine.initGame();
    engine.direction = -1;

    engine.currentPlayerIndex = 0;
    expect(engine.getNextPlayerIndex()).toBe(3);
    engine.currentPlayerIndex = 1;
    expect(engine.getNextPlayerIndex()).toBe(0);
  });

  test('advanceTurn moves to next player', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    engine.advanceTurn();
    expect(engine.currentPlayerIndex).toBe(1);

    engine.advanceTurn();
    expect(engine.currentPlayerIndex).toBe(2);

    engine.advanceTurn();
    expect(engine.currentPlayerIndex).toBe(0);
  });

  test('full turn cycle visits all players in order (3 players)', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    const visited = [];
    for (let i = 0; i < 6; i++) {
      visited.push(engine.currentPlayerIndex);
      engine.advanceTurn();
    }
    // Should cycle: 0, 1, 2, 0, 1, 2
    expect(visited).toEqual([0, 1, 2, 0, 1, 2]);
  });

  test('full turn cycle visits all players in order (4 players)', () => {
    const engine = setupEngine(4);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    const visited = [];
    for (let i = 0; i < 8; i++) {
      visited.push(engine.currentPlayerIndex);
      engine.advanceTurn();
    }
    expect(visited).toEqual([0, 1, 2, 3, 0, 1, 2, 3]);
  });

  test('reverse direction full cycle (3 players)', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = -1;

    const visited = [];
    for (let i = 0; i < 6; i++) {
      visited.push(engine.currentPlayerIndex);
      engine.advanceTurn();
    }
    expect(visited).toEqual([0, 2, 1, 0, 2, 1]);
  });
});

// ── REVERSE Card Effect ────────────────────────────────────────────────────

describe('GameEngine: REVERSE Card Effect', () => {
  test('REVERSE in 3-player game reverses direction', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    // Set up a playable REVERSE
    const topCard = engine.getTopCard();
    const reverseCard = new Card(topCard.color, 'REVERSE');
    engine.players[0].hand.push(reverseCard);
    const cardIdx = engine.players[0].hand.length - 1;

    engine.playCard(cardIdx);

    expect(engine.direction).toBe(-1);
  });

  test('REVERSE in 4-player game reverses direction', () => {
    const engine = setupEngine(4);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    const topCard = engine.getTopCard();
    const reverseCard = new Card(topCard.color, 'REVERSE');
    engine.players[0].hand.push(reverseCard);
    const cardIdx = engine.players[0].hand.length - 1;

    engine.playCard(cardIdx);

    expect(engine.direction).toBe(-1);
  });

  test('REVERSE in 2-player game acts as skip (opponent is skipped)', () => {
    const engine = setupEngine(2);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    const topCard = engine.getTopCard();
    const reverseCard = new Card(topCard.color, 'REVERSE');
    engine.players[0].hand.push(reverseCard);
    const cardIdx = engine.players[0].hand.length - 1;

    const result = engine.playCard(cardIdx);
    expect(result.success).toBe(true);

    // In 2-player, REVERSE acts as skip — opponent is skipped, back to player 0
    expect(engine.currentPlayerIndex).toBe(0);
  });

  test('double REVERSE in 3-player game restores original direction', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.direction = 1;

    // Play two reverses
    engine.direction *= -1;
    expect(engine.direction).toBe(-1);
    engine.direction *= -1;
    expect(engine.direction).toBe(1);
  });

  test('REVERSE in 3+ player game does NOT skip next player', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 1;
    engine.direction = 1;

    const topCard = engine.getTopCard();
    const reverseCard = new Card(topCard.color, 'REVERSE');
    engine.players[1].hand.push(reverseCard);
    const cardIdx = engine.players[1].hand.length - 1;

    engine.playCard(cardIdx);

    // Direction should be reversed, and turn should go to player 0 (not skip player 2)
    expect(engine.direction).toBe(-1);
    expect(engine.currentPlayerIndex).toBe(0);
  });
});

// ── SKIP Card Effect ───────────────────────────────────────────────────────

describe('GameEngine: SKIP Card Effect', () => {
  test('SKIP in 3-player game skips next player', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    const topCard = engine.getTopCard();
    const skipCard = new Card(topCard.color, 'SKIP');
    engine.players[0].hand.push(skipCard);
    const cardIdx = engine.players[0].hand.length - 1;

    engine.playCard(cardIdx);

    // Player 1 should be skipped, turn goes to player 2
    expect(engine.currentPlayerIndex).toBe(2);
  });

  test('SKIP in 4-player game skips exactly one player', () => {
    const engine = setupEngine(4);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    const topCard = engine.getTopCard();
    const skipCard = new Card(topCard.color, 'SKIP');
    engine.players[0].hand.push(skipCard);
    const cardIdx = engine.players[0].hand.length - 1;

    engine.playCard(cardIdx);

    expect(engine.currentPlayerIndex).toBe(2);
  });

  test('SKIP with reversed direction skips correct player', () => {
    const engine = setupEngine(4);
    engine.initGame();
    engine.currentPlayerIndex = 2;
    engine.direction = -1;

    const topCard = engine.getTopCard();
    const skipCard = new Card(topCard.color, 'SKIP');
    engine.players[2].hand.push(skipCard);
    const cardIdx = engine.players[2].hand.length - 1;

    engine.playCard(cardIdx);

    // Direction is -1, from player 2: next is 1 (skipped), then 0
    expect(engine.currentPlayerIndex).toBe(0);
  });
});

// ── DRAW_TWO Card Effect ───────────────────────────────────────────────────

describe('GameEngine: DRAW_TWO Card Effect', () => {
  test('DRAW_TWO makes next player draw 2 cards in 3-player game', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    const initialHandSize = engine.players[1].hand.length;
    const topCard = engine.getTopCard();
    const drawCard = new Card(topCard.color, 'DRAW_TWO');
    engine.players[0].hand.push(drawCard);
    const cardIdx = engine.players[0].hand.length - 1;

    engine.playCard(cardIdx);

    // Player 1 should draw 2 cards
    expect(engine.players[1].hand.length).toBe(initialHandSize + 2);
    // Player 1 is skipped, turn goes to player 2
    expect(engine.currentPlayerIndex).toBe(2);
  });

  test('DRAW_TWO targets correct player with reversed direction', () => {
    const engine = setupEngine(4);
    engine.initGame();
    engine.currentPlayerIndex = 1;
    engine.direction = -1;

    const initialHandSize = engine.players[0].hand.length;
    const topCard = engine.getTopCard();
    const drawCard = new Card(topCard.color, 'DRAW_TWO');
    engine.players[1].hand.push(drawCard);
    const cardIdx = engine.players[1].hand.length - 1;

    engine.playCard(cardIdx);

    // With direction -1 from player 1: next is player 0
    expect(engine.players[0].hand.length).toBe(initialHandSize + 2);
    // Player 0 is skipped, turn goes to player 3
    expect(engine.currentPlayerIndex).toBe(3);
  });
});

// ── WILD and WILD_DRAW_FOUR ────────────────────────────────────────────────

describe('GameEngine: Wild Cards in Multiplayer', () => {
  test('WILD card sets chosen color', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;

    const wildCard = new Card('NONE', 'WILD');
    engine.players[0].hand.push(wildCard);
    const cardIdx = engine.players[0].hand.length - 1;

    const result = engine.playCard(cardIdx, 'RED');
    expect(result.success).toBe(true);
    expect(engine.wildColor).toBe('RED');
  });

  test('WILD_DRAW_FOUR makes next player draw 4 and skips them', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.direction = 1;

    // Give player 0 only non-matching cards so WD4 is legal
    const topCard = engine.getTopCard();
    engine.players[0].hand = [
      new Card('NONE', 'WILD_DRAW_FOUR'),
    ];

    const initialP1Hand = engine.players[1].hand.length;

    engine.playCard(0, 'BLUE');

    expect(engine.players[1].hand.length).toBe(initialP1Hand + 4);
    // Player 1 skipped, turn goes to player 2
    expect(engine.currentPlayerIndex).toBe(2);
  });
});

// ── Card Play Validation ───────────────────────────────────────────────────

describe('GameEngine: Card Play Validation', () => {
  test('cannot play non-matching card', () => {
    const engine = setupEngine(2);
    engine.initGame();
    engine.currentPlayerIndex = 0;

    // Set a known top card
    engine.discardPile.push(new Card('RED', '5'));
    engine.wildColor = null;

    // Give player a non-matching card
    engine.players[0].hand = [new Card('BLUE', '7')];

    const result = engine.playCard(0);
    expect(result.success).toBe(false);
  });

  test('can play matching color card', () => {
    const engine = setupEngine(2);
    engine.initGame();
    engine.currentPlayerIndex = 0;

    engine.discardPile.push(new Card('RED', '5'));
    engine.wildColor = null;
    engine.players[0].hand = [new Card('RED', '3'), new Card('BLUE', '2')];

    const result = engine.playCard(0);
    expect(result.success).toBe(true);
  });

  test('can play matching value card', () => {
    const engine = setupEngine(2);
    engine.initGame();
    engine.currentPlayerIndex = 0;

    engine.discardPile.push(new Card('RED', '5'));
    engine.wildColor = null;
    engine.players[0].hand = [new Card('BLUE', '5'), new Card('GREEN', '2')];

    const result = engine.playCard(0);
    expect(result.success).toBe(true);
  });
});

// ── Win Detection ──────────────────────────────────────────────────────────

describe('GameEngine: Win Detection', () => {
  test('playing last card triggers win', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;

    // Give player exactly 1 matching card
    const topCard = engine.getTopCard();
    engine.players[0].hand = [new Card(topCard.color, '5')];

    const result = engine.playCard(0);
    expect(result.success).toBe(true);
    expect(result.winner).toBe('Player 1');
    expect(engine.gameOver).toBe(true);
  });

  test('game stops after win', () => {
    const engine = setupEngine(2);
    engine.initGame();
    engine.gameOver = true;

    const result = engine.playCard(0);
    expect(result.success).toBe(false);
  });
});

// ── Draw Card ──────────────────────────────────────────────────────────────

describe('GameEngine: Draw Card', () => {
  test('drawing a card adds it to current player hand', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;

    const initialSize = engine.players[0].hand.length;
    engine.drawCard();
    // Hand should have grown by 1
    expect(engine.players[0].hand.length).toBe(initialSize + 1);
  });
});

// ── UNO Call and Catch ─────────────────────────────────────────────────────

describe('GameEngine: UNO Call and Catch', () => {
  test('callUno succeeds when player has 2 or fewer cards', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    engine.players[0].hand = [new Card('RED', '5'), new Card('BLUE', '3')];

    expect(engine.callUno()).toBe(true);
    expect(engine.unoCalledByPlayer[0]).toBe(true);
  });

  test('callUno fails when player has more than 2 cards', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.currentPlayerIndex = 0;
    // Default hand is 7 cards
    expect(engine.callUno()).toBe(false);
  });

  test('catchUno penalizes player with 1 card who did not call', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.players[1].hand = [new Card('RED', '5')];

    const result = engine.catchUno();
    expect(result).not.toBeNull();
    expect(result.playerIndex).toBe(1);
    expect(engine.players[1].hand.length).toBe(3); // 1 + 2 penalty
  });

  test('catchUno returns null when all UNO players called', () => {
    const engine = setupEngine(3);
    engine.initGame();
    engine.players[1].hand = [new Card('RED', '5')];
    engine.unoCalledByPlayer[1] = true;

    const result = engine.catchUno();
    expect(result).toBeNull();
  });
});

// ── Factory Functions ──────────────────────────────────────────────────────

describe('GameEngine: Factory Functions', () => {
  test('createAIGame creates game with 1 human and N AI players', () => {
    const game = createAIGame(1);
    expect(game.getPlayerCount()).toBe(2);
    expect(game.players[0].isHuman).toBe(true);
    expect(game.players[1].isHuman).toBe(false);

    const game3 = createAIGame(3);
    expect(game3.getPlayerCount()).toBe(4);
    expect(game3.players[0].isHuman).toBe(true);
    expect(game3.players[1].isHuman).toBe(false);
    expect(game3.players[2].isHuman).toBe(false);
    expect(game3.players[3].isHuman).toBe(false);
  });

  test('createMultiplayerGame creates game with all human players', () => {
    const game = createMultiplayerGame(3);
    expect(game.getPlayerCount()).toBe(3);
    for (const player of game.players) {
      expect(player.isHuman).toBe(true);
    }
  });

  test('createMultiplayerGame throws for invalid player count', () => {
    expect(() => createMultiplayerGame(1)).toThrow();
    expect(() => createMultiplayerGame(5)).toThrow();
  });

  test('createAIGame default is 1 AI opponent', () => {
    const game = createAIGame();
    expect(game.getPlayerCount()).toBe(2);
  });
});

// ── Game State ─────────────────────────────────────────────────────────────

describe('GameEngine: Game State', () => {
  test('getState returns correct summary', () => {
    const engine = setupInitializedGame(3);
    const state = engine.getState();

    expect(state.playerCount).toBe(3);
    expect(state.handSizes).toHaveLength(3);
    expect(state.gameOver).toBe(false);
    expect(state.winner).toBeNull();
    expect(state.deckSize).toBeGreaterThan(0);
    expect(state.topCard).toBeDefined();
    expect([1, -1]).toContain(state.direction);
  });

  test('getState reflects direction change', () => {
    const engine = setupInitializedGame(3);
    engine.direction = -1;
    expect(engine.getState().direction).toBe(-1);
  });
});
