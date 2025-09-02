# System Architecture Diagrams

This document contains comprehensive system architecture diagrams for the DevCycle platform, providing visual representations of the system's structure, data flow, and component interactions.

## System Overview

### High-Level System Architecture

```mermaid
graph TB
    subgraph "External Users"
        DEV[Developers]
        ADMIN[System Administrators]
        API_USERS[API Consumers]
    end

    subgraph "Client Interfaces"
        WEB[Web Dashboard]
        CLI[Command Line Interface]
        API_CLIENT[API Clients]
        MOBILE[Mobile App]
    end

    subgraph "API Gateway Layer"
        LB[Load Balancer]
        GATEWAY[FastAPI Gateway]
        AUTH[Authentication Service]
        RATE_LIMIT[Rate Limiting]
        CORS[CORS Handler]
    end

    subgraph "Application Services"
        AGENT_MGR[Agent Manager]
        WORKFLOW[Workflow Engine]
        MESSAGE_HANDLER[Message Handler]
        SESSION_MGR[Session Manager]
        USER_MGR[User Manager]
    end

    subgraph "Agent Runtime"
        AGENT_EXEC[Agent Executor]
        AGENT_REGISTRY[Agent Registry]
        AGENT_SCHEDULER[Agent Scheduler]
        AGENT_MONITOR[Agent Monitor]
    end

    subgraph "Data Layer"
        POSTGRES[(PostgreSQL)]
        REDIS[(Redis Cache)]
        KAFKA[Kafka Messaging]
        FILES[File Storage]
    end

    subgraph "External Integrations"
        HF[Hugging Face Spaces]
        DOCKER[Docker Registry]
        GIT[Git Repositories]
        CI_CD[CI/CD Systems]
    end

    subgraph "Monitoring & Observability"
        METRICS[Metrics Collector]
        LOGS[Log Aggregator]
        ALERTS[Alert Manager]
        DASHBOARD[Monitoring Dashboard]
    end

    %% User connections
    DEV --> WEB
    DEV --> CLI
    ADMIN --> WEB
    API_USERS --> API_CLIENT

    %% Client to Gateway
    WEB --> LB
    CLI --> LB
    API_CLIENT --> LB
    MOBILE --> LB

    %% Gateway layer
    LB --> GATEWAY
    GATEWAY --> AUTH
    GATEWAY --> RATE_LIMIT
    GATEWAY --> CORS

    %% Gateway to Services
    GATEWAY --> AGENT_MGR
    GATEWAY --> WORKFLOW
    GATEWAY --> MESSAGE_HANDLER
    GATEWAY --> SESSION_MGR
    GATEWAY --> USER_MGR

    %% Services to Agent Runtime
    AGENT_MGR --> AGENT_EXEC
    AGENT_MGR --> AGENT_REGISTRY
    WORKFLOW --> AGENT_SCHEDULER
    AGENT_MGR --> AGENT_MONITOR

    %% Data connections
    AGENT_MGR --> POSTGRES
    SESSION_MGR --> REDIS
    MESSAGE_HANDLER --> KAFKA
    USER_MGR --> POSTGRES
    AGENT_REGISTRY --> POSTGRES

    %% External integrations
    AGENT_EXEC --> HF
    AGENT_EXEC --> DOCKER
    AGENT_EXEC --> GIT
    WORKFLOW --> CI_CD

    %% Monitoring connections
    METRICS --> GATEWAY
    METRICS --> AGENT_EXEC
    METRICS --> POSTGRES
    METRICS --> REDIS
    METRICS --> KAFKA

    LOGS --> GATEWAY
    LOGS --> AGENT_EXEC
    LOGS --> AGENT_MGR

    ALERTS --> METRICS
    DASHBOARD --> METRICS
    DASHBOARD --> LOGS
```

## Component Architecture

### Detailed Component View

