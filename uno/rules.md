# UNO Game Rules and Architecture

## Game Rules

### Deck Composition (108 cards)

| Card Type         | Per Color | Colors | Total |
|-------------------|-----------|--------|-------|
| Number 0          | 1         | 4      | 4     |
| Numbers 1-9       | 2 each    | 4      | 72    |
| SKIP              | 2         | 4      | 8     |
| REVERSE           | 2         | 4      | 8     |
| DRAW TWO          | 2         | 4      | 8     |
| WILD              | -         | -      | 4     |
| WILD DRAW FOUR    | -         | -      | 4     |

Colors: RED, YELLOW, GREEN, BLUE. Wild cards have no color (stored as `NONE`).

### Setup

1. Deck is created (108 cards) and shuffled (Fisher-Yates algorithm).
2. Each player is dealt 7 cards.
3. Top card from the deck is placed face-up as the first discard.
4. If the start card is a special card, its effect applies immediately:
   - **Number card**: Normal start, no effect.
   - **SKIP**: Player 1 is skipped; AI goes first.
   - **REVERSE**: In 2-player mode, acts as SKIP (Player 1 skipped). In multiplayer, reverses direction.
   - **DRAW TWO**: Player 1 draws 2 cards and is skipped.
   - **WILD / WILD DRAW FOUR**: Card is returned to the deck, deck is reshuffled, and a new start card is drawn. Repeats until a non-wild card appears.

### Playing a Card

A card can be played if any of the following are true:
- It is a **WILD** or **WILD DRAW FOUR** (always playable, with constraints for WD4).
- Its **color** matches the active color (top card color, or chosen color after a wild).
- Its **value** matches the top card's value.

If a player cannot play, they must draw a card. If the drawn card is playable, they may play it immediately; otherwise their turn ends.

### Card Effects

| Card             | Effect                                                       |
|------------------|--------------------------------------------------------------|
| SKIP             | Next player's turn is skipped.                               |
| REVERSE          | Reverses play direction. In 2-player mode, acts as SKIP.     |
| DRAW TWO         | Next player draws 2 cards and their turn is skipped.         |
| WILD             | Player chooses the active color. Human gets a color picker; AI auto-selects. |
| WILD DRAW FOUR   | Player chooses color. Next player draws 4 and is skipped. Subject to challenge rules. |

### Wild Draw Four Rules

- **Legality constraint**: A player may only play WILD DRAW FOUR if they have no cards matching the current active color (wild cards in hand are ignored for this check).
- **Human enforcement**: Humans are blocked from playing an illegal WD4.
- **AI behavior**: AI may play WD4 illegally; legality is tracked for challenge resolution.

### Challenge System

When a WILD DRAW FOUR is played, the opponent may challenge it:

- **If the play was illegal** (player had matching-color cards): The player who played it draws 4 penalty cards. The opponent does not draw.
- **If the play was legal** (no matching-color cards): The challenger draws 6 cards (the original 4 plus 2 penalty).
- **If the opponent accepts** (no challenge): They draw 4 cards and their turn is skipped.

AI challenge behavior:
- When AI plays WD4 against human: Human is prompted to challenge or accept.
- When human plays WD4 against AI: AI challenges with 30% probability.

### UNO Call

- A player must call UNO when they play down to 1 card remaining.
- Human can pre-call UNO when they have 2 or fewer cards (before playing).
- AI auto-calls UNO 90% of the time; 10% it "forgets" (catchable by human).
- **Catch window**: Opponents can catch an uncalled UNO until the next player takes an action.
- **Penalty if caught**: Draw 2 cards.
- AI has a 50% chance of catching a human who forgets to call UNO (checked after a 2-second delay).

### Winning

- A player wins the round by playing their last card.
- **Scoring**: The winner scores points based on the cards remaining in the opponent's hand.
- **Match win**: First player to reach 500 points wins the match.

### Point Values

| Card             | Points |
|------------------|--------|
| Number 0         | 0      |
| Numbers 1-9      | Face value |
| SKIP             | 20     |
| REVERSE          | 20     |
| DRAW TWO         | 20     |
| WILD             | 50     |
| WILD DRAW FOUR   | 50     |

### Deck Exhaustion

When the draw pile is empty, the discard pile (except the top card) is reshuffled to form a new draw pile.

### AI Strategy

The AI uses a priority-based card selection system:

| Card             | Priority |
|------------------|----------|
| DRAW TWO         | 100      |
| SKIP             | 90       |
| REVERSE          | 80       |
| WILD DRAW FOUR   | 50       |
| WILD             | 40       |
| Number cards     | 10 + face value (10-19) |

