-- Создание тестовой компании для локального тестирования AI-Admin
-- Выполните этот скрипт после применения schema.sql

-- 1. Создать тестовую компанию
INSERT INTO companies (id, name, email, phone, subscription_plan, created_at)
VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'Тестовый Салон Красоты',
    'test@salon-krasoty.ru',
    '+7 (495) 123-45-67',
    'trial',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- 2. Добавить настройки CRM (заглушка - для тестирования не используется реальная CRM)
INSERT INTO company_crm_settings (id, company_id, crm_type, api_key_encrypted, base_url, additional_settings)
VALUES (
    gen_random_uuid(),
    '550e8400-e29b-41d4-a716-446655440000',
    'bitrix24',  -- Тип CRM (для тестирования не важен)
    'dummy_api_key_for_testing',  -- Заглушка API ключа
    'https://test.bitrix24.ru',
    '{}'::jsonb
) ON CONFLICT DO NOTHING;

-- 3. Добавить настройки AI агента с описанием бизнеса
INSERT INTO company_agent_settings (
    id,
    company_id,
    company_description,
    business_type,
    target_audience,
    working_hours,
    business_highlights,
    services_catalog,
    products_catalog,
    custom_prompts
)
VALUES (
    gen_random_uuid(),
    '550e8400-e29b-41d4-a716-446655440000',
    'Премиальный салон красоты в центре Москвы. Мы предлагаем полный спектр услуг для ухода за волосами, ногтями и кожей.',
    'Салон красоты',
    'Женщины 25-45 лет, средний и высокий доход, ценящие качество и профессионализм',
    '{"monday": "10:00-20:00", "tuesday": "10:00-20:00", "wednesday": "10:00-20:00", "thursday": "10:00-20:00", "friday": "10:00-20:00", "saturday": "11:00-19:00", "sunday": "выходной"}',
    'Мастера с опытом работы 10+ лет, используем профессиональную косметику премиум-класса (Kerastase, Olaplex, CND), индивидуальный подход к каждому клиенту',
    -- Каталог услуг
    '[
        {
            "id": "service_1",
            "name": "Стрижка женская",
            "description": "Стрижка любой сложности от опытного мастера. Включает консультацию, мытье головы и укладку",
            "price": 2500,
            "duration": 60,
            "category": "Волосы"
        },
        {
            "id": "service_2",
            "name": "Окрашивание волос",
            "description": "Профессиональное окрашивание премиум красками. Техники: однотонное, балаяж, шатуш, омбре",
            "price": 5000,
            "duration": 180,
            "category": "Волосы"
        },
        {
            "id": "service_3",
            "name": "Маникюр с покрытием",
            "description": "Аппаратный маникюр с покрытием гель-лаком CND. Стойкость до 3 недель",
            "price": 2000,
            "duration": 90,
            "category": "Ногти"
        },
        {
            "id": "service_4",
            "name": "Педикюр с покрытием",
            "description": "Аппаратный педикюр с покрытием гель-лаком. Включает уход за стопами",
            "price": 2500,
            "duration": 120,
            "category": "Ногти"
        },
        {
            "id": "service_5",
            "name": "Наращивание ресниц",
            "description": "Наращивание ресниц классика или 2D-3D. Натуральный эффект, держится до 4 недель",
            "price": 3000,
            "duration": 120,
            "category": "Ресницы"
        },
        {
            "id": "service_6",
            "name": "Уход за лицом",
            "description": "Профессиональный уход: чистка, массаж, маска. Подбор по типу кожи",
            "price": 3500,
            "duration": 90,
            "category": "Лицо"
        }
    ]'::jsonb,
    -- Каталог товаров (опционально)
    '[
        {
            "id": "product_1",
            "name": "Шампунь Kerastase",
            "description": "Профессиональный шампунь для восстановления волос",
            "price": 2200,
            "category": "Уход за волосами"
        },
        {
            "id": "product_2",
            "name": "Масло для волос Olaplex",
            "description": "Восстанавливающее масло для поврежденных волос",
            "price": 3500,
            "category": "Уход за волосами"
        },
        {
            "id": "product_3",
            "name": "Крем для рук CND",
            "description": "Питательный крем для рук и кутикулы",
            "price": 800,
            "category": "Уход за руками"
        }
    ]'::jsonb,
    -- Кастомные промпты (опционально)
    '{
        "greeting": "Здравствуйте! Рада приветствовать вас в нашем салоне красоты. Меня зовут Анна, я виртуальный администратор. Чем могу помочь?",
        "closing": "Благодарю за обращение! Буду рада видеть вас в нашем салоне. Хорошего дня!"
    }'::jsonb
) ON CONFLICT DO NOTHING;

-- 4. Добавить Telegram канал с webhook токеном
INSERT INTO company_channels (
    id,
    company_id,
    channel_type,
    is_active,
    webhook_token,
    config
)
VALUES (
    gen_random_uuid(),
    '550e8400-e29b-41d4-a716-446655440000',
    'telegram',
    true,
    'test-webhook-token-123',  -- ⚠️ ВАЖНО: Этот токен нужно указать в .env как WEBHOOK_TOKEN
    '{
        "bot_username": "ai_admin_test_bot",
        "bot_name": "AI Admin Test Bot"
    }'::jsonb
) ON CONFLICT DO NOTHING;

-- 5. Проверка: выводим созданные данные
SELECT '========================================' as separator;
SELECT '✅ Тестовая компания успешно создана!' as status;
SELECT '========================================' as separator;

SELECT
    c.id as company_id,
    c.name AS company_name,
    c.subscription_plan,
    ch.channel_type,
    ch.webhook_token,
    ch.is_active
FROM companies c
JOIN company_channels ch ON ch.company_id = c.id
WHERE c.id = '550e8400-e29b-41d4-a716-446655440000';

SELECT '========================================' as separator;
SELECT '⚠️  ВАЖНО: Добавьте в .env файл:' as reminder;
SELECT '   WEBHOOK_TOKEN=test-webhook-token-123' as instruction;
SELECT '========================================' as separator;
