# Copilot Instructions for Uno Game

## Project Overview

A web-based Uno card game with vanilla JavaScript, playable against an AI opponent. The game implements full UNO rules including action cards, wild cards, and a basic AI strategy system.

## Architecture

### Core Components

1. **Card System** (`game.js` - Card class)
   - Immutable card objects with color and value properties
   - `canPlayOn()` validates moves against current discard pile and wild color
   - `getHTML()` generates visual representation

2. **Game State** (`game.js` - gameState object)
   - Centralized state container managing: deck, discard pile, players, turn order
   - Two-player system: Player 1 (human) and Player 2 (AI)
   - Direction tracking for Reverse card logic

3. **UI Layer** (`index.html`, `styles.css`)
   - DOM-based rendering without frameworks
   - Real-time updates via `gameState.render()` method
   - Card interaction through onclick handlers with card index

### Data Flow

1. User clicks card → `playCard(cardIndex)` → validates → updates state → `render()`
2. Draw button → `drawCard()` → adds to hand → triggers AI if needed → `render()`
3. AI turn triggered by `nextTurn()` → `aiTurn()` → `playCard()` → recursion or `drawCard()`

## Key Patterns & Conventions

### Card Validation Pattern
```javascript
card.canPlayOn(topCard, wildColor)
// Returns true if: card is wild OR color matches OR value matches (ignoring wild color)
```

### Game State Updates
Always follow: **Action → State Change → Render**
- Never directly manipulate DOM; use `gameState.render()` to update all UI elements
- Current methods: `updateBoard()`, `updatePlayerHand()`, `updatePlayerInfo()`, `updateGameInfo()`

### Wild Card Handling
- Wild cards trigger `showColorPicker()` modal
- Selection via `chooseColor(color)` stores in `gameState.wildColor`
- Must call `render()` after wild card selection to update discard pile display

### AI Strategy
- Find all valid playable cards: `hand.filter(card => card.canPlayOn(topCard, wildColor))`
- Select randomly from valid cards (can be enhanced with difficulty levels)
- AI cannot see player's hand (proper game rules)

## Developer Workflows

### Testing New Features
- Edit `game.js` game state or logic
- Reload browser to see changes immediately (no build step)
- Use browser console for debugging: `gameState.players[0].hand` to inspect state

### Adding Card Types
1. Add value to `values` array in `createDeck()`
2. Add special logic in `playCard()` method before `nextTurn()`
3. Update `isSpecialCard()` if it affects turn logic

### Debugging Tips
- `console.log(gameState)` - inspect full game state
- Card objects: `gameState.players[0].hand[0]` - check specific cards
- DOM updates: Check `updateBoard()`, `updatePlayerHand()` methods
- Remove `setTimeout` in `aiTurn()` for instant testing

## Integration Points & External Dependencies

### None
- **Zero external dependencies** - pure vanilla JavaScript, HTML, CSS
- No build tools, bundlers, or transpilers required
- Browser APIs used: DOM manipulation, Array methods, Math.random()

## Important Implementation Notes

1. **Deck Reshuffling**: When main deck runs out, discard pile (except top card) gets reshuffled
2. **Draw 2/Wild +4 Logic**: Next player draws, but doesn't skip turn automatically (current flow)
3. **Color Picker Modal**: Uses absolute positioning; must call `render()` after `chooseColor()`
4. **Direction Logic**: Works correctly with 2 players (Reverse = skip); adjust for 4+ players
5. **Game Over**: Once `gameState.gameOver = true`, only `resetGame()` restarts

## File Structure
```
uno-game/
├── index.html           # Game UI structure
├── styles.css          # Styling and animations
├── game.js             # Game logic (Card class + gameState)
├── README.md           # User documentation
└── .github/
    └── copilot-instructions.md  # This file
```

## When Implementing Changes

- **UI changes**: Edit `index.html` structure and `styles.css`
- **Game logic**: Edit `gameState` methods or Card class in `game.js`
- **AI strategy**: Modify `aiTurn()` method (currently random selection from valid cards)
- **Multiplayer support**: Extend `players` array structure and game flow
