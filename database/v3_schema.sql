-- ============================================================
-- SCRIPT SQL PARA EXPANSIÓN V3 - NUEVAS TABLAS
-- ============================================================

-- Tabla para historial de engagement en Twitter (likes y comentarios)
CREATE TABLE IF NOT EXISTS twitter_engagement_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id VARCHAR(255) UNIQUE NOT NULL,
    post_url TEXT,
    action_type ENUM('like', 'comment', 'both') NOT NULL,
    comment_text TEXT,
    topic VARCHAR(100),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_topic (topic)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabla para controlar ciclos de engagement
CREATE TABLE IF NOT EXISTS engagement_cycles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cycle_start DATETIME NOT NULL,
    cycle_end DATETIME,
    interactions_count INT DEFAULT 0,
    next_allowed_cycle DATETIME,
    status ENUM(
        'running',
        'completed',
        'failed'
    ) DEFAULT 'running',
    INDEX idx_cycle_start (cycle_start)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabla para pool de keywords de búsqueda en Twitter
CREATE TABLE IF NOT EXISTS keyword_pool (
    id INT AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50),
    language ENUM('es', 'en', 'both') DEFAULT 'both',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_language (language)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabla para historial de búsquedas de keywords
CREATE TABLE IF NOT EXISTS keyword_search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL,
    searched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    results_found INT DEFAULT 0,
    interactions_made INT DEFAULT 0,
    INDEX idx_keyword (keyword),
    INDEX idx_searched_at (searched_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabla para snapshots de precios (monitoreo continuo)
CREATE TABLE IF NOT EXISTS price_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 2),
    market_type ENUM(
        'crypto',
        'stock',
        'forex',
        'commodity'
    ) DEFAULT 'crypto',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_timestamp (symbol, timestamp),
    INDEX idx_market_type (market_type)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabla para detectar nuevos pares de trading
