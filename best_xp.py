import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
import arabic_reshaper
from bidi.algorithm import get_display
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import os
from dataclasses import dataclass

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إعدادات البوت
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
DATABASE_PATH = "xp_clan_bot.db"

@dataclass
class User:
    user_id: int
    username: str
    first_name: str
    xp: int
    level: int
    messages_count: int
    clan_id: Optional[int]
    clan_role: str
    language: str

@dataclass
class Clan:
    id: int
    name: str
    description: str
    leader_id: int
    total_xp: int
    member_count: int
    max_members: int
    clan_level: int

class XPClanBot:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_database()
        self.user_cooldowns = {}
        
        # النصوص متعددة اللغات
        self.texts = {
            'ar': {
                'welcome': '🎉 مرحباً بك في بوت XP والكلانات!\n\nاستخدم /help لرؤية الأوامر المتاحة',
                'help': '''🤖 **أوامر البوت:**

**📊 نظام XP:**
/profile - عرض ملفك الشخصي
/leaderboard - لوحة المتصدرين
/level - معلومات المستوى الحالي

**🏰 نظام الكلانات:**
/create_clan <اسم> - إنشاء كلان جديد
/join_clan <اسم> - الانضمام لكلان
/leave_clan - مغادرة الكلان
/clan_info - معلومات الكلان
/clan_members - أعضاء الكلان
/clan_leaderboard - ترتيب الكلانات

**⚔️ حروب الكلانات:**
/challenge_clan <اسم_الكلان> - تحدي كلان آخر
/clan_wars - الحروب النشطة
/war_status - حالة الحرب الحالية

**⚙️ الإعدادات:**
/settings - إعدادات الحساب
/language - تغيير اللغة''',
                'profile_title': '👤 **ملفك الشخصي**',
                'level_up': '🎉 تهانينا! وصلت للمستوى {}!\n🎁 حصلت على {} XP إضافية!',
                'clan_created': '🏰 تم إنشاء الكلان "{}" بنجاح!\nأنت الآن قائد الكلان.',
                'clan_joined': '🎉 انضممت بنجاح للكلان "{}"!',
                'clan_left': '👋 غادرت الكلان بنجاح.',
                'war_started': '⚔️ بدأت الحرب بين {} و {}!\nالمدة: 24 ساعة',
                'war_ended': '🏆 انتهت الحرب!\nالفائز: {}\nالنتيجة: {} - {}',
                'not_in_clan': '❌ أنت لست عضواً في أي كلان.',
                'clan_not_found': '❌ الكلان غير موجود.',
                'already_in_clan': '❌ أنت عضو في كلان بالفعل.',
                'clan_full': '❌ الكلان ممتلئ.',
                'insufficient_permissions': '❌ ليس لديك صلاحيات كافية.',
                'cooldown_message': '⏰ انتظر {} ثانية قبل كسب XP مرة أخرى.'
            },
            'en': {
                'welcome': '🎉 Welcome to XP & Clans Bot!\n\nUse /help to see available commands',
                'help': '''🤖 **Bot Commands:**

**📊 XP System:**
/profile - View your profile
/leaderboard - View leaderboard
/level - Current level info

**🏰 Clan System:**
/create_clan <name> - Create new clan
/join_clan <name> - Join a clan
/leave_clan - Leave clan
/clan_info - Clan information
/clan_members - Clan members
/clan_leaderboard - Clan rankings

**⚔️ Clan Wars:**
/challenge_clan <clan_name> - Challenge another clan
/clan_wars - Active wars
/war_status - Current war status

**⚙️ Settings:**
/settings - Account settings
/language - Change language''',
                'profile_title': '👤 **Your Profile**',
                'level_up': '🎉 Congratulations! You reached level {}!\n🎁 You earned {} bonus XP!',
                'clan_created': '🏰 Clan "{}" created successfully!\nYou are now the clan leader.',
                'clan_joined': '🎉 Successfully joined clan "{}"!',
                'clan_left': '👋 Successfully left the clan.',
                'war_started': '⚔️ War started between {} and {}!\nDuration: 24 hours',
                'war_ended': '🏆 War ended!\nWinner: {}\nScore: {} - {}',
                'not_in_clan': '❌ You are not a member of any clan.',
                'clan_not_found': '❌ Clan not found.',
                'already_in_clan': '❌ You are already in a clan.',
                'clan_full': '❌ Clan is full.',
                'insufficient_permissions': '❌ Insufficient permissions.',
                'cooldown_message': '⏰ Wait {} seconds before earning XP again.'
            }
        }

    def init_database(self):
        """تهيئة قاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                messages_count INTEGER DEFAULT 0,
                last_message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                clan_id INTEGER DEFAULT NULL,
                clan_role TEXT DEFAULT 'member',
                language TEXT DEFAULT 'ar',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (clan_id) REFERENCES clans(id)
            )
        ''')
        
        # جدول الكلانات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                leader_id INTEGER NOT NULL,
                total_xp INTEGER DEFAULT 0,
                member_count INTEGER DEFAULT 1,
                max_members INTEGER DEFAULT 50,
                clan_level INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (leader_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول حروب الكلانات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clan_wars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan1_id INTEGER NOT NULL,
                clan2_id INTEGER NOT NULL,
                clan1_score INTEGER DEFAULT 0,
                clan2_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                start_time TIMESTAMP NULL,
                end_time TIMESTAMP NULL,
                winner_id INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (clan1_id) REFERENCES clans(id),
                FOREIGN KEY (clan2_id) REFERENCES clans(id),
                FOREIGN KEY (winner_id) REFERENCES clans(id)
            )
        ''')
        
        # جدول تحديات الكلانات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clan_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_id INTEGER NOT NULL,
                challenge_type TEXT NOT NULL,
                target_value INTEGER NOT NULL,
                current_value INTEGER DEFAULT 0,
                reward_xp INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (clan_id) REFERENCES clans(id)
            )
        ''')
        
        # جدول سجل XP
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS xp_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                xp_gained INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول الإعدادات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # إدراج الإعدادات الافتراضية
        default_settings = [
            ('xp_per_message', '10'),
            ('xp_cooldown_seconds', '60'),
            ('max_clan_members', '50'),
            ('war_duration_hours', '24'),
            ('challenge_duration_hours', '168')
        ]
        
        for key, value in default_settings:
            cursor.execute('''
                INSERT OR IGNORE INTO bot_settings (setting_key, setting_value)
                VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
        conn.close()

    def get_text(self, user_id: int, key: str) -> str:
        """الحصول على النص بلغة المستخدم"""
        user = self.get_user(user_id)
        lang = user.language if user else 'ar'
        return self.texts.get(lang, self.texts['ar']).get(key, key)

    def get_user(self, user_id: int) -> Optional[User]:
        """الحصول على بيانات المستخدم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, first_name, xp, level, messages_count, 
                   clan_id, clan_role, language
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(*row)
        return None

    def create_or_update_user(self, user_id: int, username: str, first_name: str):
        """إنشاء أو تحديث المستخدم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, xp, level, messages_count, clan_id, clan_role, language)
            VALUES (?, ?, ?, 
                    COALESCE((SELECT xp FROM users WHERE user_id = ?), 0),
                    COALESCE((SELECT level FROM users WHERE user_id = ?), 1),
                    COALESCE((SELECT messages_count FROM users WHERE user_id = ?), 0),
                    (SELECT clan_id FROM users WHERE user_id = ?),
                    COALESCE((SELECT clan_role FROM users WHERE user_id = ?), 'member'),
                    COALESCE((SELECT language FROM users WHERE user_id = ?), 'ar'))
        ''', (user_id, username, first_name, user_id, user_id, user_id, user_id, user_id, user_id))
        
        conn.commit()
        conn.close()

    def add_xp(self, user_id: int, xp_amount: int, reason: str = "message") -> Tuple[bool, int, bool]:
        """إضافة XP للمستخدم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # الحصول على البيانات الحالية
        cursor.execute('SELECT xp, level FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            return False, 0, False
        
        current_xp, current_level = row
        new_xp = current_xp + xp_amount
        new_level = self.calculate_level(new_xp)
        level_up = new_level > current_level
        
        # تحديث XP والمستوى
        cursor.execute('''
            UPDATE users 
            SET xp = ?, level = ?, messages_count = messages_count + 1,
                last_message_time = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (new_xp, new_level, user_id))
        
        # تسجيل XP
        cursor.execute('''
            INSERT INTO xp_logs (user_id, xp_gained, reason)
            VALUES (?, ?, ?)
        ''', (user_id, xp_amount, reason))
        
        # تحديث XP الكلان إذا كان المستخدم في كلان
        cursor.execute('SELECT clan_id FROM users WHERE user_id = ?', (user_id,))
        clan_row = cursor.fetchone()
        
        if clan_row and clan_row[0]:
            cursor.execute('''
                UPDATE clans 
                SET total_xp = total_xp + ?, clan_level = ?
                WHERE id = ?
            ''', (xp_amount, self.calculate_clan_level(clan_row[0]), clan_row[0]))
        
        conn.commit()
        conn.close()
        
        return True, new_level, level_up

    def calculate_level(self, xp: int) -> int:
        """حساب المستوى من XP"""
        return int((xp / 100) ** 0.5) + 1

    def calculate_clan_level(self, clan_id: int) -> int:
        """حساب مستوى الكلان"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT total_xp FROM clans WHERE id = ?', (clan_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return int((row[0] / 1000) ** 0.4) + 1
        return 1

    def xp_for_next_level(self, current_level: int) -> int:
        """XP المطلوب للمستوى التالي"""
        return ((current_level) ** 2) * 100

    def create_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """إنشاء شريط تقدم"""
        filled = int((current / total) * width) if total > 0 else 0
        bar = "█" * filled + "░" * (width - filled)
        percentage = int((current / total) * 100) if total > 0 else 0
        return f"{bar} {percentage}%"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر البداية"""
        user = update.effective_user
        self.create_or_update_user(user.id, user.username or "", user.first_name or "")
        
        welcome_text = self.get_text(user.id, 'welcome')
        
        keyboard = [
            [InlineKeyboardButton("📊 الملف الشخصي", callback_data="profile")],
            [InlineKeyboardButton("🏆 لوحة المتصدرين", callback_data="leaderboard")],
            [InlineKeyboardButton("🏰 الكلانات", callback_data="clans_menu")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر المساعدة"""
        user = update.effective_user
        help_text = self.get_text(user.id, 'help')
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض الملف الشخصي"""
        user_data = self.get_user(update.effective_user.id)
        if not user_data:
            await update.message.reply_text("❌ خطأ في الحصول على البيانات")
            return
        
        # حساب XP للمستوى التالي
        next_level_xp = self.xp_for_next_level(user_data.level)
        current_level_xp = self.xp_for_next_level(user_data.level - 1) if user_data.level > 1 else 0
        progress_xp = user_data.xp - current_level_xp
        needed_xp = next_level_xp - current_level_xp
        
        progress_bar = self.create_progress_bar(progress_xp, needed_xp)
        
        # معلومات الكلان
        clan_info = ""
        if user_data.clan_id:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT name, clan_level FROM clans WHERE id = ?', (user_data.clan_id,))
            clan_row = cursor.fetchone()
            conn.close()
            
            if clan_row:
                clan_info = f"\n🏰 **الكلان:** {clan_row[0]} (مستوى {clan_row[1]})\n👑 **الرتبة:** {user_data.clan_role}"
        
        profile_text = f"""👤 **الملف الشخصي**

👨‍💼 **الاسم:** {user_data.first_name}
🆔 **المعرف:** @{user_data.username or 'غير محدد'}

📊 **إحصائيات XP:**
⭐ **المستوى:** {user_data.level}
🎯 **XP الحالي:** {user_data.xp:,}
📈 **التقدم:** {progress_bar}
🎯 **XP للمستوى التالي:** {next_level_xp - user_data.xp:,}

💬 **الرسائل:** {user_data.messages_count:,}{clan_info}

🌍 **اللغة:** {'العربية' if user_data.language == 'ar' else 'English'}"""
        
        keyboard = [
            [InlineKeyboardButton("🏆 لوحة المتصدرين", callback_data="leaderboard")],
            [InlineKeyboardButton("🏰 معلومات الكلان", callback_data="clan_info")] if user_data.clan_id else [],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup([btn for btn in keyboard if btn])
        
        await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لوحة المتصدرين"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT first_name, username, xp, level, clan_id
            FROM users 
            ORDER BY xp DESC 
            LIMIT 10
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            await update.message.reply_text("📊 لا توجد بيانات حالياً")
            return
        
        leaderboard_text = "🏆 **لوحة المتصدرين - أفضل 10 لاعبين**\n\n"
        
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        
        for i, (name, username, xp, level, clan_id) in enumerate(users):
            clan_name = ""
            if clan_id:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM clans WHERE id = ?', (clan_id,))
                clan_row = cursor.fetchone()
                conn.close()
                if clan_row:
                    clan_name = f" [{clan_row[0]}]"
            
            username_display = f"@{username}" if username else "غير محدد"
            leaderboard_text += f"{medals[i]} **{i+1}.** {name} ({username_display})\n"
            leaderboard_text += f"   📊 {xp:,} XP | ⭐ مستوى {level}{clan_name}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🏰 ترتيب الكلانات", callback_data="clan_leaderboard")],
            [InlineKeyboardButton("📊 ملفي الشخصي", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def create_clan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إنشاء كلان جديد"""
        if not context.args:
            await update.message.reply_text("❌ يرجى كتابة اسم الكلان\nمثال: `/create_clan اسم_الكلان`", parse_mode='Markdown')
            return
        
        clan_name = " ".join(context.args)
        user_id = update.effective_user.id
        
        # التحقق من أن المستخدم ليس في كلان
        user_data = self.get_user(user_id)
        if user_data and user_data.clan_id:
            await update.message.reply_text("❌ أنت عضو في كلان بالفعل. يجب مغادرة الكلان الحالي أولاً.")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # إنشاء الكلان
            cursor.execute('''
                INSERT INTO clans (name, leader_id, description)
                VALUES (?, ?, ?)
            ''', (clan_name, user_id, f"كلان {clan_name} - تم إنشاؤه بواسطة {update.effective_user.first_name}"))
            
            clan_id = cursor.lastrowid
            
            # تحديث المستخدم ليصبح قائد الكلان
            cursor.execute('''
                UPDATE users 
                SET clan_id = ?, clan_role = 'leader'
                WHERE user_id = ?
            ''', (clan_id, user_id))
            
            conn.commit()
            
            success_text = f"🏰 تم إنشاء الكلان **{clan_name}** بنجاح!\n👑 أنت الآن قائد الكلان.\n\n📋 يمكن للآخرين الانضمام باستخدام:\n`/join_clan {clan_name}`"
            
            await update.message.reply_text(success_text, parse_mode='Markdown')
            
        except sqlite3.IntegrityError:
            await update.message.reply_text("❌ اسم الكلان موجود بالفعل. يرجى اختيار اسم آخر.")
        finally:
            conn.close()

    async def join_clan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """الانضمام لكلان"""
        if not context.args:
            await update.message.reply_text("❌ يرجى كتابة اسم الكلان\nمثال: `/join_clan اسم_الكلان`", parse_mode='Markdown')
            return
        
        clan_name = " ".join(context.args)
        user_id = update.effective_user.id
        
        # التحقق من أن المستخدم ليس في كلان
        user_data = self.get_user(user_id)
        if user_data and user_data.clan_id:
            await update.message.reply_text("❌ أنت عضو في كلان بالفعل. يجب مغادرة الكلان الحالي أولاً.")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # البحث عن الكلان
        cursor.execute('SELECT id, member_count, max_members FROM clans WHERE name = ?', (clan_name,))
        clan_row = cursor.fetchone()
        
        if not clan_row:
            await update.message.reply_text("❌ الكلان غير موجود.")
            conn.close()
            return
        
        clan_id, member_count, max_members = clan_row
        
        if member_count >= max_members:
            await update.message.reply_text("❌ الكلان ممتلئ.")
            conn.close()
            return
        
        # انضمام المستخدم للكلان
        cursor.execute('''
            UPDATE users 
            SET clan_id = ?, clan_role = 'member'
            WHERE user_id = ?
        ''', (clan_id, user_id))
        
        # تحديث عدد الأعضاء
        cursor.execute('''
            UPDATE clans 
            SET member_count = member_count + 1
            WHERE id = ?
        ''', (clan_id,))
        
        conn.commit()
        conn.close()
        
        success_text = f"🎉 انضممت بنجاح للكلان **{clan_name}**!\n🏰 مرحباً بك في العائلة الجديدة!"
        await update.message.reply_text(success_text, parse_mode='Markdown')

    async def leave_clan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مغادرة الكلان"""
        user_id = update.effective_user.id
        user_data = self.get_user(user_id)
        
        if not user_data or not user_data.clan_id:
            await update.message.reply_text("❌ أنت لست عضواً في أي كلان.")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # الحصول على معلومات الكلان
        cursor.execute('SELECT name, leader_id, member_count FROM clans WHERE id = ?', (user_data.clan_id,))
        clan_row = cursor.fetchone()
        
        if not clan_row:
            await update.message.reply_text("❌ خطأ في البيانات.")
            conn.close()
            return
        
        clan_name, leader_id, member_count = clan_row
        
        # إذا كان المستخدم قائد الكلان وهناك أعضاء آخرون
        if user_data.clan_role == 'leader' and member_count > 1:
            await update.message.reply_text("❌ لا يمكن للقائد مغادرة الكلان إذا كان هناك أعضاء آخرون.\nيجب نقل القيادة أو حل الكلان أولاً.")
            conn.close()
            return
        
        # مغادرة الكلان
        cursor.execute('''
            UPDATE users 
            SET clan_id = NULL, clan_role = 'member'
            WHERE user_id = ?
        ''', (user_id,))
        
        # تحديث عدد الأعضاء أو حذف الكلان إذا كان فارغاً
        if member_count == 1:
            cursor.execute('DELETE FROM clans WHERE id = ?', (user_data.clan_id,))
        else:
            cursor.execute('''
                UPDATE clans 
                SET member_count = member_count - 1
                WHERE id = ?
            ''', (user_data.clan_id,))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"👋 غادرت الكلان **{clan_name}** بنجاح.", parse_mode='Markdown')

    async def clan_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معلومات الكلان"""
        user_data = self.get_user(update.effective_user.id)
        
        if not user_data or not user_data.clan_id:
            await update.message.reply_text("❌ أنت لست عضواً في أي كلان.")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # معلومات الكلان
        cursor.execute('''
            SELECT c.name, c.description, c.total_xp, c.member_count, c.max_members, 
                   c.clan_level, c.created_at, u.first_name
            FROM clans c
            JOIN users u ON c.leader_id = u.user_id
            WHERE c.id = ?
        ''', (user_data.clan_id,))
        
        clan_row = cursor.fetchone()
        
        if not clan_row:
            await update.message.reply_text("❌ خطأ في الحصول على بيانات الكلان.")
            conn.close()
            return
        
        name, description, total_xp, member_count, max_members, clan_level, created_at, leader_name = clan_row
        
        # أفضل 5 أعضاء
        cursor.execute('''
            SELECT first_name, xp, level
            FROM users 
            WHERE clan_id = ?
            ORDER BY xp DESC
            LIMIT 5
        ''', (user_data.clan_id,))
        
        top_members = cursor.fetchall()
        conn.close()
        
        # تنسيق تاريخ الإنشاء
        created_date = datetime.fromisoformat(created_at).strftime("%Y-%m-%d")
        
        clan_info_text = f"""🏰 **معلومات الكلان**

📛 **الاسم:** {name}
📝 **الوصف:** {description}
👑 **القائد:** {leader_name}
⭐ **مستوى الكلان:** {clan_level}

📊 **الإحصائيات:**
🎯 **إجمالي XP:** {total_xp:,}
👥 **الأعضاء:** {member_count}/{max_members}
📅 **تاريخ الإنشاء:** {created_date}

🏆 **أفضل الأعضاء:**"""
        
        for i, (member_name, member_xp, member_level) in enumerate(top_members, 1):
            clan_info_text += f"\n{i}. {member_name} - {member_xp:,} XP (مستوى {member_level})"
        
        keyboard = [
            [InlineKeyboardButton("👥 جميع الأعضاء", callback_data="clan_members")],
            [InlineKeyboardButton("⚔️ تحدي كلان", callback_data="challenge_menu")],
            [InlineKeyboardButton("📊 إحصائيات مفصلة", callback_data="clan_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(clan_info_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def clan_leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ترتيب الكلانات"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.name, c.total_xp, c.member_count, c.clan_level, u.first_name
            FROM clans c
            JOIN users u ON c.leader_id = u.user_id
            ORDER BY c.total_xp DESC
            LIMIT 10
        ''')
        
        clans = cursor.fetchall()
        conn.close()
        
        if not clans:
            await update.message.reply_text("🏰 لا توجد كلانات حالياً")
            return
        
        leaderboard_text = "🏆 **ترتيب الكلانات - أفضل 10 كلانات**\n\n"
        
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        
        for i, (name, total_xp, member_count, clan_level, leader_name) in enumerate(clans):
            leaderboard_text += f"{medals[i]} **{i+1}.** {name}\n"
            leaderboard_text += f"   👑 القائد: {leader_name}\n"
            leaderboard_text += f"   📊 {total_xp:,} XP | ⭐ مستوى {clan_level} | 👥 {member_count} عضو\n\n"
        
        keyboard = [
            [InlineKeyboardButton("👤 لوحة المتصدرين الشخصية", callback_data="leaderboard")],
            [InlineKeyboardButton("🏰 معلومات كلاني", callback_data="clan_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل العادية لكسب XP"""
        user = update.effective_user
        user_id = user.id
        
        # التحقق من الكولداون
        current_time = datetime.now()
        if user_id in self.user_cooldowns:
            time_diff = (current_time - self.user_cooldowns[user_id]).total_seconds()
            if time_diff < 60:  # 60 ثانية كولداون
                return
        
        # تحديث وقت آخر رسالة
        self.user_cooldowns[user_id] = current_time
        
        # إنشاء أو تحديث المستخدم
        self.create_or_update_user(user_id, user.username or "", user.first_name or "")
        
        # إضافة XP
        success, new_level, level_up = self.add_xp(user_id, 10, "message")
        
        if success and level_up:
            # مكافأة الترقية
            bonus_xp = new_level * 5
            self.add_xp(user_id, bonus_xp, "level_up_bonus")
            
            level_up_text = f"🎉 تهانينا {user.first_name}!\n⭐ وصلت للمستوى {new_level}!\n🎁 حصلت على {bonus_xp} XP إضافية!"
            
            try:
                await update.message.reply_text(level_up_text)
            except:
                pass  # تجاهل الأخطاء في إرسال رسالة الترقية

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أزرار الكيبورد"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data == "profile":
            await self.show_profile_callback(query)
        elif data == "leaderboard":
            await self.show_leaderboard_callback(query)
        elif data == "clan_leaderboard":
            await self.show_clan_leaderboard_callback(query)
        elif data == "clan_info":
            await self.show_clan_info_callback(query)
        elif data == "settings":
            await self.show_settings_callback(query)
        elif data == "clans_menu":
            await self.show_clans_menu_callback(query)

    async def show_profile_callback(self, query):
        """عرض الملف الشخصي عبر الكيبورد"""
        user_data = self.get_user(query.from_user.id)
        if not user_data:
            await query.edit_message_text("❌ خطأ في الحصول على البيانات")
            return
        
        # حساب XP للمستوى التالي
        next_level_xp = self.xp_for_next_level(user_data.level)
        current_level_xp = self.xp_for_next_level(user_data.level - 1) if user_data.level > 1 else 0
        progress_xp = user_data.xp - current_level_xp
        needed_xp = next_level_xp - current_level_xp
        
        progress_bar = self.create_progress_bar(progress_xp, needed_xp)
        
        # معلومات الكلان
        clan_info = ""
        if user_data.clan_id:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT name, clan_level FROM clans WHERE id = ?', (user_data.clan_id,))
            clan_row = cursor.fetchone()
            conn.close()
            
            if clan_row:
                clan_info = f"\n🏰 **الكلان:** {clan_row[0]} (مستوى {clan_row[1]})\n👑 **الرتبة:** {user_data.clan_role}"
        
        profile_text = f"""👤 **الملف الشخصي**

👨‍💼 **الاسم:** {user_data.first_name}
🆔 **المعرف:** @{user_data.username or 'غير محدد'}

📊 **إحصائيات XP:**
⭐ **المستوى:** {user_data.level}
🎯 **XP الحالي:** {user_data.xp:,}
📈 **التقدم:** {progress_bar}
🎯 **XP للمستوى التالي:** {next_level_xp - user_data.xp:,}

💬 **الرسائل:** {user_data.messages_count:,}{clan_info}

🌍 **اللغة:** {'العربية' if user_data.language == 'ar' else 'English'}"""
        
        keyboard = [
            [InlineKeyboardButton("🏆 لوحة المتصدرين", callback_data="leaderboard")],
            [InlineKeyboardButton("🏰 معلومات الكلان", callback_data="clan_info")] if user_data.clan_id else [],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
            [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup([btn for btn in keyboard if btn])
        
        await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_leaderboard_callback(self, query):
        """عرض لوحة المتصدرين عبر الكيبورد"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT first_name, username, xp, level, clan_id
            FROM users 
            ORDER BY xp DESC 
            LIMIT 10
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            await query.edit_message_text("📊 لا توجد بيانات حالياً")
            return
        
        leaderboard_text = "🏆 **لوحة المتصدرين - أفضل 10 لاعبين**\n\n"
        
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        
        for i, (name, username, xp, level, clan_id) in enumerate(users):
            clan_name = ""
            if clan_id:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM clans WHERE id = ?', (clan_id,))
                clan_row = cursor.fetchone()
                conn.close()
                if clan_row:
                    clan_name = f" [{clan_row[0]}]"
            
            username_display = f"@{username}" if username else "غير محدد"
            leaderboard_text += f"{medals[i]} **{i+1}.** {name} ({username_display})\n"
            leaderboard_text += f"   📊 {xp:,} XP | ⭐ مستوى {level}{clan_name}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🏰 ترتيب الكلانات", callback_data="clan_leaderboard")],
            [InlineKeyboardButton("📊 ملفي الشخصي", callback_data="profile")],
            [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_clan_leaderboard_callback(self, query):
        """عرض ترتيب الكلانات عبر الكيبورد"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.name, c.total_xp, c.member_count, c.clan_level, u.first_name
            FROM clans c
            JOIN users u ON c.leader_id = u.user_id
            ORDER BY c.total_xp DESC
            LIMIT 10
        ''')
        
        clans = cursor.fetchall()
        conn.close()
        
        if not clans:
            await query.edit_message_text("🏰 لا توجد كلانات حالياً")
            return
        
        leaderboard_text = "🏆 **ترتيب الكلانات - أفضل 10 كلانات**\n\n"
        
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        
        for i, (name, total_xp, member_count, clan_level, leader_name) in enumerate(clans):
            leaderboard_text += f"{medals[i]} **{i+1}.** {name}\n"
            leaderboard_text += f"   👑 القائد: {leader_name}\n"
            leaderboard_text += f"   📊 {total_xp:,} XP | ⭐ مستوى {clan_level} | 👥 {member_count} عضو\n\n"
        
        keyboard = [
            [InlineKeyboardButton("👤 لوحة المتصدرين الشخصية", callback_data="leaderboard")],
            [InlineKeyboardButton("🏰 الكلانات", callback_data="clans_menu")],
            [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_clan_info_callback(self, query):
        """عرض معلومات الكلان عبر الكيبورد"""
        user_data = self.get_user(query.from_user.id)
        
        if not user_data or not user_data.clan_id:
            await query.edit_message_text("❌ أنت لست عضواً في أي كلان.")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # معلومات الكلان
        cursor.execute('''
            SELECT c.name, c.description, c.total_xp, c.member_count, c.max_members, 
                   c.clan_level, c.created_at, u.first_name
            FROM clans c
            JOIN users u ON c.leader_id = u.user_id
            WHERE c.id = ?
        ''', (user_data.clan_id,))
        
        clan_row = cursor.fetchone()
        
        if not clan_row:
            await query.edit_message_text("❌ خطأ في الحصول على بيانات الكلان.")
            conn.close()
            return
        
        name, description, total_xp, member_count, max_members, clan_level, created_at, leader_name = clan_row
        
        # أفضل 5 أعضاء
        cursor.execute('''
            SELECT first_name, xp, level
            FROM users 
            WHERE clan_id = ?
            ORDER BY xp DESC
            LIMIT 5
        ''', (user_data.clan_id,))
        
        top_members = cursor.fetchall()
        conn.close()
        
        # تنسيق تاريخ الإنشاء
        created_date = datetime.fromisoformat(created_at).strftime("%Y-%m-%d")
        
        clan_info_text = f"""🏰 **معلومات الكلان**

📛 **الاسم:** {name}
📝 **الوصف:** {description}
👑 **القائد:** {leader_name}
⭐ **مستوى الكلان:** {clan_level}

📊 **الإحصائيات:**
🎯 **إجمالي XP:** {total_xp:,}
👥 **الأعضاء:** {member_count}/{max_members}
📅 **تاريخ الإنشاء:** {created_date}

🏆 **أفضل الأعضاء:**"""
        
        for i, (member_name, member_xp, member_level) in enumerate(top_members, 1):
            clan_info_text += f"\n{i}. {member_name} - {member_xp:,} XP (مستوى {member_level})"
        
        keyboard = [
            [InlineKeyboardButton("👥 جميع الأعضاء", callback_data="clan_members")],
            [InlineKeyboardButton("⚔️ تحدي كلان", callback_data="challenge_menu")],
            [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(clan_info_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_settings_callback(self, query):
        """عرض الإعدادات عبر الكيبورد"""
        user_data = self.get_user(query.from_user.id)
        
        settings_text = f"""⚙️ **الإعدادات**

🌍 **اللغة الحالية:** {'العربية' if user_data.language == 'ar' else 'English'}

📊 **إحصائيات سريعة:**
⭐ المستوى: {user_data.level}
🎯 XP: {user_data.xp:,}
💬 الرسائل: {user_data.messages_count:,}"""
        
        keyboard = [
            [InlineKeyboardButton("🌍 تغيير اللغة", callback_data="change_language")],
            [InlineKeyboardButton("📊 الملف الشخصي", callback_data="profile")],
            [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_clans_menu_callback(self, query):
        """عرض قائمة الكلانات عبر الكيبورد"""
        user_data = self.get_user(query.from_user.id)
        
        if user_data and user_data.clan_id:
            # المستخدم في كلان
            menu_text = "🏰 **قائمة الكلانات**\n\nأنت عضو في كلان حالياً"
            keyboard = [
                [InlineKeyboardButton("🏰 معلومات كلاني", callback_data="clan_info")],
                [InlineKeyboardButton("👥 أعضاء الكلان", callback_data="clan_members")],
                [InlineKeyboardButton("🏆 ترتيب الكلانات", callback_data="clan_leaderboard")],
                [InlineKeyboardButton("🚪 مغادرة الكلان", callback_data="leave_clan_confirm")],
                [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
            ]
        else:
            # المستخدم ليس في كلان
            menu_text = """🏰 **قائمة الكلانات**

أنت لست عضواً في أي كلان حالياً

📋 **للانضمام أو إنشاء كلان:**
• `/create_clan اسم_الكلان` - إنشاء كلان جديد
• `/join_clan اسم_الكلان` - الانضمام لكلان موجود"""
            
            keyboard = [
                [InlineKeyboardButton("🏆 ترتيب الكلانات", callback_data="clan_leaderboard")],
                [InlineKeyboardButton("📋 قائمة الكلانات", callback_data="clans_list")],
                [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

    def run(self):
        """تشغيل البوت"""
        application = Application.builder().token(BOT_TOKEN).build()
        
        # إضافة المعالجات
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("profile", self.profile_command))
        application.add_handler(CommandHandler("leaderboard", self.leaderboard_command))
        application.add_handler(CommandHandler("create_clan", self.create_clan_command))
        application.add_handler(CommandHandler("join_clan", self.join_clan_command))
        application.add_handler(CommandHandler("leave_clan", self.leave_clan_command))
        application.add_handler(CommandHandler("clan_info", self.clan_info_command))
        application.add_handler(CommandHandler("clan_leaderboard", self.clan_leaderboard_command))
        
        # معالج الأزرار
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # معالج الرسائل العادية
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        print("🤖 تم تشغيل البوت بنجاح!")
        print("📊 نظام XP والكلانات جاهز للاستخدام")
        
        # تشغيل البوت
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # تأكد من وضع التوكن الخاص بك هنا
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ يرجى وضع توكن البوت في المتغير BOT_TOKEN")
        exit(1)
    
    bot = XPClanBot()
    bot.run()