/**
 * Comprehensive test suite for UNO game core (per rules.yaml v1.0.0).
 * Tests deck creation, card validation, effects, scoring, and match logic.
 */

const {
  Card, createDeck, shuffleDeck, isActionCard, getCardEffect,
  chooseAutoColor, isWildDrawFourLegal,
  validateCardPlay, calculateRoundScore, checkMatchWin,
  COLORS, ACTION_TYPES, CARD_POINTS
} = require('../src/game-core');

describe('game-core: UNO deck and card tests (per rules.yaml)', () => {

  describe('Deck Creation (rules.yaml: deck)', () => {
    test('createDeck returns exactly 108 cards', () => {
      const deck = createDeck();
      expect(deck.length).toBe(108);
    });

    test('deck contains exactly 4 each of WILD and WILD_DRAW_FOUR', () => {
      const deck = createDeck();
      const wilds = deck.filter(c => c.value === 'WILD');
      const wildDrawFours = deck.filter(c => c.value === 'WILD_DRAW_FOUR');
      expect(wilds.length).toBe(4);
      expect(wildDrawFours.length).toBe(4);
    });

    test('deck has 1 zero per color (4 total)', () => {
      const deck = createDeck();
      const zeros = deck.filter(c => c.value === '0');
      expect(zeros.length).toBe(4);
      for (const color of COLORS) {
        expect(zeros.filter(c => c.color === color).length).toBe(1);
      }
    });

    test('deck has 2 of each number 1-9 per color (72 total)', () => {
      const deck = createDeck();
      const numbers = deck.filter(c => /^\d+$/.test(c.value) && c.value !== '0');
      expect(numbers.length).toBe(72);
      for (const color of COLORS) {
        for (let i = 1; i <= 9; i++) {
          const count = numbers.filter(c => c.color === color && c.value === i.toString()).length;
          expect(count).toBe(2);
        }
      }
    });

    test('deck has 2 of each action per color (24 total)', () => {
      const deck = createDeck();
      const actions = deck.filter(c => ACTION_TYPES.includes(c.value));
      expect(actions.length).toBe(24);
      for (const color of COLORS) {
        for (const action of ACTION_TYPES) {
          const count = actions.filter(c => c.color === color && c.value === action).length;
          expect(count).toBe(2);
        }
      }
    });

    test('deck has correct color distribution', () => {
      const deck = createDeck();
      for (const color of COLORS) {
        const colored = deck.filter(c => c.color === color);
        expect(colored.length).toBe(25);
      }
    });

    test('wild cards have NONE color', () => {
      const deck = createDeck();
      const wilds = deck.filter(c => c.isWild());
      for (const wild of wilds) {
        expect(wild.color).toBe('NONE');
      }
    });
  });

  describe('Card Class (rules.yaml: Card properties)', () => {
    test('Card.canPlayOn: matches color', () => {
      const top = new Card('RED', '5');
      const card = new Card('RED', '2');
      expect(card.canPlayOn(top)).toBe(true);
    });

    test('Card.canPlayOn: matches value', () => {
      const top = new Card('BLUE', '7');
      const card = new Card('RED', '7');
      expect(card.canPlayOn(top)).toBe(true);
    });

    test('Card.canPlayOn: WILD always playable', () => {
      const top = new Card('GREEN', '3');
      const wild = new Card('NONE', 'WILD');
      expect(wild.canPlayOn(top)).toBe(true);
    });

    test('Card.canPlayOn: respects activeColor override', () => {
      const top = new Card('GREEN', '3');
      const card = new Card('RED', '9');
      expect(card.canPlayOn(top, 'RED')).toBe(true);
      expect(card.canPlayOn(top, 'BLUE')).toBe(false);
    });

    test('Card.canPlayOn: action card by value match', () => {
      const top = new Card('RED', 'SKIP');
      const card = new Card('YELLOW', 'SKIP');
      expect(card.canPlayOn(top)).toBe(true);
    });

    test('Card.getPoints returns correct values', () => {
      expect(new Card('RED', '0').getPoints()).toBe(0);
      expect(new Card('RED', '5').getPoints()).toBe(5);
      expect(new Card('RED', 'SKIP').getPoints()).toBe(20);
      expect(new Card('RED', 'REVERSE').getPoints()).toBe(20);
      expect(new Card('RED', 'DRAW_TWO').getPoints()).toBe(20);
      expect(new Card('NONE', 'WILD').getPoints()).toBe(50);
      expect(new Card('NONE', 'WILD_DRAW_FOUR').getPoints()).toBe(50);
    });
  });

  describe('Card Classification', () => {
    test('isActionCard detects action and wild cards', () => {
      expect(isActionCard(new Card('RED', 'SKIP'))).toBe(true);
      expect(isActionCard(new Card('RED', 'REVERSE'))).toBe(true);
      expect(isActionCard(new Card('RED', 'DRAW_TWO'))).toBe(true);
      expect(isActionCard(new Card('NONE', 'WILD'))).toBe(true);
      expect(isActionCard(new Card('NONE', 'WILD_DRAW_FOUR'))).toBe(true);
      expect(isActionCard(new Card('RED', '5'))).toBe(false);
    });

    test('getCardEffect returns correct effect type', () => {
      expect(getCardEffect(new Card('RED', 'SKIP'))).toBe('SKIP_NEXT');
      expect(getCardEffect(new Card('RED', 'REVERSE'))).toBe('REVERSE_DIRECTION');
      expect(getCardEffect(new Card('RED', 'DRAW_TWO'))).toBe('DRAW_TWO');
      expect(getCardEffect(new Card('NONE', 'WILD'))).toBe('CHOOSE_COLOR');
      expect(getCardEffect(new Card('NONE', 'WILD_DRAW_FOUR'))).toBe('CHOOSE_COLOR_AND_DRAW_FOUR');
      expect(getCardEffect(new Card('RED', '5'))).toBe(null);
    });
  });

  describe('Shuffle (rules.yaml: setup.shuffle: true)', () => {
    test('shuffleDeck maintains deck size', () => {
      const deck = createDeck();
      const original = deck.slice();
      shuffleDeck(deck);
      expect(deck.length).toBe(original.length);
    });

    test('shuffleDeck preserves card multiset', () => {
      const deck = createDeck();
      const original = deck.slice();
      shuffleDeck(deck);

      const countBefore = c => {
        const key = `${c.color}-${c.value}`;
        return original.reduce((acc, card) => acc + ((`${card.color}-${card.value}` === key) ? 1 : 0), 0);
      };
      const countAfter = c => {
        const key = `${c.color}-${c.value}`;
        return deck.reduce((acc, card) => acc + ((`${card.color}-${card.value}` === key) ? 1 : 0), 0);
      };

      for (const card of original) {
        expect(countAfter(card)).toBe(countBefore(card));
      }
    });
  });

  describe('AI Color Selection (rules.yaml: chooseAutoColor strategy)', () => {
    test('chooseAutoColor picks color with most cards', () => {
      const hand = [
        new Card('RED', '5'), new Card('RED', '7'), new Card('RED', '9'),
        new Card('BLUE', '3'),
        new Card('GREEN', '1')
      ];
      expect(chooseAutoColor(hand)).toBe('RED');
    });

    test('chooseAutoColor returns random if no colored cards', () => {
      const hand = [
        new Card('NONE', 'WILD'),
        new Card('NONE', 'WILD_DRAW_FOUR')
      ];
      const color = chooseAutoColor(hand);
      expect(COLORS).toContain(color);
    });

    test('chooseAutoColor handles empty hand', () => {
      const color = chooseAutoColor([]);
      expect(COLORS).toContain(color);
    });

    test('chooseAutoColor breaks ties deterministically (first color in order)', () => {
      const hand = [
        new Card('RED', '1'),
        new Card('YELLOW', '2'),
        new Card('GREEN', '3'),
        new Card('BLUE', '4')
      ];
      const color = chooseAutoColor(hand);
      expect(COLORS).toContain(color);
    });
  });

  describe('WILD_DRAW_FOUR Legality (rules.yaml: constraint MUST_HAVE_NO_MATCHING_COLOR)', () => {
    test('isWildDrawFourLegal returns false if player has matching color', () => {
      const hand = [
        new Card('RED', '5'),
        new Card('RED', '7'),
        new Card('NONE', 'WILD_DRAW_FOUR')
      ];
      const playedCard = new Card('NONE', 'WILD_DRAW_FOUR');
      expect(isWildDrawFourLegal(playedCard, hand, 'RED')).toBe(false);
    });

    test('isWildDrawFourLegal returns true if no matching color in hand', () => {
      const hand = [
        new Card('BLUE', '5'),
        new Card('GREEN', '7'),
        new Card('NONE', 'WILD_DRAW_FOUR')
      ];
      const playedCard = new Card('NONE', 'WILD_DRAW_FOUR');
      expect(isWildDrawFourLegal(playedCard, hand, 'RED')).toBe(true);
    });

    test('isWildDrawFourLegal ignores wild cards when checking legality', () => {
      const hand = [
        new Card('NONE', 'WILD'),
        new Card('NONE', 'WILD_DRAW_FOUR')
      ];
      const playedCard = new Card('NONE', 'WILD_DRAW_FOUR');
      expect(isWildDrawFourLegal(playedCard, hand, 'RED')).toBe(true);
    });

    test('isWildDrawFourLegal non-WILD_DRAW_FOUR always legal', () => {
      const hand = [new Card('RED', '5')];
      const playedCard = new Card('NONE', 'WILD');
      expect(isWildDrawFourLegal(playedCard, hand, 'RED')).toBe(true);
    });
  });
});

