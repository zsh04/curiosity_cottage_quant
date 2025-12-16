const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const cors = require('cors');

const app = express();
const PORT = 3000;
const ENGINE_URL = process.env.ENGINE_URL || 'http://cc_engine:8000';

app.use(cors());

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'cc_gateway' });
});

// Proxy API requests to Engine
app.use('/api', createProxyMiddleware({
    target: ENGINE_URL,
    changeOrigin: true,
    pathRewrite: {
        '^/api': '/api', // keep /api prefix or remove it depending on Engine route. Engine has /api base path.
    },
    onProxyReq: (proxyReq, req, res) => {
        console.log(`[Proxy] ${req.method} ${req.path} -> ${ENGINE_URL}/api${req.path}`);
    }
}));

app.listen(PORT, () => {
    console.log(`BFF Gateway running on port ${PORT}`);
    console.log(`Proxying /api to ${ENGINE_URL}`);
});
