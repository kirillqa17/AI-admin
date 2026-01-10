-- Seed Data для разработки и тестирования
-- Тестовая компания с настройками

-- 1. Тестовая компания
INSERT INTO companies (id, name, email, phone, subscription_plan, subscription_status)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Тестовый Салон Красоты',
    'test@salon.ru',
    '+79001234567',
    'premium',
    'active'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    updated_at = NOW();

-- 2. CRM настройки (Bitrix24 для тестов)
INSERT INTO company_crm_settings (
    id, company_id, crm_type, api_key_encrypted, base_url, is_active
)
VALUES (
    'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'bitrix24',
    'dummy_api_key_for_testing',
    'https://test.bitrix24.ru',
    true
) ON CONFLICT (company_id) DO UPDATE SET
    crm_type = EXCLUDED.crm_type,
    updated_at = NOW();

-- 3. Agent настройки
INSERT INTO company_agent_settings (
    id, company_id, company_description, business_type, target_audience,
    working_hours, address, phone_display, greeting_message, farewell_message,
    services_catalog, business_highlights, temperature
)
VALUES (
    'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Салон красоты премиум-класса в центре города. Предоставляем полный спектр услуг по уходу за волосами, ногтями, кожей лица и тела.',
    'salon',
    'Женщины и мужчины от 18 до 65 лет, ценящие качественный сервис и профессиональный подход',
    'Пн-Пт: 9:00-21:00, Сб-Вс: 10:00-20:00',
    'г. Москва, ул. Тверская, д. 15',
    '+7 (495) 123-45-67',
    'Здравствуйте! Добро пожаловать в наш салон красоты. Чем могу помочь?',
    'Спасибо за обращение! Будем рады видеть вас в нашем салоне!',
    '[
        {"name": "Мужская стрижка", "price": 1500, "duration": 45, "description": "Стрижка любой сложности от опытного мастера"},
        {"name": "Женская стрижка", "price": 2500, "duration": 60, "description": "Стрижка с укладкой"},
        {"name": "Окрашивание волос", "price": 5000, "duration": 120, "description": "Профессиональное окрашивание"},
        {"name": "Маникюр", "price": 1800, "duration": 60, "description": "Классический или аппаратный маникюр"},
        {"name": "Педикюр", "price": 2200, "duration": 75, "description": "Классический или аппаратный педикюр"},
        {"name": "Массаж лица", "price": 3000, "duration": 45, "description": "Расслабляющий массаж лица"}
    ]'::jsonb,
    'Более 10 лет на рынке. Только сертифицированные мастера. Используем косметику премиум-класса.',
    0.7
) ON CONFLICT (company_id) DO UPDATE SET
    company_description = EXCLUDED.company_description,
    services_catalog = EXCLUDED.services_catalog,
    updated_at = NOW();

-- 4. Telegram канал с тестовым webhook токеном
INSERT INTO company_channels (
    id, company_id, channel_type, channel_name, is_active, webhook_token, config
)
VALUES (
    'd3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'telegram',
    'Telegram Bot',
    true,
    'test-webhook-token-123',
    '{"bot_username": "aichatbot_example_bot"}'::jsonb
) ON CONFLICT (webhook_token) DO UPDATE SET
    is_active = true,
    updated_at = NOW();

-- 5. WhatsApp канал (для будущих тестов)
INSERT INTO company_channels (
    id, company_id, channel_type, channel_name, is_active, webhook_token, config
)
VALUES (
    'e4eebc99-9c0b-4ef8-bb6d-6bb9bd380a55',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'whatsapp',
    'WhatsApp Business',
    false,
    'test-whatsapp-token-456',
    '{}'::jsonb
) ON CONFLICT (webhook_token) DO UPDATE SET
    is_active = false,
    updated_at = NOW();