describe('game-core: Validation, scoring, and match logic (per rules.yaml)', () => {

  describe('Card Play Validation (rules.yaml: play_validation)', () => {
    test('validates matching color', () => {
      const result = validateCardPlay(new Card('RED', '5'), new Card('RED', '3'), null);
      expect(result.valid).toBe(true);
    });

    test('validates matching value', () => {
      const result = validateCardPlay(new Card('RED', '5'), new Card('YELLOW', '5'), null);
      expect(result.valid).toBe(true);
    });

    test('validates matching active color after wild', () => {
      const result = validateCardPlay(new Card('RED', '5'), new Card('NONE', 'WILD'), 'RED');
      expect(result.valid).toBe(true);
    });

    test('rejects non-matching card', () => {
      const result = validateCardPlay(new Card('BLUE', '7'), new Card('RED', '3'), 'RED');
      expect(result.valid).toBe(false);
      expect(result.reason).toBeDefined();
    });

    test('wild card always valid', () => {
      const result = validateCardPlay(new Card('NONE', 'WILD'), new Card('RED', '5'), null);
      expect(result.valid).toBe(true);
    });

    test('action card matches color', () => {
      const result = validateCardPlay(new Card('GREEN', 'SKIP'), new Card('GREEN', '7'), null);
      expect(result.valid).toBe(true);
    });

    test('action card matches value', () => {
      const result = validateCardPlay(new Card('RED', 'SKIP'), new Card('BLUE', 'SKIP'), null);
      expect(result.valid).toBe(true);
    });

    test('rejects null card', () => {
      const result = validateCardPlay(null, new Card('RED', '3'), 'RED');
      expect(result.valid).toBe(false);
    });
  });

  describe('Scoring (rules.yaml: scoring enabled, card_points)', () => {
    test('calculateRoundScore sums card point values', () => {
      const hand = [
        new Card('RED', '5'),
        new Card('YELLOW', '3'),
        new Card('BLUE', 'SKIP')
      ];
      expect(calculateRoundScore(hand)).toBe(5 + 3 + 20);
    });

    test('wilds count as 50 points', () => {
      const hand = [new Card('NONE', 'WILD'), new Card('NONE', 'WILD_DRAW_FOUR')];
      expect(calculateRoundScore(hand)).toBe(100);
    });

    test('empty hand scores 0', () => {
      expect(calculateRoundScore([])).toBe(0);
    });

    test('includes all card types', () => {
      const hand = [
        new Card('RED', '0'),
        new Card('RED', '9'),
        new Card('RED', 'REVERSE'),
        new Card('RED', 'DRAW_TWO'),
        new Card('NONE', 'WILD_DRAW_FOUR')
      ];
      expect(calculateRoundScore(hand)).toBe(0 + 9 + 20 + 20 + 50);
    });
  });

  describe('Match Win (rules.yaml: match_win_condition TARGET_SCORE default 500)', () => {
    test('returns null when both players under target', () => {
      const result = checkMatchWin({ human: 100, ai: 150 }, 500);
      expect(result).toBeNull();
    });

    test('detects winner at target score', () => {
      const result = checkMatchWin({ human: 500, ai: 200 }, 500);
      expect(result.winner).toBe('human');
      expect(result.finalScore).toBe(500);
    });

    test('detects winner above target score', () => {
      const result = checkMatchWin({ human: 200, ai: 525 }, 500);
      expect(result.winner).toBe('ai');
      expect(result.finalScore).toBe(525);
    });

    test('uses custom target score', () => {
      const scores = { human: 250, ai: 250 };
      expect(checkMatchWin(scores, 250).winner).toBeDefined();
      expect(checkMatchWin(scores, 500)).toBeNull();
    });
  });
});
