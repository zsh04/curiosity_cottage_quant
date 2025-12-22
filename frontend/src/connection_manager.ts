import { TelemetryPacket } from './components/ProTerminal';

export type ConnectionState = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'CRITICAL';

export interface ConnectionConfig {
    url: string;
    maxBackoffMs: number;
    initialBackoffMs: number;
    criticalThresholdMs: number;
    onStateChange: (state: ConnectionState) => void;
    onMessage: (data: TelemetryPacket) => void;
    onLog: (msg: string) => void;
}

export class TelemetryConnectionManager {
    private ws: WebSocket | null = null;
    private config: ConnectionConfig;
    private backoffMs: number;
    private reconnectTimer: any = null;
    private criticalTimer: any = null;
    private lastMessageTime: number = Date.now();
    private state: ConnectionState = 'DISCONNECTED';
    private isIntentionalClose: boolean = false;

    constructor(config: ConnectionConfig) {
        this.config = config;
        this.backoffMs = config.initialBackoffMs;
    }

    public connect() {
        if (this.state === 'CONNECTED' || this.state === 'CONNECTING') return;

        this.isIntentionalClose = false;
        this._setState('CONNECTING');
        this.config.onLog(`Intent: Establishing Uplink to ${this.config.url}...`);

        try {
            this.ws = new WebSocket(this.config.url);
            this.ws.onopen = this._handleOpen.bind(this);
            this.ws.onmessage = this._handleMessage.bind(this);
            this.ws.onclose = this._handleClose.bind(this);
            this.ws.onerror = this._handleError.bind(this);
        } catch (e) {
            this.config.onLog(`Result: Connection Failed (${e}). Retrying...`);
            this._scheduleReconnect();
        }
    }

    public disconnect() {
        this.isIntentionalClose = true;
        this._clearTimers();
        if (this.ws) {
            this.ws.close();
        }
        this._setState('DISCONNECTED');
    }

    private _setState(newState: ConnectionState) {
        if (this.state !== newState) {
            this.state = newState;
            this.config.onStateChange(newState);
        }
    }

    private _handleOpen() {
        this.config.onLog('Result: Link Established. Stream Active.');
        this._setState('CONNECTED');
        this.backoffMs = this.config.initialBackoffMs; // Reset backoff
        this.lastMessageTime = Date.now();
        this._startCriticalMonitor();
    }

    private _handleMessage(event: MessageEvent) {
        try {
            this.lastMessageTime = Date.now();
            const packet: TelemetryPacket = JSON.parse(event.data);
            this.config.onMessage(packet);

            // If we were CRITICAL but got a message, revert to CONNECTED
            if (this.state === 'CRITICAL') {
                this._setState('CONNECTED');
                this.config.onLog('Recovery: Signal Restored.');
            }
        } catch (e) {
            console.error('Packet Parse Error', e);
        }
    }

    private _handleClose(event: CloseEvent) {
        this._clearTimers();
        if (this.isIntentionalClose) return;

        this._setState('DISCONNECTED');
        this.config.onLog(`Alert: Link Severed (Code: ${event.code}). Initiating Backoff Protocol...`);
        this._scheduleReconnect();
    }

    private _handleError(event: Event) {
        // WebSocket error usually leads to close, let close handle it
        console.error('WebSocket Error', event);
    }

    private _scheduleReconnect() {
        if (this.reconnectTimer) return;

        this.config.onLog(`Retry: Attempting reconnect in ${this.backoffMs}ms...`);

        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;

            // Exponential Backoff Logic
            this.backoffMs = Math.min(this.backoffMs * 2, this.config.maxBackoffMs);

            this.connect();
        }, this.backoffMs);
    }

    private _startCriticalMonitor() {
        if (this.criticalTimer) clearInterval(this.criticalTimer);

        this.criticalTimer = setInterval(() => {
            const timeSinceLast = Date.now() - this.lastMessageTime;

            if (this.state === 'CONNECTED' && timeSinceLast > this.config.criticalThresholdMs) {
                this._setState('CRITICAL');
                this.config.onLog(`CRITICAL: Data Loss Detected (> ${this.config.criticalThresholdMs}ms). Check Neural Engine.`);
            }
        }, 1000); // Check every second
    }

    private _clearTimers() {
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        if (this.criticalTimer) clearInterval(this.criticalTimer);
        this.reconnectTimer = null;
        this.criticalTimer = null;
    }
}
