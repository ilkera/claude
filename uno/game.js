// Import game logic (for Node/browser compatibility)
const gameLogic = typeof module !== 'undefined' && module.require ? require('./src/game-logic') : window.gameLogic;

// Card class
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

    getHTML() {
        let text = this.value;
        if (this.isWild()) {
            text = this.value === 'wild_draw' ? 'WILD\n+4' : 'WILD';
        }
        return `<div class="card ${this.color}" data-card="${this.color}-${this.value}">${text}</div>`;
    }
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

    // Initialize the game
    init() {
        this.createDeck();
        this.shuffleDeck();
        this.dealCards();
        this.discardPile.push(this.deck.pop());
        
        // Make sure first card isn't a special card
        while (this.isSpecialCard(this.discardPile[0])) {
            this.deck.push(this.discardPile.pop());
            this.shuffleDeck();
            this.discardPile.push(this.deck.pop());
        }
        
        this.render();
    },

    // Create standard UNO deck
    createDeck() {
        const colors = ['red', 'yellow', 'blue', 'green'];
        const values = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'skip', 'reverse', 'draw2'];
        
        // Number and action cards
        for (let color of colors) {
            for (let value of values) {
                if (value === '0') {
                    this.deck.push(new Card(color, value));
                } else {
                    this.deck.push(new Card(color, value));
                    this.deck.push(new Card(color, value));
                }
            }
        }
        
        // Wild cards
        for (let i = 0; i < 4; i++) {
            this.deck.push(new Card('wild', 'wild'));
            this.deck.push(new Card('wild', 'wild_draw'));
        }
    },

    // Shuffle deck using Fisher-Yates
    shuffleDeck() {
        for (let i = this.deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.deck[i], this.deck[j]] = [this.deck[j], this.deck[i]];
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

    // Check if card is a special card
    isSpecialCard(card) {
        return ['skip', 'reverse', 'draw2', 'wild', 'wild_draw'].includes(card.value);
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
        
        // Check if player can play the drawn card
        const topCard = this.discardPile[this.discardPile.length - 1];
        if (card.canPlayOn(topCard, this.wildColor)) {
            document.getElementById('gameStatus').textContent = 'Card drawn! You can play it if you want.';
            // Return the drawn card so callers (like AI) can act on it
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
        this.shuffleDeck();
    },

    // Play a card
    playCard(cardIndex) {
        if (this.gameOver) return;
        
        const currentPlayer = this.players[this.currentPlayerIndex];
        const card = currentPlayer.hand[cardIndex];
        const topCard = this.discardPile[this.discardPile.length - 1];
        
        // Check if move is valid
        if (!card.canPlayOn(topCard, this.wildColor)) {
            alert('Invalid move! Card cannot be played.');
            return;
        }
        
        // Remove card from hand
        currentPlayer.hand.splice(cardIndex, 1);
        this.discardPile.push(card);
        this.wildColor = null;
        
        // Handle special cards
        if (card.value === 'draw2') {
            this.drawCards(2);
        } else if (card.value === 'wild_draw') {
            // Use game logic to handle wild_draw for AI vs human
            const logic = currentPlayer.isHuman 
                ? gameLogic.handleHumanWildCard(true)
                : gameLogic.handleAIWildCard(true, currentPlayer.hand, null);
            
            this.drawCards(logic.cardsForNext);
            this.wildColor = logic.wildColor;
            
            if (currentPlayer.isHuman) {
                this.awaitingColorChoice = logic.awaitColorChoice;
                this.showColorPicker();
                this.render();
                return;
            } else {
                this.nextTurn();
                this.render();
                return;
            }
        } else if (card.value === 'skip') {
            this.nextTurn();
        } else if (card.value === 'reverse') {
            if (this.players.length === 2) {
                this.nextTurn();
            } else {
                this.direction *= -1;
            }
        } else if (card.isWild()) {
            // Use game logic to handle wild for AI vs human
            const logic = currentPlayer.isHuman 
                ? gameLogic.handleHumanWildCard(false)
                : gameLogic.handleAIWildCard(false, currentPlayer.hand, null);
            
            this.wildColor = logic.wildColor;
            
            if (currentPlayer.isHuman) {
                this.awaitingColorChoice = logic.awaitColorChoice;
                this.showColorPicker();
                this.render();
                return;
            } else {
                // AI auto-selects; continue to turn advancement
            }
        }
        
        // Check for win
        if (currentPlayer.hand.length === 0) {
            this.endGame(currentPlayer.name);
            this.render();
            return;
        }
        
        // Check for UNO
        if (currentPlayer.hand.length === 1 && !this.callUnoPlayed) {
            document.getElementById('gameStatus').textContent = `${currentPlayer.name} has UNO!`;
        }
        
        this.nextTurn();
        this.render();
    },

    // Draw multiple cards
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
        // Use game logic to process the choice
        const result = gameLogic.processColorChoice(color);
        this.wildColor = result.wildColor;
        this.awaitingColorChoice = result.awaitColorChoice;
        
        document.getElementById('colorPickerContainer').style.display = 'none';
        
        // If we were waiting for the human to pick a color after playing a wild, advance the turn
        if (result.shouldAdvanceTurn) {
            this.nextTurn();
        }
        this.render();
    },



    // Call UNO
    callUno() {
        const currentPlayer = this.players[this.currentPlayerIndex];
        if (currentPlayer.hand.length === 1) {
            this.callUnoPlayed = true;
            document.getElementById('gameStatus').textContent = `${currentPlayer.name} called UNO!`;
        }
    },

    // Next turn
    nextTurn() {
        this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
        this.callUnoPlayed = false;
        
        // AI turn
        if (!this.gameOver && !this.players[this.currentPlayerIndex].isHuman) {
            setTimeout(() => this.aiTurn(), 1500);
        }
    },

    // AI turn logic
    aiTurn() {
        const aiPlayer = this.players[this.currentPlayerIndex];
        const topCard = this.discardPile[this.discardPile.length - 1];
        
        // Find playable cards
        const playableCards = aiPlayer.hand
            .map((card, index) => ({ card, index }))
            .filter(({ card }) => card.canPlayOn(topCard, this.wildColor));
        
        if (playableCards.length === 0) {
            // If AI draws a playable card, auto-play it; otherwise drawCard() will call nextTurn()
            const drawn = this.drawCard();
            if (drawn && drawn.canPlayOn(topCard, this.wildColor)) {
                // drawn card was pushed to the end of AI hand
                const idx = aiPlayer.hand.length - 1;
                this.playCard(idx);
            }
        } else {
            // Play a random card from playable cards
            const selected = playableCards[Math.floor(Math.random() * playableCards.length)];
            this.playCard(selected.index);
        }
    },

    // End game
    endGame(winner) {
        this.gameOver = true;
        document.getElementById('gameStatus').textContent = `🎉 ${winner} wins the game! 🎉`;
    },

    // Reset game
    resetGame() {
        this.deck = [];
        this.discardPile = [];
        this.players.forEach(p => p.hand = []);
        this.currentPlayerIndex = 0;
        this.direction = 1;
        this.wildColor = null;
        this.gameOver = false;
        this.callUnoPlayed = false;
        document.getElementById('colorPickerContainer').style.display = 'none';
        this.init();
    },

    // Render game state
    render() {
        this.updateBoard();
        this.updatePlayerHand();
        this.updatePlayerInfo();
        this.updateGameInfo();
    },

    // Update game board
    updateBoard() {
        const topCard = this.discardPile[this.discardPile.length - 1];
        const discardPile = document.getElementById('discardPile');
        
        let cardHTML = `<div class="card ${topCard.color}" style="color: white;">${topCard.value}</div>`;
        if (this.wildColor) {
            cardHTML = `<div class="card ${this.wildColor}" style="color: white;">WILD</div>`;
        }
        discardPile.innerHTML = cardHTML;
        
        document.getElementById('deckCount').textContent = `${this.deck.length} cards`;
    },

    // Update player hand
    updatePlayerHand() {
        const hand = document.getElementById('playerHand');
        const currentPlayer = this.players[0];
        
        hand.innerHTML = currentPlayer.hand
            .map((card, index) => {
                const playable = card.canPlayOn(this.discardPile[this.discardPile.length - 1], this.wildColor);
                const classes = `${card.color} ${!playable ? 'invalid' : ''}`;
                return `<div class="card ${classes}" onclick="if (${this.currentPlayerIndex} === 0) gameState.playCard(${index})">${card.value}</div>`;
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
    }
};

// Start game when page loads
window.addEventListener('DOMContentLoaded', () => {
    gameState.init();
});
