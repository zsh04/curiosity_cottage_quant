
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { Resource } from '@opentelemetry/resources';
import { SEMRESATTRS_SERVICE_NAME } from '@opentelemetry/semantic-conventions';

const enableTelemetry = () => {
    const provider = new WebTracerProvider({
        resource: new Resource({
            [SEMRESATTRS_SERVICE_NAME]: 'cc-frontend',
        }),
    });

    // Exporter to OpenTelemetry Collector (Direct via CORS)
    const collectorExporter = new OTLPTraceExporter({
        url: 'http://localhost:4318/v1/traces', // Requires CORS enabled on Collector
    });

    provider.addSpanProcessor(new BatchSpanProcessor(collectorExporter));

    // Optional: Console Exporter for Dev Debugging
    if (import.meta.env.DEV) {
        provider.addSpanProcessor(new SimpleSpanProcessor(new ConsoleSpanExporter()));
    }

    provider.register({
        contextManager: new ZoneContextManager(),
    });

    // Register Instrumentations (Document Load, XHR/Fetch, User Interaction)
    registerInstrumentations({
        instrumentations: [
            getWebAutoInstrumentations({
                // Disable noisy instrumentations if needed
                '@opentelemetry/instrumentation-document-load': {},
                '@opentelemetry/instrumentation-user-interaction': {},
                '@opentelemetry/instrumentation-xml-http-request': {},
                '@opentelemetry/instrumentation-fetch': {},
            }),
        ],
    });

    console.log('📡 Browser Telemetry Initialized');
};

enableTelemetry();