```mermaid
graph TB
    subgraph "API Gateway Components"
        subgraph "FastAPI Gateway"
            ROUTER[Router]
            MIDDLEWARE[Middleware Stack]
            VALIDATION[Request Validation]
            SERIALIZATION[Response Serialization]
        end

        subgraph "Security Layer"
            JWT_AUTH[JWT Authentication]
            TOKEN_BLACKLIST[Token Blacklist]
            RBAC[Role-Based Access Control]
            CSRF[CSRF Protection]
        end

        subgraph "Rate Limiting"
            RATE_COUNTER[Rate Counter]
            THROTTLE[Throttling Logic]
            QUOTA[Quota Management]
        end
    end

    subgraph "Application Layer Components"
        subgraph "Agent Manager"
            AGENT_CRUD[Agent CRUD Operations]
            AGENT_DEPLOY[Agent Deployment]
            AGENT_CONFIG[Configuration Management]
            AGENT_VERSION[Version Control]
        end

        subgraph "Workflow Engine"
            WORKFLOW_DEF[Workflow Definition]
            TASK_ORCHESTRATOR[Task Orchestrator]
            DEPENDENCY_MGR[Dependency Manager]
            ERROR_HANDLER[Error Handler]
        end

        subgraph "Message Handler"
            MESSAGE_ROUTER[Message Router]
            MESSAGE_QUEUE[Message Queue]
            DEAD_LETTER[Dead Letter Queue]
            MESSAGE_PERSIST[Message Persistence]
        end
    end

    subgraph "Agent Runtime Components"
        subgraph "Agent Executor"
            CONTAINER_MGR[Container Manager]
            RESOURCE_MGR[Resource Manager]
            EXECUTION_ENGINE[Execution Engine]
            ISOLATION[Isolation Layer]
        end

        subgraph "Agent Registry"
            AGENT_METADATA[Agent Metadata]
            CAPABILITY_REG[Capability Registry]
            DEPENDENCY_REG[Dependency Registry]
            COMPATIBILITY[Compatibility Checker]
        end
    end

    %% Connections
    ROUTER --> MIDDLEWARE
    MIDDLEWARE --> VALIDATION
    VALIDATION --> SERIALIZATION

    JWT_AUTH --> TOKEN_BLACKLIST
    JWT_AUTH --> RBAC
    RBAC --> CSRF

    RATE_COUNTER --> THROTTLE
    THROTTLE --> QUOTA

    AGENT_CRUD --> AGENT_DEPLOY
    AGENT_DEPLOY --> AGENT_CONFIG
    AGENT_CONFIG --> AGENT_VERSION

    WORKFLOW_DEF --> TASK_ORCHESTRATOR
    TASK_ORCHESTRATOR --> DEPENDENCY_MGR
    DEPENDENCY_MGR --> ERROR_HANDLER

    MESSAGE_ROUTER --> MESSAGE_QUEUE
    MESSAGE_QUEUE --> DEAD_LETTER
    MESSAGE_QUEUE --> MESSAGE_PERSIST

    CONTAINER_MGR --> RESOURCE_MGR
    RESOURCE_MGR --> EXECUTION_ENGINE
    EXECUTION_ENGINE --> ISOLATION

    AGENT_METADATA --> CAPABILITY_REG
    CAPABILITY_REG --> DEPENDENCY_REG
    DEPENDENCY_REG --> COMPATIBILITY
```

## Data Architecture

