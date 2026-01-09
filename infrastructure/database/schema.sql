-- AI-Admin PostgreSQL Schema
-- Multi-tenant SAAS architecture

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Companies (клиенты SAAS - салоны, клиники и т.д.)
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    
    -- Subscription
    subscription_plan VARCHAR(50) DEFAULT 'free', -- free, basic, premium, enterprise
    subscription_status VARCHAR(50) DEFAULT 'active', -- active, suspended, cancelled
    subscription_expires_at TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    
    -- Billing
    billing_email VARCHAR(255)
);

CREATE INDEX idx_companies_email ON companies(email);
CREATE INDEX idx_companies_active ON companies(is_active);

-- CRM Settings для каждой компании
CREATE TABLE company_crm_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- CRM Configuration
    crm_type VARCHAR(50) NOT NULL, -- 'yclients', 'dikidi', 'bitrix24', '1c'
    api_key_encrypted TEXT NOT NULL, -- Зашифрованный API ключ
    base_url VARCHAR(500),
    company_id_in_crm VARCHAR(255), -- ID компании в CRM (для YCLIENTS)
    
    -- Additional CRM-specific settings (JSON)
    additional_settings JSONB DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_sync_at TIMESTAMP,
    last_sync_status VARCHAR(50), -- success, failed
    last_sync_error TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(company_id) -- Одна CRM на компанию (пока)
);

CREATE INDEX idx_crm_settings_company ON company_crm_settings(company_id);
CREATE INDEX idx_crm_settings_type ON company_crm_settings(crm_type);

-- Agent Settings для каждой компании
CREATE TABLE company_agent_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Company Information
    company_description TEXT,
    business_type VARCHAR(100), -- Тип бизнеса: салон красоты, фитнес, медцентр, etc
    target_audience TEXT, -- Целевая аудитория
    working_hours VARCHAR(500),
    address TEXT,
    phone_display VARCHAR(50), -- Телефон для показа клиентам

    -- Business Context (для AI агента)
    services_catalog JSONB DEFAULT '[]', -- Каталог услуг с описаниями
    products_catalog JSONB DEFAULT '[]', -- Каталог товаров с описаниями
    business_highlights TEXT, -- Ключевые преимущества бизнеса

    -- Agent Behavior
    greeting_message TEXT,
    farewell_message TEXT,
    custom_instructions TEXT, -- Особые инструкции для агента
    
    -- AI Settings
    temperature DECIMAL(3,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 8192,
    model_name VARCHAR(100) DEFAULT 'gemini-2.0-flash-exp',
    
    -- Custom Prompts (JSON)
    custom_prompts JSONB DEFAULT '{}',
    
    -- Features
    features JSONB DEFAULT '{"auto_booking": true, "consultation": true, "reminders": true}',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(company_id)
);

CREATE INDEX idx_agent_settings_company ON company_agent_settings(company_id);

-- Channels для каждой компании
CREATE TABLE company_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Channel Info
    channel_type VARCHAR(50) NOT NULL, -- 'telegram', 'whatsapp', 'voice', 'web'
    channel_name VARCHAR(255), -- Название канала для клиента
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    -- Channel-specific config (JSON)
    config JSONB DEFAULT '{}',
    
    -- Webhook
    webhook_token VARCHAR(255) UNIQUE, -- Уникальный токен для webhook URL
    webhook_url VARCHAR(500), -- Полный webhook URL
    
    -- Statistics
    messages_received INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    last_activity_at TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_channels_company ON company_channels(company_id);
CREATE INDEX idx_channels_token ON company_channels(webhook_token);
CREATE INDEX idx_channels_type ON company_channels(channel_type);

-- Sessions (привязаны к компании)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- User Info
    user_id VARCHAR(255) NOT NULL, -- ID в канале (telegram_id, phone и т.д.)
    channel VARCHAR(50) NOT NULL,
    
    -- State
    state VARCHAR(50) NOT NULL DEFAULT 'INITIATED',
    context JSONB DEFAULT '{}',
    
    -- CRM linkage
    crm_client_id VARCHAR(255), -- ID клиента в CRM компании
    crm_appointment_id VARCHAR(255), -- ID созданной записи
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP, -- TTL для автоочистки
    
    -- Index для быстрого поиска
    UNIQUE(company_id, user_id, channel)
);

CREATE INDEX idx_sessions_company ON sessions(company_id);
CREATE INDEX idx_sessions_user ON sessions(company_id, user_id, channel);
CREATE INDEX idx_sessions_last_activity ON sessions(last_activity_at);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- Messages (история сообщений)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Message Info
    channel VARCHAR(50) NOT NULL,
    message_type VARCHAR(50) DEFAULT 'text', -- text, audio, image, etc.
    
    -- Content
    text TEXT,
    audio_url VARCHAR(500),
    image_url VARCHAR(500),
    file_url VARCHAR(500),
    
    -- Sender
    is_from_bot BOOLEAN DEFAULT false,
    from_user_id VARCHAR(255),
    from_user_name VARCHAR(255),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_company ON messages(company_id);
CREATE INDEX idx_messages_created ON messages(created_at DESC);

-- Function Calls Log (для аналитики)
CREATE TABLE function_calls_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Function Info
    function_name VARCHAR(100) NOT NULL,
    arguments JSONB,
    result JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'success', -- success, failed
    error_message TEXT,
    execution_time_ms INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_function_calls_company ON function_calls_log(company_id);
CREATE INDEX idx_function_calls_created ON function_calls_log(created_at DESC);

-- API Keys для компаний (если нужно API access)
CREATE TABLE company_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) NOT NULL, -- Для показа в UI: "sk_live_abc..."
    name VARCHAR(255), -- Название ключа
    
    -- Permissions
    permissions JSONB DEFAULT '["read", "write"]',
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_api_keys_company ON company_api_keys(company_id);
CREATE INDEX idx_api_keys_hash ON company_api_keys(key_hash);

-- Analytics (агрегированная статистика)
CREATE TABLE company_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Date
    date DATE NOT NULL,
    
    -- Metrics
    sessions_created INTEGER DEFAULT 0,
    messages_received INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    appointments_created INTEGER DEFAULT 0,
    appointments_cancelled INTEGER DEFAULT 0,
    
    -- Channel breakdown (JSON)
    channel_stats JSONB DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(company_id, date)
);

CREATE INDEX idx_analytics_company_date ON company_analytics(company_id, date DESC);

-- Автоочистка expired sessions (CRON job)
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM sessions WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Обновление updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers для updated_at
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_crm_settings_updated_at BEFORE UPDATE ON company_crm_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_settings_updated_at BEFORE UPDATE ON company_agent_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_channels_updated_at BEFORE UPDATE ON company_channels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
