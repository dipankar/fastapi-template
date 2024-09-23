class AuthenticatedWebSocket {
    constructor(url, token) {
        this.url = url;
        this.token = token;
        this.socket = null;
        this.connect();
    }

    connect() {
        this.socket = new WebSocket(`${this.url}?token=${this.token}`);

        this.socket.onopen = (event) => {
            console.log('WebSocket connection established');
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Received message:', data);
            // Handle the received message here
        };

        this.socket.onclose = (event) => {
            console.log('WebSocket connection closed');
            // Implement reconnection logic here if needed
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    send(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not open. Message not sent.');
        }
    }

    close() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Usage:
// const token = 'your_jwt_token_here';
// const ws = new AuthenticatedWebSocket('ws://your-server-url/ws', token);