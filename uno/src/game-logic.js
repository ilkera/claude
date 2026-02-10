/**
 * Pure game logic for wild card handling and turn flow.
 * No DOM, no timeouts, no side effects—fully testable.
 */

/**
 * Choose auto color for AI based on card counts in hand.
 * @param {Card[]} hand - Player's hand
 * @returns {string} - Color name: 'red', 'yellow', 'blue', 'green'
 */
function chooseAutoColor(hand) {
  const counts = { red: 0, yellow: 0, blue: 0, green: 0 };
  for (const card of hand) {
    if (counts.hasOwnProperty(card.color)) {
      counts[card.color]++;
    }
  }
  
  let best = null;
  let bestCount = -1;
  for (const color of Object.keys(counts)) {
    if (counts[color] > bestCount) {
      best = color;
      bestCount = counts[color];
    }
  }
  
  if (!best || bestCount === 0) {
    const colors = ['red', 'yellow', 'blue', 'green'];
    return colors[Math.floor(Math.random() * colors.length)];
  }
  return best;
}

/**
 * Handle wild or wild_draw card play for AI.
 * Returns new game state partial (color and turn info).
 * @param {boolean} isWildDraw - true if wild_draw (+4), false if wild
 * @param {Card[]} aiHand - AI player's hand (for auto color selection)
 * @param {Card[]} nextPlayerHand - Next player's hand (for draw count)
 * @returns {Object} - { wildColor: string, shouldAdvanceTurn: boolean, nextPlayerGetsCards: number }
 */
function handleAIWildCard(isWildDraw, aiHand, nextPlayerHand) {
  const wildColor = chooseAutoColor(aiHand);
  const cardsForNext = isWildDraw ? 4 : 0;
  return {
    wildColor,
    shouldAdvanceTurn: true,
    nextPlayerGetsCards: cardsForNext
  };
}

/**
 * Handle wild or wild_draw card play for human.
 * Requires user to choose color; turn does not advance until then.
 * @param {boolean} isWildDraw - true if wild_draw, false if wild
 * @returns {Object} - { wildColor: null, shouldAdvanceTurn: false, awaitColorChoice: true, cardsForNext: number }
 */
function handleHumanWildCard(isWildDraw) {
  const cardsForNext = isWildDraw ? 4 : 0;
  return {
    wildColor: null,
    shouldAdvanceTurn: false,
    awaitColorChoice: true,
    cardsForNext: cardsForNext
  };
}

/**
 * Process human's color choice after playing a wild.
 * @param {string} chosenColor - Color chosen: 'red', 'yellow', 'blue', 'green'
 * @returns {Object} - { wildColor: string, shouldAdvanceTurn: true, awaitColorChoice: false }
 */
function processColorChoice(chosenColor) {
  return {
    wildColor: chosenColor,
    shouldAdvanceTurn: true,
    awaitColorChoice: false
  };
}

/**
 * Check if a card should trigger color selection.
 * @param {Card} card - Card being played
 * @returns {boolean}
 */
function requiresColorPick(card) {
  return card.isWild && (card.value === 'wild' || card.value === 'wild_draw');
}

// Exports for Node and browser
const gameLogic = {
  chooseAutoColor,
  handleAIWildCard,
  handleHumanWildCard,
  processColorChoice,
  requiresColorPick
};

if (typeof module !== 'undefined' && module.exports) module.exports = gameLogic;
if (typeof window !== 'undefined') window.gameLogic = gameLogic;
