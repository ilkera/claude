// Import game-core (Node/browser compatible)
var _gameCore = typeof module !== 'undefined' && module.require ? require('./src/game-core') : window.gameCore;

// Display-friendly value names for rendering
var _DISPLAY_VALUES = {
    'SKIP': 'SKIP', 'REVERSE': 'REV', 'DRAW_TWO': '+2',
    'WILD': 'WILD', 'WILD_DRAW_FOUR': 'W+4'
};
function displayValue(card) {
    return _DISPLAY_VALUES[card.value] || card.value;
}
function displayColor(card) {
    return _gameCore.toDisplayColor(card.color) || (card.isWild() ? 'wild' : card.color);
}

// Game state management
const gameState = {
    deck: [],
    discardPile: [],
    players: [
        { hand: [], name: 'Player 1', isHuman: true },
        { hand: [], name: 'Player 2', isHuman: false }
    ],
    currentPlayerIndex: 0,
    direction: 1, // 1 for forward, -1 for reverse
    wildColor: null,
    gameOver: false,
    callUnoPlayed: false,
    awaitingColorChoice: false,
    awaitingWildDrawFourSkip: false,
    lastWildDrawFourLegal: true,
    awaitingChallenge: false,
    pendingWildDrawFourPlayer: null,
    scores: { 'Player 1': 0, 'Player 2': 0 },
    unoCalledByPlayer: {},
    debugMode: true,

    // Initialize the game
    init() {
        this.deck = _gameCore.shuffleDeck(_gameCore.createDeck());
        this.dealCards();
        this.discardPile.push(this.deck.pop());
        this.handleStartCard();
        this.render();
    },

    // Handle the starting discard card per rules.yaml
    handleStartCard() {
        const startCard = this.discardPile[this.discardPile.length - 1];

        if (startCard.value === 'WILD' || startCard.value === 'WILD_DRAW_FOUR') {
            this.deck.push(this.discardPile.pop());
            _gameCore.shuffleDeck(this.deck);
            this.discardPile.push(this.deck.pop());
            this.handleStartCard();
        } else if (startCard.value === 'SKIP') {
            document.getElementById('gameStatus').textContent = 'Start card is SKIP! Player 1 is skipped.';
            this.nextTurn();
        } else if (startCard.value === 'REVERSE') {
            if (this.players.length === 2) {
                document.getElementById('gameStatus').textContent = 'Start card is REVERSE! Player 1 is skipped.';
                this.nextTurn();
            } else {
                this.direction *= -1;
                document.getElementById('gameStatus').textContent = 'Start card is REVERSE! Direction reversed.';
            }
        } else if (startCard.value === 'DRAW_TWO') {
            const firstPlayer = this.players[this.currentPlayerIndex];
            for (let i = 0; i < 2; i++) {
                if (this.deck.length === 0) this.reshuffleDeck();
                firstPlayer.hand.push(this.deck.pop());
            }
            document.getElementById('gameStatus').textContent = `Start card is DRAW TWO! ${firstPlayer.name} draws 2 and is skipped.`;
            this.nextTurn();
        }
    },

    // Deal initial 7 cards to each player
    dealCards() {
        for (let i = 0; i < 7; i++) {
            for (let player of this.players) {
                player.hand.push(this.deck.pop());
            }
        }
    },

    // Draw a card
    drawCard() {
        if (this.gameOver) return;

        const currentPlayer = this.players[this.currentPlayerIndex];

        if (this.deck.length === 0) {
            this.reshuffleDeck();
        }

        const card = this.deck.pop();
        currentPlayer.hand.push(card);

        const topCard = this.discardPile[this.discardPile.length - 1];
        if (card.canPlayOn(topCard, this.wildColor)) {
            document.getElementById('gameStatus').textContent = 'Card drawn! You can play it if you want.';
            this.render();
            return card;
        } else {
            this.nextTurn();
        }

        this.render();
        return null;
    },

    // Reshuffle deck from discard pile
    reshuffleDeck() {
        const topCard = this.discardPile.pop();
        this.deck = this.discardPile;
        this.discardPile = [topCard];
        _gameCore.shuffleDeck(this.deck);
    },

    // Play a card
    playCard(cardIndex) {
        if (this.gameOver) return;

        const currentPlayer = this.players[this.currentPlayerIndex];
        const card = currentPlayer.hand[cardIndex];
        const topCard = this.discardPile[this.discardPile.length - 1];

        if (!card.canPlayOn(topCard, this.wildColor)) {
            alert('Invalid move! Card cannot be played.');
            return;
        }

        // WILD_DRAW_FOUR constraint: MUST_HAVE_NO_MATCHING_COLOR
        if (card.value === 'WILD_DRAW_FOUR') {
            const activeColor = this.wildColor || topCard.color;
            const hasMatchingColor = currentPlayer.hand.some(
                (c, i) => i !== cardIndex && c.color === activeColor
            );
            if (hasMatchingColor && currentPlayer.isHuman) {
                alert('You cannot play Wild Draw Four when you have cards matching the current color!');
                return;
            }
            this.lastWildDrawFourLegal = !hasMatchingColor;
        }

        // Remove card from hand
        currentPlayer.hand.splice(cardIndex, 1);
        this.discardPile.push(card);
        this.wildColor = null;

        // Handle special cards
        if (card.value === 'DRAW_TWO') {
            this.drawCards(2);
            this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
        } else if (card.value === 'WILD_DRAW_FOUR') {
            this.pendingWildDrawFourPlayer = this.currentPlayerIndex;

            if (currentPlayer.isHuman) {
                this.awaitingColorChoice = true;
                this.awaitingWildDrawFourSkip = true;
                this.showColorPicker();
                this.render();
                return;
            } else {
                // AI auto-selects color
                this.wildColor = _gameCore.chooseAutoColor(currentPlayer.hand);
                this.awaitingChallenge = true;
                document.getElementById('challengeContainer').style.display = 'block';
                document.getElementById('gameStatus').textContent = 'AI played Wild Draw Four! Challenge or accept?';
                this.render();
                return;
            }
        } else if (card.value === 'SKIP') {
            this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
        } else if (card.value === 'REVERSE') {
            if (this.players.length === 2) {
                // 2-player: acts as SKIP
                this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
            } else {
                this.direction *= -1;
            }
        } else if (card.isWild()) {
            if (currentPlayer.isHuman) {
                this.awaitingColorChoice = true;
                this.showColorPicker();
                this.render();
                return;
            } else {
                this.wildColor = _gameCore.chooseAutoColor(currentPlayer.hand);
            }
        }

        // Check for win
        if (currentPlayer.hand.length === 0) {
            this.endGame(currentPlayer.name);
            this.render();
            return;
        }

        // Check for UNO
        if (currentPlayer.hand.length === 1) {
            if (!currentPlayer.isHuman) {
                if (Math.random() < 0.9) {
                    this.unoCalledByPlayer[this.currentPlayerIndex] = true;
                    document.getElementById('gameStatus').textContent = `${currentPlayer.name} calls UNO!`;
                } else {
                    document.getElementById('gameStatus').textContent = `${currentPlayer.name} has UNO! Did they call it?`;
                }
            } else if (!this.unoCalledByPlayer[this.currentPlayerIndex]) {
                document.getElementById('gameStatus').textContent = `${currentPlayer.name} has UNO!`;
                if (Math.random() < 0.5) {
                    setTimeout(() => {
                        if (!this.unoCalledByPlayer[this.currentPlayerIndex] && currentPlayer.hand.length === 1) {
                            for (let j = 0; j < 2; j++) {
                                if (this.deck.length === 0) this.reshuffleDeck();
                                currentPlayer.hand.push(this.deck.pop());
                            }
                            document.getElementById('gameStatus').textContent =
                                `AI caught you not calling UNO! Draw 2 cards!`;
                            this.render();
                        }
                    }, 2000);
                }
            }
        }

        this.nextTurn();
        this.render();
    },

    // Draw multiple cards for next player
    drawCards(count) {
        const nextPlayer = this.players[(this.currentPlayerIndex + this.direction + this.players.length) % this.players.length];
        for (let i = 0; i < count; i++) {
            if (this.deck.length === 0) {
                this.reshuffleDeck();
            }
            nextPlayer.hand.push(this.deck.pop());
        }
    },

    // Show color picker for wild cards
    showColorPicker() {
        document.getElementById('colorPickerContainer').style.display = 'block';
    },

    // Choose color for wild card
    chooseColor(color) {
        this.wildColor = _gameCore.toLogicColor(color);
        this.awaitingColorChoice = false;

        document.getElementById('colorPickerContainer').style.display = 'none';

        if (this.awaitingWildDrawFourSkip) {
            this.awaitingWildDrawFourSkip = false;
            const aiChallenges = Math.random() < 0.3;
            if (aiChallenges) {
                document.getElementById('gameStatus').textContent = 'AI challenges your Wild Draw Four!';
                setTimeout(() => this.resolveAIChallenge(), 1500);
            } else {
                this.drawCards(4);
                this.nextTurn(); // Skip past AI
                this.nextTurn(); // Back to human
            }
        } else {
            this.nextTurn();
        }
        this.render();
    },

    // Resolve AI's challenge of human's WD4
    resolveAIChallenge() {
        const wasIllegal = !this.lastWildDrawFourLegal;

        if (wasIllegal) {
            // Human's WD4 was illegal — human draws 4
            const human = this.players[0];
            for (let i = 0; i < 4; i++) {
                if (this.deck.length === 0) this.reshuffleDeck();
                human.hand.push(this.deck.pop());
            }
            document.getElementById('gameStatus').textContent =
                `Challenge successful! Your Wild Draw Four was illegal. You draw 4 cards!`;
            this.nextTurn();
        } else {
            // Human's WD4 was legal — AI draws 6
            const ai = this.players[1];
            for (let i = 0; i < 6; i++) {
                if (this.deck.length === 0) this.reshuffleDeck();
                ai.hand.push(this.deck.pop());
            }
            document.getElementById('gameStatus').textContent =
                `Challenge failed! AI draws 6 cards.`;
            this.nextTurn(); // Skip AI
            this.nextTurn(); // Back to human
        }
        this.render();
    },

    // Resolve human's challenge of AI's WD4
    resolveChallenge(doChallenge) {
        document.getElementById('challengeContainer').style.display = 'none';
        this.awaitingChallenge = false;

        if (doChallenge) {
            const wasIllegal = !this.lastWildDrawFourLegal;

            if (wasIllegal) {
                // AI's WD4 was illegal — AI draws 4
                const ai = this.players[this.pendingWildDrawFourPlayer];
                for (let i = 0; i < 4; i++) {
                    if (this.deck.length === 0) this.reshuffleDeck();
                    ai.hand.push(this.deck.pop());
                }
                document.getElementById('gameStatus').textContent =
                    `Challenge successful! AI's Wild Draw Four was illegal. AI draws 4 cards!`;
                this.nextTurn();
            } else {
                // AI's WD4 was legal — human draws 6
                const human = this.players[0];
                for (let i = 0; i < 6; i++) {
                    if (this.deck.length === 0) this.reshuffleDeck();
                    human.hand.push(this.deck.pop());
                }
                document.getElementById('gameStatus').textContent =
                    `Challenge failed! You draw 6 cards.`;
                this.nextTurn(); // Skip human
                this.nextTurn(); // Advance to AI
            }
        } else {
            this.drawCards(4);
            document.getElementById('gameStatus').textContent = 'You accepted. Drawing 4 cards and skipping your turn.';
            this.nextTurn(); // Skip human
            this.nextTurn(); // Advance to AI
        }
        this.pendingWildDrawFourPlayer = null;
        this.render();
    },

    // Call UNO
    callUno() {
        const currentPlayer = this.players[this.currentPlayerIndex];
        if (currentPlayer.hand.length <= 2 && currentPlayer.isHuman) {
            this.unoCalledByPlayer[this.currentPlayerIndex] = true;
            document.getElementById('gameStatus').textContent = `${currentPlayer.name} called UNO!`;
        }
    },

    // Catch opponent not calling UNO
    catchUno() {
        for (let i = 0; i < this.players.length; i++) {
            const player = this.players[i];
            if (player.hand.length === 1 && !this.unoCalledByPlayer[i]) {
                for (let j = 0; j < 2; j++) {
                    if (this.deck.length === 0) this.reshuffleDeck();
                    player.hand.push(this.deck.pop());
                }
                document.getElementById('gameStatus').textContent =
                    `${player.name} was caught not calling UNO! Draws 2 penalty cards!`;
                this.unoCalledByPlayer[i] = true;
                this.render();
                return;
            }
        }
        document.getElementById('gameStatus').textContent = 'No one to catch!';
    },

    // Calculate AI's best move strategy
    calculateAIStrategy() {
        const aiPlayer = this.players[1];
        const topCard = this.discardPile[this.discardPile.length - 1];

        const playableCards = aiPlayer.hand
            .map((card, index) => ({ card, index }))
            .filter(({ card }) => card.canPlayOn(topCard, this.wildColor));

        if (playableCards.length === 0) {
            return { playableCount: 0, bestCard: null, bestCards: [], maxPriority: null, allCards: [] };
        }

        const priorities = playableCards.map(pc => this.getCardPriority(pc.card));
        const maxPriority = Math.max(...priorities);
        const bestCards = playableCards.filter((pc, idx) => priorities[idx] === maxPriority);

        return {
            playableCount: playableCards.length,
            bestCard: bestCards[0],
            bestCards: bestCards,
            maxPriority: maxPriority,
            allCards: playableCards.map((pc, idx) => ({
                card: pc.card, index: pc.index, priority: priorities[idx]
            }))
        };
    },

    // Next turn
    nextTurn() {
        this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
        this.callUnoPlayed = false;
        this.unoCalledByPlayer = {};

        if (!this.gameOver && !this.players[this.currentPlayerIndex].isHuman) {
            setTimeout(() => this.aiTurn(), 1500);
        }
    },

    // AI card priority for strategic play
    getCardPriority(card) {
        if (card.value === 'DRAW_TWO') return 100;
        if (card.value === 'SKIP') return 90;
        if (card.value === 'REVERSE') return 80;
        if (card.value === 'WILD_DRAW_FOUR') return 50;
        if (card.value === 'WILD') return 40;
        const numValue = parseInt(card.value);
        if (!isNaN(numValue)) return 10 + numValue;
        return 0;
    },

    // AI turn logic
    aiTurn() {
        const strategy = this.calculateAIStrategy();
        const aiPlayer = this.players[this.currentPlayerIndex];
        const topCard = this.discardPile[this.discardPile.length - 1];

        if (strategy.playableCount === 0) {
            const drawn = this.drawCard();
            if (drawn && drawn.canPlayOn(topCard, this.wildColor)) {
                const idx = aiPlayer.hand.length - 1;
                this.playCard(idx);
            }
        } else if (strategy.playableCount === 1) {
            this.playCard(strategy.bestCard.index);
        } else {
            const selected = strategy.bestCards[Math.floor(Math.random() * strategy.bestCards.length)];
            this.playCard(selected.index);
        }
    },

    // End game
    endGame(winner) {
        this.gameOver = true;
        document.getElementById('gameStatus').textContent = `🎉 ${winner} wins the game! 🎉`;
    },

    // Reset game (new round)
    resetGame() {
        this.deck = [];
        this.discardPile = [];
        this.players.forEach(p => p.hand = []);
        this.currentPlayerIndex = 0;
        this.direction = 1;
        this.wildColor = null;
        this.gameOver = false;
        this.callUnoPlayed = false;
        this.awaitingWildDrawFourSkip = false;
        this.awaitingChallenge = false;
        this.lastWildDrawFourLegal = true;
        this.pendingWildDrawFourPlayer = null;
        this.unoCalledByPlayer = {};
        document.getElementById('colorPickerContainer').style.display = 'none';
        document.getElementById('challengeContainer').style.display = 'none';
        this.init();
    },

    // Full reset (new match — resets scores)
    resetMatch() {
        this.scores = { 'Player 1': 0, 'Player 2': 0 };
        this.updateScoreDisplay();
        this.resetGame();
    },

    // Render game state
    render() {
        this.updateBoard();
        this.updatePlayerHand();
        this.updatePlayerInfo();
        this.updateGameInfo();
        if (this.debugMode) {
            this.updateDebugInfo();
        }
    },

    // Update game board
    updateBoard() {
        const topCard = this.discardPile[this.discardPile.length - 1];
        const discardPile = document.getElementById('discardPile');

        let cardHTML = `<div class="card ${displayColor(topCard)}" style="color: white;">${displayValue(topCard)}</div>`;
        if (this.wildColor) {
            cardHTML = `<div class="card ${_gameCore.toDisplayColor(this.wildColor)}" style="color: white;">WILD</div>`;
        }
        discardPile.innerHTML = cardHTML;

        document.getElementById('deckCount').textContent = `${this.deck.length} cards`;
    },

    // Update player hand
    updatePlayerHand() {
        const hand = document.getElementById('playerHand');
        const currentPlayer = this.players[0];
        const topCard = this.discardPile[this.discardPile.length - 1];

        hand.innerHTML = currentPlayer.hand
            .map((card, index) => {
                const playable = card.canPlayOn(topCard, this.wildColor);
                const classes = `${displayColor(card)} ${!playable ? 'invalid' : ''}`;
                return `<div class="card ${classes}" onclick="if (${this.currentPlayerIndex} === 0) gameState.playCard(${index})">${displayValue(card)}</div>`;
            })
            .join('');
    },

    // Update player info
    updatePlayerInfo() {
        const p1 = this.players[0];
        const p2 = this.players[1];

        document.getElementById('p1HandSize').textContent = `Hand: ${p1.hand.length} cards`;
        document.getElementById('p2HandSize').textContent = `Hand: ${p2.hand.length} cards`;

        document.getElementById('p1Uno').textContent = p1.hand.length === 1 ? '🔴 UNO!' : '';
        document.getElementById('p2Uno').textContent = p2.hand.length === 1 ? '🔴 UNO!' : '';
    },

    // Update game info
    updateGameInfo() {
        const currentPlayer = this.players[this.currentPlayerIndex];
        document.getElementById('currentPlayer').textContent = currentPlayer.name;

        if (!this.gameOver && this.currentPlayerIndex === 1) {
            document.getElementById('gameStatus').textContent = 'AI is thinking...';
        } else if (!this.gameOver) {
            document.getElementById('gameStatus').textContent = 'Your turn! Play a card or draw.';
        }
    },

    // Debug info: Show AI's hand and strategy
    updateDebugInfo() {
        const debugContainer = document.getElementById('debugInfo');
        if (!debugContainer) return;

        const aiPlayer = this.players[1];
        const topCard = this.discardPile[this.discardPile.length - 1];
        const strategy = this.calculateAIStrategy();

        let debugHTML = `
            <h4>🐛 DEBUG INFO</h4>
            <p><strong>AI Hand (${aiPlayer.hand.length} cards):</strong></p>
            <div style="display: flex; flex-wrap: wrap; gap: 5px;">
        `;

        aiPlayer.hand.forEach((card, idx) => {
            const isPlayable = card.canPlayOn(topCard, this.wildColor);
            const borderStyle = isPlayable ? 'border: 3px solid lime;' : 'border: 1px solid gray;';
            const priority = isPlayable ? this.getCardPriority(card) : '-';
            debugHTML += `<div class="card ${displayColor(card)}" style="${borderStyle}; position: relative;" title="Priority: ${priority}"><small>${displayValue(card)}</small></div>`;
        });

        debugHTML += `
            </div>
            <p><strong>Playable Cards:</strong> ${strategy.playableCount} / ${aiPlayer.hand.length}</p>
        `;

        if (strategy.playableCount > 0) {
            debugHTML += `
                <div style="background: #e8f5e9; padding: 8px; border-radius: 4px; margin: 8px 0;">
                    <p style="margin: 5px 0;"><strong>📊 AI Strategy:</strong></p>
                    <p style="margin: 5px 0; font-size: 12px;"><strong>Card Priorities:</strong></p>
                    <ul style="margin: 5px 0; padding-left: 20px; font-size: 12px;">
            `;

            strategy.allCards.forEach(ac => {
                const isBest = ac.priority === strategy.maxPriority;
                const bestMarker = isBest ? '⭐ ' : '';
                debugHTML += `<li>${bestMarker}${displayColor(ac.card)} ${displayValue(ac.card)}: ${ac.priority}</li>`;
            });

            debugHTML += `
                    </ul>
                    <p style="margin: 5px 0; font-size: 12px;"><strong>Best Choice:</strong> ${strategy.bestCards.length} option(s) with priority ${strategy.maxPriority}</p>
                    <ul style="margin: 5px 0; padding-left: 20px; font-size: 12px;">
            `;

            strategy.bestCards.forEach(bc => {
                debugHTML += `<li>👉 ${displayColor(bc.card)} ${displayValue(bc.card)}</li>`;
            });

            debugHTML += `
                    </ul>
                </div>
            `;
        }

        debugHTML += `
            <p><strong>Top Card:</strong> ${displayColor(topCard)} ${displayValue(topCard)}</p>
            <p><strong>Active Color:</strong> ${this.wildColor ? _gameCore.toDisplayColor(this.wildColor) : 'none'}</p>
            <p><strong>Current Player:</strong> ${this.players[this.currentPlayerIndex].name}</p>
        `;

        debugContainer.innerHTML = debugHTML;
    }
};

// Start game when page loads
window.addEventListener('DOMContentLoaded', () => {
    gameState.init();
});