When multiple cards share the highest priority, one is chosen at random. If no card is playable, the AI draws; if the drawn card is playable, it is played immediately.

For wild color selection, the AI picks the color it holds the most of. If the hand has no colored cards (all wilds), a random color is chosen.

---

## Architecture

### File Structure

```
uno/
  index.html          Entry point (loads game-core.js and game.js)
  styles.css           Stylesheet
  game.js              Game state, UI rendering, turn flow, AI logic
  src/
    game-core.js       Card class, deck operations, constants, validation, scoring
  __tests__/
    game-core.test.js  Jest test suite (41 tests)
  package.json         Node config (Jest dependency)
```

### Module Design

The codebase uses two modules with a clear separation of concerns:

**`src/game-core.js`** — Pure logic, no DOM access. Dual-exported for Node (tests) and browser (game).

| Export                | Type     | Purpose                                        |
|-----------------------|----------|-------------------------------------------------|
| `COLORS`              | Constant | `['RED', 'YELLOW', 'GREEN', 'BLUE']`            |
| `NUMBER_VALUES`       | Constant | `['0'..'9']`                                    |
| `ACTION_TYPES`        | Constant | `['SKIP', 'REVERSE', 'DRAW_TWO']`               |
| `WILD_TYPES`          | Constant | `['WILD', 'WILD_DRAW_FOUR']`                    |
| `WILD_COLOR`          | Constant | `'NONE'`                                        |
| `CARD_POINTS`         | Constant | Point value lookup by card value                |
| `DISPLAY_COLORS`      | Constant | Uppercase-to-lowercase color mapping for UI     |
| `toDisplayColor()`    | Function | Logic color -> display color                    |
| `toLogicColor()`      | Function | Display color -> logic color                    |
| `Card`                | Class    | Card with `color`, `value`, `canPlayOn()`, `getPoints()`, `isWild()`, `isAction()`, `isNumber()` |
| `createDeck()`        | Function | Returns a 108-card deck                         |
| `shuffleDeck()`       | Function | Fisher-Yates in-place shuffle                   |
| `isActionCard()`      | Function | Checks if card is action or wild                |
| `getCardEffect()`     | Function | Maps card value to effect string                |
| `chooseAutoColor()`   | Function | AI color selection (most-held color)             |
| `isWildDrawFourLegal()` | Function | Validates WD4 legality against hand             |
| `validateCardPlay()`  | Function | Validates a card play attempt                   |
| `calculateRoundScore()` | Function | Sums point values of a hand                    |
| `checkMatchWin()`     | Function | Checks if any player reached target score       |

**`game.js`** — Browser-only. Manages game state, DOM rendering, and player interaction.

| Component              | Purpose                                                    |
|------------------------|------------------------------------------------------------|
| `gameState` object     | Central state: deck, discard pile, players, turn tracking   |
| `init()`               | Creates deck, shuffles, deals, handles start card           |
| `playCard()`           | Validates and plays a card, applies effects, checks win/UNO |
| `drawCard()`           | Draws a card; if playable, allows immediate play            |
| `chooseColor()`        | Handles human color selection after wild                    |
| `resolveChallenge()`   | Handles human's challenge decision on AI's WD4              |
| `resolveAIChallenge()` | Handles AI's challenge of human's WD4                       |
| `aiTurn()`             | AI decision loop using `calculateAIStrategy()`              |
| `calculateAIStrategy()` | Finds playable cards, ranks by priority                   |
| `render()`             | Updates all DOM elements (board, hand, info, debug)         |

### Data Flow

```
game-core.js (pure logic)
    |
    |-- Card class, deck creation, shuffle, validation, scoring
    |
game.js (state + UI)
    |
    |-- imports game-core via window.gameCore (browser) or require (Node)
    |-- gameState.init() creates deck using gameCore.createDeck() + shuffleDeck()
    |-- playCard() uses Card.canPlayOn() for validation
    |-- Wild color selection uses gameCore.chooseAutoColor()
    |-- Color conversion uses gameCore.toLogicColor() / toDisplayColor()
    |
index.html
    |
    |-- Loads game-core.js first (sets window.gameCore)
    |-- Loads game.js second (reads window.gameCore)
    |-- gameState.init() runs on DOMContentLoaded
```

### Testing

Single test file (`__tests__/game-core.test.js`) with 41 tests covering:

- Deck creation (card counts, color distribution, wild cards)
- Card class (`canPlayOn`, `getPoints`)
- Card classification (`isActionCard`, `getCardEffect`)
- Shuffle (size preservation, card multiset preservation)
- AI color selection (most-held color, empty hand, ties)
- WD4 legality checks
- Card play validation
- Round scoring
- Match win detection

Run tests: `npx jest`
