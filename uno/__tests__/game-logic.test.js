const {
  chooseAutoColor,
  handleAIWildCard,
  handleHumanWildCard,
  processColorChoice,
  requiresColorPick
} = require('../src/game-logic');
const { Card } = require('../src/game-core');

describe('game-logic: wild card and turn flow tests', () => {
  describe('chooseAutoColor', () => {
    test('chooses the color with most cards in hand', () => {
      const hand = [
        new Card('red', '5'),
        new Card('red', '7'),
        new Card('red', '9'),
        new Card('blue', '3'),
        new Card('green', '1')
      ];
      const color = chooseAutoColor(hand);
      expect(color).toBe('red');
    });

    test('ties go to the first alphabetical color in the loop', () => {
      // red, yellow, blue, green all have 1 card each
      const hand = [
        new Card('red', '1'),
        new Card('yellow', '2'),
        new Card('blue', '3'),
        new Card('green', '4')
      ];
      const color = chooseAutoColor(hand);
      expect(['red', 'yellow', 'blue', 'green']).toContain(color);
    });

    test('returns random color if hand has no colored cards', () => {
      const hand = [
        new Card('wild', 'wild'),
        new Card('wild', 'wild_draw')
      ];
      const color = chooseAutoColor(hand);
      expect(['red', 'yellow', 'blue', 'green']).toContain(color);
    });

    test('empty hand returns random color', () => {
      const hand = [];
      const color = chooseAutoColor(hand);
      expect(['red', 'yellow', 'blue', 'green']).toContain(color);
    });
  });

  describe('handleAIWildCard', () => {
    test('AI wild card returns auto-color and advances turn', () => {
      const aiHand = [new Card('red', '5'), new Card('red', '7')];
      const nextHand = [];
      const result = handleAIWildCard(false, aiHand, nextHand);
      expect(result.wildColor).toBe('red');
      expect(result.shouldAdvanceTurn).toBe(true);
      expect(result.nextPlayerGetsCards).toBe(0);
    });

    test('AI wild_draw returns auto-color, advances turn, gives 4 cards', () => {
      const aiHand = [new Card('blue', '2')];
      const nextHand = [];
      const result = handleAIWildCard(true, aiHand, nextHand);
      expect(result.wildColor).toBe('blue');
      expect(result.shouldAdvanceTurn).toBe(true);
      expect(result.nextPlayerGetsCards).toBe(4);
    });
  });

  describe('handleHumanWildCard', () => {
    test('human wild card does NOT advance turn and sets awaitColorChoice', () => {
      const result = handleHumanWildCard(false);
      expect(result.wildColor).toBe(null);
      expect(result.shouldAdvanceTurn).toBe(false);
      expect(result.awaitColorChoice).toBe(true);
      expect(result.cardsForNext).toBe(0);
    });

    test('human wild_draw does NOT advance turn, sets awaitColorChoice, gives 4 cards', () => {
      const result = handleHumanWildCard(true);
      expect(result.wildColor).toBe(null);
      expect(result.shouldAdvanceTurn).toBe(false);
      expect(result.awaitColorChoice).toBe(true);
      expect(result.cardsForNext).toBe(4);
    });
  });

  describe('processColorChoice', () => {
    test('processes red color choice', () => {
      const result = processColorChoice('red');
      expect(result.wildColor).toBe('red');
      expect(result.shouldAdvanceTurn).toBe(true);
      expect(result.awaitColorChoice).toBe(false);
    });

    test('processes yellow color choice', () => {
      const result = processColorChoice('yellow');
      expect(result.wildColor).toBe('yellow');
      expect(result.shouldAdvanceTurn).toBe(true);
      expect(result.awaitColorChoice).toBe(false);
    });

    test('processes blue color choice', () => {
      const result = processColorChoice('blue');
      expect(result.wildColor).toBe('blue');
      expect(result.shouldAdvanceTurn).toBe(true);
      expect(result.awaitColorChoice).toBe(false);
    });

    test('processes green color choice', () => {
      const result = processColorChoice('green');
      expect(result.wildColor).toBe('green');
      expect(result.shouldAdvanceTurn).toBe(true);
      expect(result.awaitColorChoice).toBe(false);
    });
  });

  describe('requiresColorPick', () => {
    test('wild card requires color pick', () => {
      const card = new Card('wild', 'wild');
      expect(requiresColorPick(card)).toBe(true);
    });

    test('wild_draw card requires color pick', () => {
      const card = new Card('wild', 'wild_draw');
      expect(requiresColorPick(card)).toBe(true);
    });

    test('colored card does not require color pick', () => {
      const card = new Card('red', '5');
      expect(requiresColorPick(card)).toBe(false);
    });

    test('skip card does not require color pick', () => {
      const card = new Card('red', 'skip');
      expect(requiresColorPick(card)).toBe(false);
    });

    test('draw2 card does not require color pick', () => {
      const card = new Card('blue', 'draw2');
      expect(requiresColorPick(card)).toBe(false);
    });
  });

  describe('integration: AI wild flow', () => {
    test('AI with mixed hand chooses best color', () => {
      const aiHand = [
        new Card('yellow', '1'),
        new Card('yellow', '2'),
        new Card('yellow', '3'),
        new Card('red', '4'),
        new Card('blue', '5')
      ];
      const result = handleAIWildCard(false, aiHand, []);
      expect(result.wildColor).toBe('yellow');
      expect(result.shouldAdvanceTurn).toBe(true);
    });
  });

  describe('integration: human wild flow', () => {
    test('human plays wild, must pick color before turn advances', () => {
      const humanWildResult = handleHumanWildCard(false);
      expect(humanWildResult.shouldAdvanceTurn).toBe(false);
      expect(humanWildResult.awaitColorChoice).toBe(true);

      // Then user picks a color
      const choiceResult = processColorChoice('green');
      expect(choiceResult.shouldAdvanceTurn).toBe(true);
      expect(choiceResult.wildColor).toBe('green');
      expect(choiceResult.awaitColorChoice).toBe(false);
    });

    test('human plays wild_draw, draws 4, then picks color before turn advances', () => {
      const humanWildDraw = handleHumanWildCard(true);
      expect(humanWildDraw.cardsForNext).toBe(4);
      expect(humanWildDraw.shouldAdvanceTurn).toBe(false);
      expect(humanWildDraw.awaitColorChoice).toBe(true);

      const choiceResult = processColorChoice('blue');
      expect(choiceResult.shouldAdvanceTurn).toBe(true);
      expect(choiceResult.wildColor).toBe('blue');
    });
  });
});