CREATE TABLE IF NOT EXISTS new_pairs_detected (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    exchange VARCHAR(50) DEFAULT 'binance',
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    first_price DECIMAL(20, 8),
    notified BOOLEAN DEFAULT FALSE,
    INDEX idx_detected_at (detected_at),
    INDEX idx_notified (notified)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabla para historial de noticias
CREATE TABLE IF NOT EXISTS news_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    news_hash VARCHAR(64) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    source VARCHAR(100),
    summary TEXT,
    published_at DATETIME,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    relevance_score FLOAT DEFAULT 0,
    category VARCHAR(50),
    published_to_socials BOOLEAN DEFAULT FALSE,
    INDEX idx_news_hash (news_hash),
    INDEX idx_published_at (published_at),
    INDEX idx_relevance_score (relevance_score)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabla para alertas de precio (pumps/dumps)
CREATE TABLE IF NOT EXISTS price_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    alert_type ENUM('pump', 'dump') NOT NULL,
    price_before DECIMAL(20, 8) NOT NULL,
    price_after DECIMAL(20, 8) NOT NULL,
    change_percent DECIMAL(10, 2) NOT NULL,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT FALSE,
    INDEX idx_symbol (symbol),
    INDEX idx_detected_at (detected_at),
    INDEX idx_notified (notified)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabla para señales de trading (análisis técnico)
CREATE TABLE IF NOT EXISTS trading_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal_type ENUM('LONG', 'SHORT', 'NEUTRAL') NOT NULL,
    entry_price DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    position_size DECIMAL(20, 8),
    atr_value DECIMAL(20, 8),
    rsi_value DECIMAL(10, 2),
    macd_value DECIMAL(20, 8),
    confidence_score FLOAT,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    image_path VARCHAR(255),
    published BOOLEAN DEFAULT FALSE,
    INDEX idx_symbol (symbol),
    INDEX idx_generated_at (generated_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ============================================================
-- INSERTAR KEYWORDS INICIALES (200 palabras)
-- ============================================================

INSERT IGNORE INTO
    keyword_pool (keyword, category, language)
VALUES
    -- Crypto Keywords (ES)
    ('bitcoin', 'crypto', 'both'),
    ('ethereum', 'crypto', 'both'),
    (
        'criptomonedas',
        'crypto',
        'es'
    ),
    ('btc', 'crypto', 'both'),
    ('eth', 'crypto', 'both'),
    ('solana', 'crypto', 'both'),
    ('cardano', 'crypto', 'both'),
    ('polkadot', 'crypto', 'both'),
    ('binance', 'crypto', 'both'),
    ('coinbase', 'crypto', 'both'),
    ('altcoins', 'crypto', 'both'),
    ('defi', 'crypto', 'both'),
    ('nft', 'crypto', 'both'),
    (
        'blockchain',
        'crypto',
        'both'
    ),
    (
        'trading crypto',
        'crypto',
        'both'
    ),
    (
        'inversión cripto',
        'crypto',
        'es'
    ),
    (
        'crypto investment',
        'crypto',
        'en'
    ),
    ('hodl', 'crypto', 'both'),
    ('bull market', 'crypto', 'en'),
    ('bear market', 'crypto', 'en'),

-- Stock Market Keywords
('acciones', 'stocks', 'es'),
(
    'bolsa valores',
    'stocks',
    'es'
),
(
    'wall street',
    'stocks',
    'both'
),
('nasdaq', 'stocks', 'both'),
('sp500', 'stocks', 'both'),
('dow jones', 'stocks', 'both'),
('apple stock', 'stocks', 'en'),
('tesla stock', 'stocks', 'en'),
(
    'microsoft stock',
    'stocks',
    'en'
),
(
    'amazon stock',
    'stocks',
    'en'
),
(
    'inversión acciones',
    'stocks',
    'es'
),
(
    'stock trading',
    'stocks',
    'en'
),
(
    'dividendos',
    'stocks',
    'both'
),
(
    'earnings report',
    'stocks',
    'en'
),
('ipo', 'stocks', 'both'),

-- Forex Keywords
('forex', 'forex', 'both'),
('divisas', 'forex', 'es'),
('eurusd', 'forex', 'both'),
('gbpusd', 'forex', 'both'),
('usdjpy', 'forex', 'both'),
(
    'trading divisas',
    'forex',
    'es'
),
(
    'currency trading',
    'forex',
    'en'
),
('fx trading', 'forex', 'en'),

-- Commodities Keywords
('oro', 'commodities', 'es'),
('plata', 'commodities', 'es'),
('gold', 'commodities', 'en'),
('silver', 'commodities', 'en'),
(
    'petróleo',
    'commodities',
    'es'
),
(
    'crude oil',
    'commodities',
    'en'
),
(
    'commodities',
    'commodities',
    'both'
),

-- General Investment Keywords
(
    'inversiones',
    'general',
    'es'
),
('investment', 'general', 'en'),
('trading', 'general', 'both'),
(
    'análisis técnico',
    'general',
    'es'
),
(
    'technical analysis',
    'general',
    'en'
),
(
    'análisis fundamental',
    'general',
    'es'
),
(
    'fundamental analysis',
    'general',
    'en'
),
(
    'estrategia trading',
    'general',
    'es'
),
(
    'trading strategy',
    'general',
    'en'
),
(
    'gestión riesgo',
    'general',
    'es'
),
(
    'risk management',
    'general',
    'en'
),
('portafolio', 'general', 'es'),
('portfolio', 'general', 'en'),
(
    'diversificación',
    'general',
    'es'
),
(
    'diversification',
    'general',
    'en'
),
(
    'rentabilidad',
    'general',
    'es'
),
(
    'profitability',
    'general',
    'en'
),
(
    'mercados financieros',
    'general',
    'es'
),
(
    'financial markets',
    'general',
    'en'
);

-- Nota: Se pueden agregar más keywords manualmente o mediante script