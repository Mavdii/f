export const config = {
    BOT_TOKEN: process.env.BOT_TOKEN || 'YOUR_BOT_TOKEN_HERE',
    DATABASE_PATH: './data/bot.db',
    
    // XP System Configuration
    XP: {
        MESSAGE_XP: 5,
        MESSAGE_COOLDOWN: 60000, // 1 minute
        DAILY_BONUS: 50,
        WEEKLY_BONUS: 200,
        LEVEL_MULTIPLIER: 100,
        MAX_LEVEL: 100
    },

    // Clan System Configuration
    CLAN: {
        MAX_MEMBERS: 50,
        MIN_LEVEL_TO_CREATE: 10,
        MIN_LEVEL_TO_JOIN: 5,
        WAR_DURATION: 24 * 60 * 60 * 1000, // 24 hours
        CHALLENGE_DURATION: 7 * 24 * 60 * 60 * 1000 // 7 days
    },

    // Leaderboard Configuration
    LEADERBOARD: {
        TOP_COUNT: 10,
        RESET_DAY: 1, // Monday
        RESET_HOUR: 0
    },

    // Language Configuration
    DEFAULT_LANGUAGE: 'ar',
    SUPPORTED_LANGUAGES: ['ar', 'en']
};