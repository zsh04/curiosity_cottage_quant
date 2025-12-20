import { initializeFaro, ReactIntegration, getWebInstrumentations, ReactRouterVersion } from '@grafana/faro-react';
import { TracingInstrumentation } from '@grafana/faro-web-tracing';
import { createRoutesFromChildren, matchRoutes, Routes, useLocation, useNavigationType } from 'react-router-dom';

export function initTelemetry() {
    console.log('🚀 Initializing Grafana Faro RUM...');

    initializeFaro({
        url: 'https://faro-collector-prod-us-west-0.grafana.net/collect/cd4f0144e8b7762309242d679bc6bd8f',
        app: {
            name: 'Curiosity Cottage Quant',
            version: '1.0.0',
            environment: 'development',
        },
        instrumentations: [
            // Mandatory: Captures Console logs, Errors, and Web Vitals
            ...getWebInstrumentations({
                captureConsole: true,
            }),
            // Optional: Captures Network Timing (replacing your custom API tracking)
            new TracingInstrumentation(),
            // React Integration: Tracks component errors and route changes
            new ReactIntegration({
                router: {
                    version: ReactRouterVersion.V6,
                    dependencies: {
                        createRoutesFromChildren,
                        matchRoutes,
                        Routes,
                        useLocation,
                        useNavigationType,
                    }
                }
            })
        ],
    });
}
