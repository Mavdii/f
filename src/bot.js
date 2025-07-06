import TelegramBot from 'node-telegram-bot-api';
import { DatabaseManager } from './database/manager.js';
import { XPSystem } from './systems/xp.js';
import { ClanSystem } from './systems/clan.js';
import { CommandHandler } from './handlers/commands.js';
import { MessageHandler } from './handlers/messages.js';
import { CallbackHandler } from './handlers/callbacks.js';
import { ScheduleManager } from './utils/scheduler.js';
import { Logger } from './utils/logger.js';
import { config } from './config/config.js';

class XPClanBot {
    constructor() {
        this.bot = new TelegramBot(config.BOT_TOKEN, { polling: true });
        this.db = new DatabaseManager();
        this.xpSystem = new XPSystem(this.db);
        this.clanSystem = new ClanSystem(this.db);
        this.commandHandler = new CommandHandler(this.bot, this.db, this.xpSystem, this.clanSystem);
        this.messageHandler = new MessageHandler(this.bot, this.db, this.xpSystem);
        this.callbackHandler = new CallbackHandler(this.bot, this.db, this.xpSystem, this.clanSystem);
        this.scheduler = new ScheduleManager(this.db, this.xpSystem, this.clanSystem);
        this.logger = new Logger();
    }

    async initialize() {
        try {
            await this.db.initialize();
            this.setupEventHandlers();
            this.scheduler.start();
            
            console.log('🚀 XP Clan Bot started successfully!');
            this.logger.info('Bot initialized and ready');
        } catch (error) {
            console.error('❌ Failed to initialize bot:', error);
            process.exit(1);
        }
    }

    setupEventHandlers() {
        // Command handling
        this.bot.onText(/^\/(.+)/, (msg, match) => {
            this.commandHandler.handle(msg, match[1]);
        });

        // Message handling for XP
        this.bot.on('message', (msg) => {
            if (!msg.text?.startsWith('/')) {
                this.messageHandler.handle(msg);
            }
        });

        // Callback query handling
        this.bot.on('callback_query', (query) => {
            this.callbackHandler.handle(query);
        });

        // Error handling
        this.bot.on('error', (error) => {
            this.logger.error('Bot error:', error);
        });

        // Polling error handling
        this.bot.on('polling_error', (error) => {
            this.logger.error('Polling error:', error);
        });
    }
}

// Start the bot
const bot = new XPClanBot();
bot.initialize();