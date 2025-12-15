const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const upstream = process.env.UPSTREAM_API_URL || 'http://engine:8000';

app.use('/api', createProxyMiddleware({ target: upstream, changeOrigin: true }));

app.get('/', (req, res) => {
    res.send('BFF Service Operational');
});

app.listen(3000, () => {
    console.log('BFF listening on port 3000');
});
