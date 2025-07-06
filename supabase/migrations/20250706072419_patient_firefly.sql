-- جداول قاعدة البيانات لبوت XP والكلانات

-- جدول المستخدمين
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    xp BIGINT DEFAULT 0,
    level INT DEFAULT 1,
    messages_count BIGINT DEFAULT 0,
    last_message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    clan_id INT DEFAULT NULL,
    clan_role VARCHAR(50) DEFAULT 'member',
    language VARCHAR(10) DEFAULT 'ar',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (clan_id) REFERENCES clans(id) ON DELETE SET NULL
);

-- جدول الكلانات
CREATE TABLE IF NOT EXISTS clans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    leader_id BIGINT NOT NULL,
    total_xp BIGINT DEFAULT 0,
    member_count INT DEFAULT 1,
    max_members INT DEFAULT 50,
    clan_level INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (leader_id) REFERENCES users(user_id)
);

-- جدول حروب الكلانات
CREATE TABLE IF NOT EXISTS clan_wars (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clan1_id INT NOT NULL,
    clan2_id INT NOT NULL,
    clan1_score BIGINT DEFAULT 0,
    clan2_score BIGINT DEFAULT 0,
    status ENUM('pending', 'active', 'finished') DEFAULT 'pending',
    start_time TIMESTAMP NULL,
    end_time TIMESTAMP NULL,
    winner_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (clan1_id) REFERENCES clans(id),
    FOREIGN KEY (clan2_id) REFERENCES clans(id),
    FOREIGN KEY (winner_id) REFERENCES clans(id)
);

-- جدول تحديات الكلانات
CREATE TABLE IF NOT EXISTS clan_challenges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clan_id INT NOT NULL,
    challenge_type VARCHAR(50) NOT NULL,
    target_value BIGINT NOT NULL,
    current_value BIGINT DEFAULT 0,
    reward_xp BIGINT NOT NULL,
    status ENUM('active', 'completed', 'expired') DEFAULT 'active',
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (clan_id) REFERENCES clans(id)
);

-- جدول سجل XP
CREATE TABLE IF NOT EXISTS xp_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    xp_gained BIGINT NOT NULL,
    reason VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- جدول الإعدادات
CREATE TABLE IF NOT EXISTS bot_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- جدول المكافآت
CREATE TABLE IF NOT EXISTS rewards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level_required INT NOT NULL,
    reward_type VARCHAR(50) NOT NULL,
    reward_value VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- إدراج الإعدادات الافتراضية
INSERT IGNORE INTO bot_settings (setting_key, setting_value) VALUES
('xp_per_message', '10'),
('xp_cooldown_seconds', '60'),
('max_clan_members', '50'),
('war_duration_hours', '24'),
('challenge_duration_hours', '168');

-- إدراج المكافآت الافتراضية
INSERT IGNORE INTO rewards (level_required, reward_type, reward_value, description) VALUES
(5, 'title', 'مبتدئ نشيط', 'لقب للوصول للمستوى 5'),
(10, 'xp_bonus', '50', 'مكافأة XP إضافية'),
(15, 'title', 'محارب متمرس', 'لقب للوصول للمستوى 15'),
(20, 'xp_bonus', '100', 'مكافأة XP كبيرة'),
(25, 'title', 'أسطورة الكلان', 'لقب للوصول للمستوى 25'),
(30, 'special', 'clan_leader_bonus', 'مكافأة خاصة لقادة الكلانات');

-- فهارس لتحسين الأداء
CREATE INDEX idx_users_xp ON users(xp DESC);
CREATE INDEX idx_users_clan ON users(clan_id);
CREATE INDEX idx_clans_xp ON clans(total_xp DESC);
CREATE INDEX idx_xp_logs_user ON xp_logs(user_id);
CREATE INDEX idx_clan_wars_status ON clan_wars(status);