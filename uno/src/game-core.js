// Testable game core utilities (no DOM). Exports work in Node (CommonJS) and browser (window.gameCore).
class Card {
  constructor(color, value) {
    this.color = color;
    this.value = value;
  }

  isWild() {
    return this.color === 'wild';
  }

  canPlayOn(topCard, wildColor = null) {
    if (this.isWild()) return true;
    const checkColor = wildColor || topCard.color;
    return this.color === checkColor || this.value === topCard.value;
  }
}

function createDeck() {
  const deck = [];
  const colors = ['red', 'yellow', 'blue', 'green'];
  const values = ['0','1','2','3','4','5','6','7','8','9','skip','reverse','draw2'];

  for (let color of colors) {
    for (let value of values) {
      if (value === '0') {
        deck.push(new Card(color, value));
      } else {
        deck.push(new Card(color, value));
        deck.push(new Card(color, value));
      }
    }
  }

  for (let i = 0; i < 4; i++) {
    deck.push(new Card('wild', 'wild'));
    deck.push(new Card('wild', 'wild_draw'));
  }

  return deck;
}

function shuffleDeck(deck) {
  // In-place Fisher-Yates
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck;
}

function isSpecialCard(card) {
  if (!card) return false;
  const val = card.value || card;
  return ['skip','reverse','draw2','wild','wild_draw'].includes(val);
}

// Exports for Node and browser
const gameCore = { Card, createDeck, shuffleDeck, isSpecialCard };
if (typeof module !== 'undefined' && module.exports) module.exports = gameCore;
if (typeof window !== 'undefined') window.gameCore = gameCore;
