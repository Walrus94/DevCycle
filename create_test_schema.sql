-- Create test database schema for DevCycle
-- Extracted from Alembic migration 001_fastapi_users_schema.py

-- Create user table (FastAPI Users base table) with all fields
CREATE TABLE "user" (
    "id" UUID NOT NULL,
    "email" VARCHAR(320) NOT NULL,
    "hashed_password" VARCHAR(1024) NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
    "is_superuser" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_verified" BOOLEAN NOT NULL DEFAULT FALSE,
    "first_name" VARCHAR(100),
    "last_name" VARCHAR(100),
    "role" VARCHAR(50) NOT NULL DEFAULT 'user',
    PRIMARY KEY ("id")
);

-- Create indexes for user table
CREATE INDEX "ix_user_email" ON "user" ("email");
CREATE UNIQUE INDEX "ix_user_id" ON "user" ("id");
CREATE INDEX "ix_user_role" ON "user" ("role");

-- Create audit_logs table (non-auth related)
CREATE TABLE "audit_logs" (
    "id" SERIAL NOT NULL,
    "user_id" UUID,
    "action" VARCHAR(100) NOT NULL,
    "resource" VARCHAR(100) NOT NULL,
    "resource_id" VARCHAR(100),
    "details" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY ("id")
);

-- Create indexes for audit_logs table
CREATE INDEX "ix_audit_logs_action" ON "audit_logs" ("action");
CREATE INDEX "ix_audit_logs_resource" ON "audit_logs" ("resource");
CREATE INDEX "ix_audit_logs_user_id" ON "audit_logs" ("user_id");

-- Create agents table
CREATE TABLE "agents" (
    "id" UUID NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "agent_type" VARCHAR(50) NOT NULL,
    "description" TEXT,
    "version" VARCHAR(20) NOT NULL,
    "capabilities" TEXT NOT NULL,  -- JSON string
    "configuration" TEXT NOT NULL,  -- JSON string
    "metadata_json" TEXT NOT NULL,  -- JSON string
    "status" VARCHAR(20) NOT NULL DEFAULT 'offline',
    "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
    "last_heartbeat" TIMESTAMP WITH TIME ZONE,
    "response_time_ms" INTEGER,
    "error_count" INTEGER NOT NULL DEFAULT 0,
    "last_error" TEXT,
    "uptime_seconds" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    "last_seen" TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY ("id")
);

-- Create indexes for agents table
CREATE UNIQUE INDEX "ix_agents_id" ON "agents" ("id");
CREATE UNIQUE INDEX "ix_agents_name" ON "agents" ("name");
CREATE INDEX "ix_agents_agent_type" ON "agents" ("agent_type");
CREATE INDEX "ix_agents_status" ON "agents" ("status");

-- Create agent_tasks table
CREATE TABLE "agent_tasks" (
    "id" UUID NOT NULL,
    "agent_id" UUID NOT NULL,
    "task_type" VARCHAR(100) NOT NULL,
    "status" VARCHAR(50) NOT NULL,
    "parameters" TEXT NOT NULL,  -- JSON string
    "result" TEXT,  -- JSON string
    "error" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    "started_at" TIMESTAMP WITH TIME ZONE,
    "completed_at" TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY ("id")
);

-- Create indexes for agent_tasks table
CREATE UNIQUE INDEX "ix_agent_tasks_id" ON "agent_tasks" ("id");
CREATE INDEX "ix_agent_tasks_agent_id" ON "agent_tasks" ("agent_id");
CREATE INDEX "ix_agent_tasks_task_type" ON "agent_tasks" ("task_type");
CREATE INDEX "ix_agent_tasks_status" ON "agent_tasks" ("status");
