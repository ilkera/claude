# Uno Card Game

A web-based implementation of the classic UNO card game. Play against an AI opponent in your browser.

## Features

- **Full UNO Rules**: Color matching, number matching, action cards (Skip, Reverse, Draw 2)
- **Wild Cards**: Play Wild and Wild +4 cards with color selection
- **AI Opponent**: Intelligent computer player with strategic card selection
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Game State**: Live updates for hand size, player status, and game progress

## Game Rules

- Players take turns playing cards that match the discard pile by color or number
- If you can't play, draw a card
- Action cards have special effects:
  - **Skip**: Next player's turn is skipped
  - **Reverse**: Direction of play is reversed
  - **Draw 2**: Next player draws 2 cards
  - **Wild**: Play any color, choose a new color
  - **Wild +4**: Next player draws 4 cards, choose a new color
- First player to empty their hand wins

## Getting Started

### Download and Run Locally

1. Clone the repository:
   ```bash
   git clone https://github.com/ilkera/claude.git
   cd claude/uno
   ```

2. Open the game in your browser:
   ```bash
   # macOS
   open index.html

   # Linux
   xdg-open index.html

   # Windows
   start index.html
   ```
   Or simply double-click `index.html` in your file manager.

3. (Optional) Install dev dependencies to run tests:
   ```bash
   npm install
   npm test
   ```

No build step or server required — the game runs entirely in the browser from static files.

### How to Play

1. Click on cards in your hand to play them
2. If no valid cards, click "Draw Card"
3. When you have 1 card left, click "UNO!" to declare it
4. Click "Catch!" if you think the AI forgot to call UNO
5. Click "New Game" to restart

## Files

- `index.html` - Game interface and layout
- `styles.css` - Styling and animations
- `game.js` - Game logic and AI implementation

## Browser Compatibility

Works in all modern browsers:
- Chrome
- Firefox
- Safari
- Edge

## Technical Details

### Game Architecture
- **Card System**: Object-oriented card representation with validation
- **Game State**: Centralized state management for game flow
- **AI Logic**: Simple but effective strategy using playable card selection
- **Rendering**: DOM-based rendering with real-time updates

### Key Functions
- `Card`: Card class with color, value, and game logic
- `gameState`: Central object managing game state and logic
  - `init()`: Initialize game
  - `playCard()`: Handle card plays
  - `drawCard()`: Player draws
  - `aiTurn()`: AI decision logic
  - `render()`: Update UI

## Future Enhancements

- Multiplayer support (2-4 players)
- Different AI difficulty levels
- Sound effects and animations
- Score tracking across games
- Card statistics and achievements
