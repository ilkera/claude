/**
 * Game Core: Card and Deck logic for UNO (per rules.yaml v1.0.0)
 * Single source of truth for all card constants, Card class, and deck operations.
 *
 * Deck composition (108 cards):
 * - 4 colors × (1×0 + 2×1-9 + 2×SKIP + 2×REVERSE + 2×DRAW_TWO) = 100 colored cards
 * - 4×WILD + 4×WILD_DRAW_FOUR = 8 wild cards
 */

// ── Constants (single source of truth) ──────────────────────────────────────

const COLORS = ['RED', 'YELLOW', 'GREEN', 'BLUE'];
const NUMBER_VALUES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
const ACTION_TYPES = ['SKIP', 'REVERSE', 'DRAW_TWO'];
const WILD_TYPES = ['WILD', 'WILD_DRAW_FOUR'];
const WILD_COLOR = 'NONE';

const CARD_POINTS = {
  '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
  'SKIP': 20, 'REVERSE': 20, 'DRAW_TWO': 20,
  'WILD': 50, 'WILD_DRAW_FOUR': 50
};

// Display-color mapping for UI layer (lowercase ↔ uppercase)
const DISPLAY_COLORS = {
  RED: 'red', YELLOW: 'yellow', GREEN: 'green', BLUE: 'blue'
};

const toDisplayColor = (logicColor) =>
  logicColor ? (DISPLAY_COLORS[logicColor] || null) : null;

const toLogicColor = (displayColor) => {
  if (!displayColor) return null;
  const entry = Object.entries(DISPLAY_COLORS).find(([, v]) => v === displayColor);
  return entry ? entry[0] : null;
};

/**
 * Card class: Represents a single UNO card.
 * - Number cards: color + numeric value
 * - Action cards: color + action (SKIP, REVERSE, DRAW_TWO)
 * - Wild cards: NONE color + WILD or WILD_DRAW_FOUR
 */
class Card {
  constructor(color, value) {
    this.color = color;
    this.value = value;
  }

  isWild()   { return WILD_TYPES.includes(this.value); }
  isAction() { return ACTION_TYPES.includes(this.value); }
  isNumber() { return NUMBER_VALUES.includes(this.value); }

  /** Playable if: wild, color matches active color, or value matches top card. */
  canPlayOn(topCard, activeColor = null) {
    if (this.isWild()) return true;
    const checkColor = activeColor || topCard.color;
    return this.color === checkColor || this.value === topCard.value;
  }

  getPoints() { return CARD_POINTS[this.value] || 0; }
}

/** Create a standard 108-card UNO deck using centralized constants. */
function createDeck() {
  const deck = [];

  for (const color of COLORS) {
    // Number 0: 1× per color
    deck.push(new Card(color, NUMBER_VALUES[0]));
    // Numbers 1-9: 2× per color
    for (const num of NUMBER_VALUES.slice(1)) {
      deck.push(new Card(color, num), new Card(color, num));
    }
    // Action cards: 2× each per color
    for (const action of ACTION_TYPES) {
      deck.push(new Card(color, action), new Card(color, action));
    }
  }

  // Wild cards: 4× each
  for (const wild of WILD_TYPES) {
    for (let i = 0; i < 4; i++) deck.push(new Card(WILD_COLOR, wild));
  }

  return deck;
}

/** Shuffle deck in-place (Fisher-Yates). */
function shuffleDeck(deck) {
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck;
}

/** Check if a card is a special (action or wild) card. */
function isActionCard(card) {
  if (!card) return false;
  const val = card.value || card;
  return ACTION_TYPES.includes(val) || WILD_TYPES.includes(val);
}

const EFFECT_MAP = {
  'SKIP': 'SKIP_NEXT',
  'REVERSE': 'REVERSE_DIRECTION',
  'DRAW_TWO': 'DRAW_TWO',
  'WILD': 'CHOOSE_COLOR',
  'WILD_DRAW_FOUR': 'CHOOSE_COLOR_AND_DRAW_FOUR'
};

/** Get the effect type of a card (or null for number cards). */
function getCardEffect(card) {
  return card ? (EFFECT_MAP[card.value] || null) : null;
}

/** AI picks the color it holds the most of; random if none. */
function chooseAutoColor(hand) {
  const counts = {};
  for (const c of COLORS) counts[c] = 0;
  for (const card of hand) if (counts[card.color] !== undefined) counts[card.color]++;

  const best = COLORS.reduce((a, b) => counts[a] >= counts[b] ? a : b);
  return counts[best] > 0 ? best : COLORS[Math.floor(Math.random() * COLORS.length)];
}

/** WD4 is legal only if player has no cards matching activeColor. */
function isWildDrawFourLegal(playedCard, playerHand, activeColor) {
  if (playedCard.value !== 'WILD_DRAW_FOUR') return true;
  return !playerHand.some(c => c.color === activeColor && !c.isWild());
}

/**
 * Validate card play attempt (per rules.yaml: play_validation).
 * @param {Card} card - Card to play
 * @param {Card} topCard - Top of discard pile
 * @param {string} activeColor - Current active color
 * @returns {Object} - { valid: boolean, reason?: string }
 */
function validateCardPlay(card, topCard, activeColor) {
  if (!card) {
    return { valid: false, reason: 'No card selected' };
  }
  if (!card.canPlayOn(topCard, activeColor)) {
    return { valid: false, reason: 'Card does not match color or value' };
  }
  return { valid: true };
}

/**
 * Calculate round score (per rules.yaml: scoring.card_points).
 * @param {Card[]} playerHand - Remaining cards in hand
 * @returns {number} - Total points
 */
function calculateRoundScore(playerHand) {
  return playerHand.reduce((total, card) => total + card.getPoints(), 0);
}

/**
 * Check if match is complete (per rules.yaml: match_win_condition TARGET_SCORE default 500).
 * @param {Object} scores - { playerName: score }
 * @param {number} targetScore - Default 500
 * @returns {Object|null} - { winner: string } or null if no winner yet
 */
function checkMatchWin(scores, targetScore = 500) {
  for (const [playerName, score] of Object.entries(scores)) {
    if (score >= targetScore) {
      return { winner: playerName, finalScore: score };
    }
  }
  return null;
}

// ── Exports ──────────────────────────────────────────────────────────────────

const gameCore = {
  // Constants
  COLORS, NUMBER_VALUES, ACTION_TYPES, WILD_TYPES, WILD_COLOR, CARD_POINTS,
  DISPLAY_COLORS, toDisplayColor, toLogicColor,
  // Classes
  Card,
  // Functions
  createDeck, shuffleDeck, isActionCard, getCardEffect,
  chooseAutoColor, isWildDrawFourLegal,
  validateCardPlay, calculateRoundScore, checkMatchWin
};

if (typeof module !== 'undefined' && module.exports) module.exports = gameCore;
if (typeof window !== 'undefined') window.gameCore = gameCore;