### Database Schema Overview

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : has
    USERS ||--o{ AGENTS : owns
    USERS ||--o{ WORKFLOWS : creates

    AGENTS ||--o{ TASKS : executes
    AGENTS ||--o{ MESSAGES : sends
    AGENTS ||--o{ MESSAGES : receives

    WORKFLOWS ||--o{ TASKS : contains
    TASKS ||--o{ TASK_LOGS : generates

    USERS {
        uuid id PK
        string email UK
        string username UK
        string password_hash
        string role
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    SESSIONS {
        uuid id PK
        uuid user_id FK
        string session_token UK
        json session_data
        timestamp expires_at
        timestamp created_at
        timestamp last_accessed
    }

    AGENTS {
        uuid id PK
        uuid owner_id FK
        string name
        string type
        string status
        json configuration
        json capabilities
        string version
        timestamp created_at
        timestamp updated_at
        timestamp last_heartbeat
    }

    WORKFLOWS {
        uuid id PK
        uuid creator_id FK
        string name
        string description
        json workflow_definition
        string status
        timestamp created_at
        timestamp updated_at
        timestamp started_at
        timestamp completed_at
    }

    TASKS {
        uuid id PK
        uuid workflow_id FK
        uuid agent_id FK
        string name
        string type
        string status
        json input_data
        json output_data
        json error_data
        integer priority
        timestamp created_at
        timestamp started_at
        timestamp completed_at
    }

    MESSAGES {
        uuid id PK
        uuid sender_id FK
        uuid recipient_id FK
        string message_type
        json payload
        string status
        timestamp created_at
        timestamp delivered_at
        timestamp read_at
    }

    TASK_LOGS {
        uuid id PK
        uuid task_id FK
        string log_level
        string message
        json context
        timestamp created_at
    }
```

### Data Flow Architecture

```mermaid
graph LR
    subgraph "Data Sources"
        API_REQUESTS[API Requests]
        USER_INPUT[User Input]
        AGENT_OUTPUT[Agent Output]
        SYSTEM_EVENTS[System Events]
    end

    subgraph "Data Processing"
        VALIDATION[Data Validation]
        TRANSFORMATION[Data Transformation]
        ENRICHMENT[Data Enrichment]
        AGGREGATION[Data Aggregation]
    end

    subgraph "Data Storage"
        POSTGRES[(PostgreSQL)]
        REDIS[(Redis Cache)]
        KAFKA[Kafka Topics]
        FILES[File Storage]
    end

    subgraph "Data Consumption"
        API_RESPONSES[API Responses]
        DASHBOARDS[Dashboards]
        REPORTS[Reports]
        ANALYTICS[Analytics]
    end

    %% Data flow
    API_REQUESTS --> VALIDATION
    USER_INPUT --> VALIDATION
    AGENT_OUTPUT --> TRANSFORMATION
    SYSTEM_EVENTS --> ENRICHMENT

    VALIDATION --> POSTGRES
    TRANSFORMATION --> REDIS
    ENRICHMENT --> KAFKA
    AGGREGATION --> FILES

    POSTGRES --> API_RESPONSES
    REDIS --> DASHBOARDS
    KAFKA --> REPORTS
    FILES --> ANALYTICS
```

## Security Architecture

### Security Layer Diagram

```mermaid
graph TB
    subgraph "External Threats"
        MALICIOUS[Malicious Users]
        BOTS[Automated Bots]
        ATTACKS[Network Attacks]
    end

    subgraph "Security Perimeter"
        FIREWALL[Network Firewall]
        WAF[Web Application Firewall]
        DDoS[DDoS Protection]
    end

    subgraph "Application Security"
        AUTH_LAYER[Authentication Layer]
        AUTHZ_LAYER[Authorization Layer]
        INPUT_VALIDATION[Input Validation]
        OUTPUT_SANITIZATION[Output Sanitization]
    end

    subgraph "Data Security"
        ENCRYPTION[Data Encryption]
        ACCESS_CONTROL[Access Control]
        AUDIT_LOGS[Audit Logging]
        BACKUP[Secure Backup]
    end

    subgraph "Infrastructure Security"
        CONTAINER_SEC[Container Security]
        NETWORK_SEC[Network Security]
        SECRETS_MGR[Secrets Management]
        VULN_SCAN[Vulnerability Scanning]
    end

    %% Threat mitigation
    MALICIOUS --> FIREWALL
    BOTS --> WAF
    ATTACKS --> DDoS

    %% Security layers
    FIREWALL --> AUTH_LAYER
    WAF --> AUTHZ_LAYER
    DDoS --> INPUT_VALIDATION

    AUTH_LAYER --> ENCRYPTION
    AUTHZ_LAYER --> ACCESS_CONTROL
    INPUT_VALIDATION --> AUDIT_LOGS
    OUTPUT_SANITIZATION --> BACKUP

    ENCRYPTION --> CONTAINER_SEC
    ACCESS_CONTROL --> NETWORK_SEC
    AUDIT_LOGS --> SECRETS_MGR
    BACKUP --> VULN_SCAN
```

## Deployment Architecture

### Development Environment

```mermaid
graph TB
    subgraph "Developer Machine"
        IDE[IDE/Editor]
        TERMINAL[Terminal]
        BROWSER[Browser]
    end

    subgraph "Local Services"
        DOCKER_COMPOSE[Docker Compose]
        POSTGRES_LOCAL[(PostgreSQL Local)]
        REDIS_LOCAL[(Redis Local)]
        KAFKA_LOCAL[Kafka Local]
        API_LOCAL[FastAPI Local]
    end

    subgraph "Development Tools"
        POETRY[Poetry]
        PRE_COMMIT[Pre-commit Hooks]
        TESTS[Test Suite]
        LINTERS[Code Linters]
    end

    IDE --> DOCKER_COMPOSE
    TERMINAL --> POETRY
    BROWSER --> API_LOCAL

    DOCKER_COMPOSE --> POSTGRES_LOCAL
    DOCKER_COMPOSE --> REDIS_LOCAL
    DOCKER_COMPOSE --> KAFKA_LOCAL
    DOCKER_COMPOSE --> API_LOCAL

    POETRY --> PRE_COMMIT
    PRE_COMMIT --> TESTS
    TESTS --> LINTERS
```

### Production Environment (Future)

```mermaid
graph TB
    subgraph "Load Balancer Tier"
        LB[Load Balancer]
        SSL[SSL Termination]
        CDN[Content Delivery Network]
    end

    subgraph "Application Tier"
        API1[API Instance 1]
        API2[API Instance 2]
        API3[API Instance N]
    end

    subgraph "Data Tier"
        POSTGRES_PRIMARY[(PostgreSQL Primary)]
        POSTGRES_REPLICA1[(PostgreSQL Replica 1)]
        POSTGRES_REPLICA2[(PostgreSQL Replica 2)]
        REDIS_CLUSTER[(Redis Cluster)]
        KAFKA_CLUSTER[Kafka Cluster]
    end

    subgraph "Monitoring Tier"
        PROMETHEUS[Prometheus]
        GRAFANA[Grafana]
        ALERTMANAGER[AlertManager]
        JAEGER[Jaeger Tracing]
    end

    subgraph "External Services"
        HF_PROD[Hugging Face Production]
        DOCKER_REGISTRY[Docker Registry]
        SECRETS_VAULT[Secrets Vault]
    end

    %% Load balancer connections
    LB --> API1
    LB --> API2
    LB --> API3

    %% Application to data
    API1 --> POSTGRES_PRIMARY
    API2 --> POSTGRES_PRIMARY
    API3 --> POSTGRES_PRIMARY

    POSTGRES_PRIMARY --> POSTGRES_REPLICA1
    POSTGRES_PRIMARY --> POSTGRES_REPLICA2

    API1 --> REDIS_CLUSTER
    API2 --> REDIS_CLUSTER
    API3 --> REDIS_CLUSTER

    API1 --> KAFKA_CLUSTER
    API2 --> KAFKA_CLUSTER
    API3 --> KAFKA_CLUSTER

    %% Monitoring connections
    PROMETHEUS --> API1
    PROMETHEUS --> API2
    PROMETHEUS --> API3
    PROMETHEUS --> POSTGRES_PRIMARY
    PROMETHEUS --> REDIS_CLUSTER
    PROMETHEUS --> KAFKA_CLUSTER

    GRAFANA --> PROMETHEUS
    ALERTMANAGER --> PROMETHEUS
    JAEGER --> API1
    JAEGER --> API2
    JAEGER --> API3

    %% External service connections
    API1 --> HF_PROD
    API2 --> HF_PROD
    API3 --> HF_PROD

    API1 --> DOCKER_REGISTRY
    API2 --> DOCKER_REGISTRY
    API3 --> DOCKER_REGISTRY

    API1 --> SECRETS_VAULT
    API2 --> SECRETS_VAULT
    API3 --> SECRETS_VAULT
```

## Agent Communication Patterns

### Inter-Agent Communication

```mermaid
sequenceDiagram
    participant BA as Business Analyst
    participant WM as Workflow Manager
    participant CG as Code Generator
    participant TE as Test Engineer
    participant DE as Deployment Engineer
    participant KAFKA as Kafka Message Bus

    BA->>WM: Requirements Analysis Complete
    WM->>KAFKA: Publish Workflow Event
    KAFKA->>CG: Deliver Code Generation Task
    CG->>KAFKA: Publish Code Generated Event
    KAFKA->>TE: Deliver Testing Task
    TE->>KAFKA: Publish Test Results
    KAFKA->>DE: Deliver Deployment Task
    DE->>KAFKA: Publish Deployment Status
    KAFKA->>WM: Deliver Workflow Complete Event
    WM->>BA: Notify Workflow Completion
```

## Next Steps

- **[Architecture Overview](overview.md)** - Return to main architecture overview
- **[Agent System Architecture](agent-system.md)** - Detailed agent system design
- **[Security Architecture](security.md)** - Comprehensive security design
- **[Project Structure](../getting-started/project-structure.md)** - Codebase organization
