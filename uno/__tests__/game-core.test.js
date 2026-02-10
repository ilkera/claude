const { Card, createDeck, shuffleDeck, isSpecialCard } = require('../src/game-core');

describe('game-core basic tests (P0)', () => {
  test('createDeck returns 108 cards', () => {
    const deck = createDeck();
    expect(deck.length).toBe(108);
  });

  test('deck contains four wild and four wild_draw', () => {
    const deck = createDeck();
    const wild = deck.filter(c => c.color === 'wild' && c.value === 'wild');
    const wildDraw = deck.filter(c => c.color === 'wild' && c.value === 'wild_draw');
    expect(wild.length).toBe(4);
    expect(wildDraw.length).toBe(4);
  });

  test('Card.canPlayOn: matches color', () => {
    const top = new Card('red', '5');
    const card = new Card('red', '2');
    expect(card.canPlayOn(top)).toBe(true);
  });

  test('Card.canPlayOn: matches value', () => {
    const top = new Card('blue', '7');
    const card = new Card('red', '7');
    expect(card.canPlayOn(top)).toBe(true);
  });

  test('Card.canPlayOn: wild always playable', () => {
    const top = new Card('green', '3');
    const card = new Card('wild', 'wild');
    expect(card.canPlayOn(top)).toBe(true);
  });

  test('Card.canPlayOn: respects wildColor override', () => {
    const top = new Card('green', '3');
    const card = new Card('red', '9');
    expect(card.canPlayOn(top, 'red')).toBe(true);
    expect(card.canPlayOn(top, 'blue')).toBe(false);
  });

  test('isSpecialCard detects special values', () => {
    expect(isSpecialCard({ value: 'skip' })).toBe(true);
    expect(isSpecialCard({ value: 'reverse' })).toBe(true);
    expect(isSpecialCard({ value: 'draw2' })).toBe(true);
    expect(isSpecialCard({ value: 'wild' })).toBe(true);
    expect(isSpecialCard({ value: 'wild_draw' })).toBe(true);
    expect(isSpecialCard({ value: '5' })).toBe(false);
  });

  test('shuffleDeck keeps same size and same multiset of values', () => {
    const deck = createDeck();
    const copy = deck.slice();
    shuffleDeck(deck);
    expect(deck.length).toBe(copy.length);

    // Check multiset equality by counts of color-value pairs
    const count = d => d.reduce((acc, c) => { const k = `${c.color}-${c.value}`; acc[k] = (acc[k] || 0) + 1; return acc; }, {});
    expect(count(deck)).toEqual(count(copy));
  });
});
