const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const axios = require('axios');
const cors = require('cors');

// --- Configuration ---
const PORT = process.env.PORT || 3000;
const ENGINE_URL = process.env.ENGINE_URL || 'http://cc_engine:8000';
const FINBERT_URL = process.env.FINBERT_URL || 'http://cc_finbert:8000';

const app = express();
app.use(cors());
app.use(express.json());

// --- WebSocket Setup ---
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

console.log(`🚀 BFF Server Configuration:`);
console.log(`   - PORT: ${PORT}`);
console.log(`   - ENGINE: ${ENGINE_URL}`);
console.log(`   - FINBERT: ${FINBERT_URL}`);

// --- State Store ---
let latestTelemetry = {
    timestamp: null,
    status: 'Initializing',
    market: {
        price: 0.0,
        alpha: 0.0,
        regime: 'Unknown'
    },
    sentiment: {
        label: 'Neutral',
        score: 0.0
    },
    signals: [],
    logs: []
};

// --- API Routes (Proxies) ---

// Reset System
app.post('/trade/reset', async (req, res) => {
    try {
        console.log('[BFF] Proxying RESET request to Engine...');
        // Note: Engine endpoint might be /api/actions/reset or similar. 
        // Based on analysis, we found /api/actions/rebalance and /halt.
        // We will assume a future /reset or map it to something safe or log it.
        // For now, let's try /api/actions/reset assuming it will be implemented or proxy fails gracefully.
        const response = await axios.post(`${ENGINE_URL}/api/actions/reset`, req.body);
        res.json(response.data);
    } catch (error) {
        console.error('[BFF] Reset Proxy Error:', error.message);
        res.status(error.response?.status || 500).json({ error: 'Failed to reset engine' });
    }
});

// Force Trigger (Manual) -> Rebalance
app.post('/trade/force', async (req, res) => {
    try {
        console.log('[BFF] Proxying FORCE/REBALANCE request to Engine...');
        // Mapping 'force' to 'rebalance' as per finding /api/actions/rebalance
        const response = await axios.post(`${ENGINE_URL}/api/actions/rebalance`, req.body);
        res.json(response.data);
    } catch (error) {
        console.error('[BFF] Force Proxy Error:', error.message);
        res.status(error.response?.status || 500).json({ error: 'Failed to trigger engine' });
    }
});

async function fetchEngineState() {
    try {
        const [stateRes, agentMetricsRes, modelMetricsRes] = await Promise.all([
            axios.get(`${ENGINE_URL}/api/system/state/current`),
            axios.get(`${ENGINE_URL}/api/system/metrics/agents`),
            axios.get(`${ENGINE_URL}/api/system/metrics/models`)
        ]);

        return {
            state: stateRes.data,
            agentMetrics: agentMetricsRes.data,
            modelMetrics: modelMetricsRes.data
        };
    } catch (e) {
        console.error('[BFF] State Fetch Error:', e.message);
        return null;
    }
}

async function telemetryLoop() {
    try {
        // Fetch Real Observability Data
        const engineData = await fetchEngineState();

        if (engineData && engineData.state) {
            const state = engineData.state;

            // Build Enhanced Telemetry Packet
            latestTelemetry = {
                timestamp: state.timestamp || new Date().toISOString(),
                status: state.status || 'Unknown',

                // Market Data (from state)
                market: {
                    symbol: state.market?.symbol || 'SPY',
                    price: state.market?.price || 0.0,
                    alpha: state.market?.alpha || 0.0,
                    regime: state.market?.regime || 'Unknown',
                    velocity: state.market?.velocity || 0.0,
                    acceleration: state.market?.acceleration || 0.0
                },

                // Portfolio (from state)
                portfolio: {
                    nav: state.portfolio?.nav || 0.0,
                    cash: state.portfolio?.cash || 0.0,
                    daily_pnl: state.portfolio?.daily_pnl || 0.0,
                    max_drawdown: state.portfolio?.max_drawdown || 0.0
                },

                // Signal (from state)
                signal: {
                    side: state.signal?.side || 'FLAT',
                    confidence: state.signal?.confidence || 0.0,
                    reasoning: state.signal?.reasoning || ''
                },

                // Governance (from state)
                governance: {
                    approved_size: state.governance?.approved_size || 0.0
                },

                // Logs (from state)
                logs: state.logs || [],

                // Agent Performance (NEW)
                agents: engineData.agentMetrics || {},

                // Model Performance (NEW)
                models: engineData.modelMetrics || {},

                // Legacy sentiment (for backwards compatibility)
                sentiment: {
                    label: 'N/A',
                    score: 0.0
                }
            };

            // Broadcast to all connected clients
            const packet = JSON.stringify({
                type: 'TELEMETRY',
                data: latestTelemetry
            });

            wss.clients.forEach(client => {
                if (client.readyState === WebSocket.OPEN) {
                    client.send(packet);
                }
            });
        }

    } catch (error) {
        console.error('[BFF] Loop Warning:', error.message);
    }

    // Schedule next beat (1 second)
    setTimeout(telemetryLoop, 1000);
}

// Start Loop
telemetryLoop();

// --- WebSocket Connection Handler ---
wss.on('connection', (ws) => {
    console.log('Client connected to Telemetry Stream');

    // Send immediate state
    ws.send(JSON.stringify({
        type: 'WELCOME',
        data: latestTelemetry
    }));

    ws.on('close', () => console.log('Client disconnected'));
});

// --- Start Server ---
server.listen(PORT, '0.0.0.0', () => {
    console.log(`BFF Server listening on port ${PORT}`);
});
