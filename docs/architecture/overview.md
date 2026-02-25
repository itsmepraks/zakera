# Zakera System Architecture

## Overview

Zakera is built as a modern, cloud-native microservices architecture with a focus on scalability, observability, and maintainability.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  Web Browser  │  Mobile App  │  API Clients  │  CLI Tools      │
└────────┬────────────┬──────────────┬─────────────────┬──────────┘
         │            │              │                 │
         └────────────┴──────────────┴─────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Load Balancer   │
                    │   (NGINX/Ingress) │
                    └─────────┬─────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    ┌────▼─────┐      ┌──────▼──────┐      ┌─────▼─────┐
    │ Frontend │      │   API       │      │ WebSocket │
    │ (React)  │      │ (FastAPI)   │      │  Server   │
    └──────────┘      └──────┬──────┘      └─────┬─────┘
                              │                    │
                    ┌─────────┴────────────────────┘
                    │
         ┌──────────┼──────────────────────┐
         │          │                      │
    ┌────▼────┐ ┌──▼──────┐        ┌─────▼──────┐
    │ Auth    │ │ Convo   │        │ Model      │
    │ Service │ │ Service │        │ Manager    │
    └────┬────┘ └──┬──────┘        └─────┬──────┘
         │          │                     │
         └──────────┴─────────────────────┘
                    │
         ┌──────────┼──────────────────────┐
         │          │                      │
    ┌────▼────┐ ┌──▼──────┐        ┌─────▼──────┐
    │Database │ │ Redis   │        │ External   │
    │(SQLite/ │ │ Cache   │        │ LLM APIs   │
    │Postgres)│ └─────────┘        └────────────┘
    └─────────┘

         Observability Layer
    ┌─────────────────────────────┐
    │ Jaeger  │ Prometheus │ Logs │
    └─────────────────────────────┘
```

## Component Details

Refer to [components.md](components.md) for detailed component documentation.

## Data Flow

Refer to [data-flow.md](data-flow.md) for request flow diagrams.

## Technology Stack

See [technology-stack.md](technology-stack.md) for complete stack details.
