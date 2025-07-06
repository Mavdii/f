
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client
from datetime import datetime, timedelta, date
# استيراد مدير الكلانات

import asyncio

API_ID = 22696039
API_HASH = "00f9cc1d3419e879013f7a9d2d9432e2"
BOT_TOKEN = "7788824693:AAG3mJf-NOGcCNCLCD-KFV8q5T21BvmcJ2U"
SUPABASE_URL = "https://ccnvqlulsblbzrkdbipj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNjbnZxbHVsc2JsYnpya2RiaXBqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE0MTQxMDMsImV4cCI6MjA2Njk5MDEwM30.zBUJOLQ2bNH0t8L5HcSGo6nbYcVxYeCoLgPqDi6kkb0"

SUPER_ADMIN_IDS = [7089656746]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
clan_manager = ClanManager(supabase)
# خيارات شراء الأدمن
ADMIN_PRICES = {
    "1": {"days": 1, "coins": 1500},
    "2": {"days": 2, "coins": 3000},
    "3": {"days": 3, "coins": 4500}
}

# خيارات الاستبدال (Normal Exchange)
EXCHANGE_OPTIONS = [
    {"xp": 200, "coins": 100},
    {"xp": 500, "coins": 300},
    {"xp": 750, "coins": 560},
    {"xp": 1000, "coins": 700}
]

# إعدادات المكافآت اليومية
DAILY_REWARD_XP = 400
DAILY_REWARD_COINS = 200

# إعدادات أمر الشكر
THANK_YOU_REWARD_XP = 200
THANK_YOU_REWARD_COINS = 150
THANK_YOU_COOLDOWN_HOURS = 1

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def xp_msg(name, level, level_name, xp, next_xp, coins, user_id, username, stats):
    return (
        f"**Your Full Information** 🏷\n"
        f"👤 **Name**: <a href=\"tg://user?id={user_id}\">{username}</a>\n"
        f"🏅 **Level**: **{level}** - **{level_name}**\n"
        f"🧙‍♂️ **XP**: **{xp}**/**{next_xp}**\n"
        f"💰 **Coins**: **{coins}**\n"
    )

async def get_or_create_user(user_id, group_id, username):
    """الحصول على المستخدم أو إنشاؤه في قاعدة البيانات"""
    try:
        # محاولة جلب المستخدم من قاعدة البيانات
        res = supabase.table("group_members").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        user = res.data[0] if res.data else None

        if user:
            # تحديث آخر نشاط واسم المستخدم
            supabase.table("group_members").update({
                "last_activity": datetime.now().isoformat(),
                "username": username,
                "updated_at": datetime.now().isoformat()
            }).eq("user_id", user_id).eq("group_id", group_id).execute()
            return user
        else:
            # المستخدم غير موجود، أضفه
            new_user = {
                "user_id": user_id,
                "group_id": group_id,
                "username": username,
                "xp": 0,
                "coins": 0,
                "level": 1,
                "messages_count": 0,
                "total_messages": 0,
                "is_admin": False,
                "is_banned": False,
                "warning_count": 0,
                "join_date": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            result = supabase.table("group_members").insert(new_user).execute()
            return result.data[0] if result.data else new_user
    except Exception as e:
        print(f"خطأ في get_or_create_user: {e}")
        return None

async def get_user_stats(user_id, group_id):
    """الحصول على إحصائيات المستخدم"""
    try:
        res = supabase.table("group_members").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        user = res.data[0] if res.data else None

        if user:
            lvl = user.get("level", 1)

            # البحث عن المستوى الحالي
            current_level_res = supabase.table("levels").select("*").eq("level", lvl).execute()
            level_name = current_level_res.data[0]["name"] if current_level_res.data else "بدون اسم"

            # البحث عن المستوى التالي
            next_lvl = lvl + 1
            next_level_res = supabase.table("levels").select("*").eq("level", next_lvl).execute()
            next_xp = next_level_res.data[0]["required_xp"] if next_level_res.data else (user.get("xp", 0) + 100)

            return {
                "name": user.get("username", "بدون اسم"),
                "level": lvl,
                "level_name": level_name,
                "xp": user.get("xp", 0),
                "next_xp": next_xp,
                "coins": user.get("coins", 0)
            }
        else:
            return {
                "name": "بدون اسم",
                "level": 1,
                "level_name": "بدون اسم",
                "xp": 0,
                "next_xp": 100,
                "coins": 0
            }
    except Exception as e:
        print(f"خطأ في get_user_stats: {e}")
        return {
            "name": "بدون اسم",
            "level": 1,
            "level_name": "بدون اسم",
            "xp": 0,
            "next_xp": 100,
            "coins": 0
        }

async def update_user_xp(user_id, group_id, username, plus_xp=30, plus_coins=10):
    """تحديث XP وكوينز المستخدم + توزيع XP للكلان"""
    try:
        user = await get_or_create_user(user_id, group_id, username)
        if not user:
            return None, []

        new_xp = user.get("xp", 0) + plus_xp
        new_coins = user.get("coins", 0) + plus_coins
        lvl = user.get("level", 1)
        new_total_messages = user.get("total_messages", 0) + 1
        new_messages_count = user.get("messages_count", 0) + 1

        # فحص المستوى التالي
        congrats = None  # تهيئة المتغير
        while True:
            levels_res = supabase.table("levels").select("*").eq("level", lvl + 1).execute()
            next_level_obj = levels_res.data[0] if levels_res.data else None

            if next_level_obj and new_xp >= next_level_obj["required_xp"]:
                lvl += 1
                level_congrats = next_level_obj.get("congratulation", next_level_obj.get("congrats_message", "تهانينا!"))
                congrats = (
                    f" **Amazing** <a href=\"tg://user?id={user_id}\">{username}</a> !\n"
                    f"{level_congrats}"
                )
            else:
                break

        # تحديث البيانات
        supabase.table("group_members").update({
            "xp": new_xp,
            "coins": new_coins,
            "level": lvl,
            "username": username,
            "total_messages": new_total_messages,
            "messages_count": new_messages_count,
            "last_activity": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }).eq("user_id", user_id).eq("group_id", group_id).execute()

        # توزيع XP للكلان (10%)
        await clan_manager.add_member_xp(user_id, plus_xp)

        # تسجيل المعاملة
        await log_transaction(user_id, group_id, "xp_gain", plus_xp, f"رسالة عادية: +{plus_xp} XP")
        await log_transaction(user_id, group_id, "coins_gain", plus_coins, f"رسالة عادية: +{plus_coins} كوينز")

        # تحديث تقدم المهام
        await update_task_progress(user_id, group_id, "send_messages", 1)

        # فحص وإعطاء الشارات الجديدة
        new_badges = await check_and_award_badges(user_id, group_id)

        return congrats, new_badges
    except Exception as e:
        print(f"خطأ في update_user_xp: {e}")
        return None, []
# ==============================
# 🏆 أوامر الكلانات المختصرة
# ==============================

# إنشاء كلان: /cc اسم تاج
@app.on_message(filters.command("cc") & filters.group)
async def clan_create_cmd(client, message):
    user_id = message.from_user.id
    group_id = message.chat.id
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply_text("❗ استخدم: /cc اسم_الكلان تاج_الكلان")
        return
    name, tag = args[1], args[2]
    ok, msg = await clan_manager.create_clan(user_id, group_id, name, tag)
    await message.reply_text(msg)

# انضمام لكلان: /cj ID
@app.on_message(filters.command("cj") & filters.group)
async def clan_join_cmd(client, message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text("❗ استخدم: /cj ID_الكلان")
        return
    try:
        clan_id = int(args[1])
    except:
        await message.reply_text("❗ رقم الكلان غير صحيح.")
        return
    ok, msg = await clan_manager.join_clan(user_id, clan_id)
    await message.reply_text(msg)

# مغادرة كلان: /cl
@app.on_message(filters.command("cl") & filters.group)
async def clan_leave_cmd(client, message):
    user_id = message.from_user.id
    ok, msg = await clan_manager.leave_clan(user_id)
    await message.reply_text(msg)

# معلومات الكلان: /ci
@app.on_message(filters.command("ci") & filters.group)
async def clan_info_cmd(client, message):
    user_id = message.from_user.id
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان.")
        return
    text = f"🏷️ <b>{clan['name']}</b> [{clan['tag']}], ID: <code>{clan['id']}</code>\n"
    text += f"👑 الزعيم: <a href=\"tg://user?id={clan['leader_id']}\">{clan['leader_id']}</a>\n"
    text += f"🏆 المستوى: {clan['level']} | XP: {clan['xp']}\n"
    text += f"💰 كوينز: {clan['coins']}\n"
    text += f"📝 الوصف: {clan['description']}\n"
    await message.reply_text(text)

# أعضاء الكلان: /cm
@app.on_message(filters.command("cm") & filters.group)
async def clan_members_cmd(client, message):
    user_id = message.from_user.id
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان.")
        return
    members = await clan_manager.get_clan_members(clan["id"])
    text = f"👥 أعضاء كلان {clan['name']} (ID: {clan['id']}):\n"
    for m in members:
        role = "👑" if m["role"] == "leader" else "🧑‍🤝‍🧑"
        text += f"{role} <a href=\"tg://user?id={m['user_id']}\">{m['user_id']}</a>\n"
    await message.reply_text(text)

# تصنيف الكلانات: /ctop
@app.on_message(filters.command("ctop") & filters.group)
async def clan_top_cmd(client, message):
    top = await clan_manager.get_top_clans()
    text = "🏆 أفضل الكلانات:\n"
    for i, c in enumerate(top, 1):
        text += f"{i}. {c['name']} [{c['tag']}] (ID: {c['id']}) - مستوى {c['level']} - {c['xp']} XP\n"
    await message.reply_text(text)

async def buy_admin(user_id, group_id, username, days, price):
    """شراء رتبة أدمن مؤقت"""
    try:
        # إعادة جلب أحدث رصيد للكوينز من قاعدة البيانات مباشرة
        res = supabase.table("group_members").select("coins, username").eq("user_id", user_id).eq("group_id", group_id).execute()
        if not res.data:
            return False, "حدث خطأ في النظام! المستخدم غير موجود في قاعدة البيانات.", ""

        current_coins = res.data[0].get("coins", 0)
        current_username = res.data[0].get("username", username)

        print(f"فحص الكوينز للمستخدم {user_id}: لديه {current_coins} كوينز، يحتاج {price} كوينز")

        if current_coins < price:
            return False, f"عذرًا! ليس لديك كوينز كافية لشراء هذه الرتبة. لديك {current_coins} كوينز وتحتاج {price} كوينز.", ""

        # حساب تواريخ الصلاحية
        purchase_date = datetime.now()
        expiry_date = purchase_date + timedelta(days=days)

        # تحديث رصيد الكوينز وحالة الأدمن
        new_coins = current_coins - price
        supabase.table("group_members").update({
            "coins": new_coins,
            "admin_expiry": expiry_date.isoformat(),
            "is_admin": True,
            "updated_at": datetime.now().isoformat()
        }).eq("user_id", user_id).eq("group_id", group_id).execute()

        # تسجيل عملية الشراء
        purchase_data = {
            "user_id": user_id,
            "group_id": group_id,
            "item_type": "admin",
            "duration_days": days,
            "start_at": purchase_date.isoformat(),
            "end_at": expiry_date.isoformat(),
            "is_active": True
        }
        print(f"تسجيل عملية الشراء: {purchase_data}")
        response = supabase.table("purchases").insert(purchase_data).execute()
        if hasattr(response, 'error') and response.error:
            print(f"خطأ في Supabase: {response.error}")
        else:
            print("تم تسجيل عملية الشراء بنجاح")

        # رسالة النجاح
        success_msg = (
            f"✅ ***Payment has been completed successfully.** 💯 \n\n"
            f"👤 **The buyer:** <a href=\"tg://user?id={user_id}\">{username}</a>\n"
            f"💰 **Amount paid:** **{price}** **Coins**\n"
            f"⏳ **Duration:** **{days}** Days\n"
            f"📅 **Expiry Date:** **{expiry_date.strftime('%Y-%m-%d %H:%M:%S')}**\n\n"
            f"💬 **Note:** **You must contact with @Mavdiii to give you the admin rank**\n\n"
            f"💰 **Remaining Balance:** **{new_coins}** **Coins**"
        )

        # تسجيل المعاملة
        await log_transaction(user_id, group_id, "purchase", price, f"شراء أدمن لمدة {days} أيام")

        return True, success_msg, ""
    except Exception as e:
        print(f"خطأ في buy_admin: {e}")
        return False, "حدث خطأ في النظام!", ""

async def exchange_xp_to_coins(user_id, group_id, xp_amount, coins_amount):
    """استبدال XP بكوينز"""
    try:
        res = supabase.table("group_members").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        user = res.data[0] if res.data else None

        if not user:
            return False, "لم يتم العثور على بياناتك!"

        current_xp = user.get("xp", 0)
        current_coins = user.get("coins", 0)
        username = user.get("username", "مستخدم")

        if current_xp < xp_amount:
            return False, f"للأسف، تحتاج إلى {xp_amount} XP ولديك فقط {current_xp} XP"

        # تنفيذ الاستبدال
        new_xp = current_xp - xp_amount
        new_coins = current_coins + coins_amount

        # تحديث قاعدة البيانات
        supabase.table("group_members").update({
            "xp": new_xp,
            "coins": new_coins,
            "updated_at": datetime.now().isoformat()
        }).eq("user_id", user_id).eq("group_id", group_id).execute()

        # تسجيل الاستبدال في جدول xp_exchange
        supabase.table("xp_exchange").insert({
            "user_id": user_id,
            "group_id": group_id,
            "xp_exchanged": xp_amount,
            "coins_received": coins_amount,
            "exchanged_at": datetime.now().isoformat()
        }).execute()

        # تسجيل المعاملة
        await log_transaction(user_id, group_id, "exchange", coins_amount, f"استبدال {xp_amount} XP بـ {coins_amount} كوينز")

        return True, f"✅ **Exchange Completed Successfully by: <a href=\"tg://user?id={user_id}\">{username}</a>!**\n\n📉 **XP Deducted:** **{xp_amount}**\n📈 **Coins Credited:** **{coins_amount}**\n\n🧙‍♂️ **Your Current XP:** **{new_xp}**\n💰 **Your Current Coin Balance:** **{new_coins}**"
    except Exception as e:
        print(f"خطأ في exchange_xp_to_coins: {e}")
        return False, "حدث خطأ في النظام!"

async def update_user_coins(user_id, group_id, amount):
    """إضافة كوينز للمستخدم (للإدارة)"""
    try:
        res = supabase.table("group_members").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        user = res.data[0] if res.data else None

        if user:
            new_coins = user.get("coins", 0) + amount
            supabase.table("group_members").update({
                "coins": new_coins,
                "updated_at": datetime.now().isoformat()
            }).eq("user_id", user_id).eq("group_id", group_id).execute()

            # تسجيل المعاملة
            await log_transaction(user_id, group_id, "admin_add", amount, f"إضافة كوينز من الإدارة: +{amount}")
            return True
        return False
    except Exception as e:
        print(f"خطأ في update_user_coins: {e}")
        return False

async def add_user_xp(user_id, group_id, amount):
    """إضافة XP للمستخدم (للإدارة)"""
    try:
        res = supabase.table("group_members").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        user = res.data[0] if res.data else None

        if user:
            new_xp = user.get("xp", 0) + amount
            supabase.table("group_members").update({
                "xp": new_xp,
                "updated_at": datetime.now().isoformat()
            }).eq("user_id", user_id).eq("group_id", group_id).execute()

            # تسجيل المعاملة
            await log_transaction(user_id, group_id, "admin_add", amount, f"إضافة XP من الإدارة: +{amount}")
            return True
        return False
    except Exception as e:
        print(f"خطأ في add_user_xp: {e}")
        return False

# دالة للتحقق من المكافآت اليومية وتسجيلها
async def check_and_claim_daily_reward(user_id, group_id, username):
    """فحص وطلب المكافأة اليومية"""
    try:
        now = datetime.utcnow()

        # التحقق من آخر مرة طلب فيها المستخدم المكافأة
        res = supabase.table("daily_rewards").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        daily_record = res.data[0] if res.data else None

        if daily_record:
            last_claimed = datetime.fromisoformat(daily_record["last_claimed"].replace("Z", "+00:00"))
            time_diff = now - last_claimed

            # التحقق إذا مر 24 ساعة منذ آخر مطالبة
            if time_diff < timedelta(hours=24):
                remaining_time = timedelta(hours=24) - time_diff
                hours = int(remaining_time.seconds // 3600)
                minutes = int((remaining_time.seconds % 3600) // 60)
                return False, f"⏰ يجب انتظار {hours} ساعة و {minutes} دقيقة قبل طلب المكافأة التالية!"

            # تحديث streak count
            if time_diff <= timedelta(hours=48):  # إذا كان أقل من 48 ساعة (يوم متتالي)
                new_streak = daily_record["streak_count"] + 1
            else:  # إذا انقطع التسلسل
                new_streak = 1

            new_total_claims = daily_record["total_claims"] + 1

            # تحديث السجل
            supabase.table("daily_rewards").update({
                "last_claimed": now.isoformat(),
                "streak_count": new_streak,
                "total_claims": new_total_claims
            }).eq("user_id", user_id).eq("group_id", group_id).execute()
        else:
            # إنشاء سجل جديد للمستخدم
            new_streak = 1
            new_total_claims = 1
            supabase.table("daily_rewards").insert({
                "user_id": user_id,
                "group_id": group_id,
                "last_claimed": now.isoformat(),
                "streak_count": new_streak,
                "total_claims": new_total_claims
            }).execute()

        # إعطاء المكافأة للمستخدم
        await update_user_xp(user_id, group_id, username, DAILY_REWARD_XP, DAILY_REWARD_COINS)

        # تحديث تقدم المهام
        await update_task_progress(user_id, group_id, "daily_login", 1)

        # تسجيل المعاملة
        await log_transaction(user_id, group_id, "daily_reward", DAILY_REWARD_XP, f"مكافأة يومية: streak {new_streak}")

        return True, f"🎁 <a href=\"tg://user?id={user_id}\">{username}</a> **has successfully claimed the daily gift.**\n\n💰 **+{DAILY_REWARD_COINS} Coins**\n🧙‍♂️ **+{DAILY_REWARD_XP} XP**\n🔥 **Streak**: **{new_streak}** **day**"
    except Exception as e:
        print(f"خطأ في check_and_claim_daily_reward: {e}")
        return False, "حدث خطأ في النظام!"

# دالة للتحقق من cooldown أمر الشكر
async def check_thank_you_cooldown(user_id, group_id):
    """فحص cooldown أمر الشكر"""
    try:
        now = datetime.utcnow()

        # التحقق من آخر مرة استخدم فيها المستخدم أمر الشكر
        res = supabase.table("thank_you_cooldown").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        cooldown_record = res.data[0] if res.data else None

        if cooldown_record:
            last_used = datetime.fromisoformat(cooldown_record["last_used"].replace("Z", "+00:00"))
            time_diff = now - last_used

            # التحقق إذا مر 4 ساعات منذ آخر استخدام
            if time_diff < timedelta(hours=THANK_YOU_COOLDOWN_HOURS):
                remaining_time = timedelta(hours=THANK_YOU_COOLDOWN_HOURS) - time_diff
                hours = int(remaining_time.seconds // 3600)
                minutes = int((remaining_time.seconds % 3600) // 60)
                return False, f"⏰ يجب انتظار {hours} ساعة و {minutes} دقيقة قبل شكر شخص آخر!"

        return True, ""
    except Exception as e:
        print(f"خطأ في check_thank_you_cooldown: {e}")
        return False, "حدث خطأ في النظام!"

# دالة لتسجيل استخدام أمر الشكر
async def record_thank_you_usage(user_id, group_id):
    """تسجيل استخدام أمر الشكر"""
    try:
        now = datetime.utcnow()

        # التحقق من وجود سجل سابق
        res = supabase.table("thank_you_cooldown").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        cooldown_record = res.data[0] if res.data else None

        if cooldown_record:
            # تحديث السجل الموجود
            new_total_given = cooldown_record["total_thanks_given"] + 1
            supabase.table("thank_you_cooldown").update({
                "last_used": now.isoformat(),
                "total_thanks_given": new_total_given
            }).eq("user_id", user_id).eq("group_id", group_id).execute()
        else:
            # إنشاء سجل جديد
            supabase.table("thank_you_cooldown").insert({
                "user_id": user_id,
                "group_id": group_id,
                "last_used": now.isoformat(),
                "total_thanks_given": 1,
                "total_thanks_received": 0
            }).execute()
    except Exception as e:
        print(f"خطأ في record_thank_you_usage: {e}")

# دالة لإعطاء مكافأة الشكر
async def give_thank_you_reward(thanked_user_id, group_id, thanked_username):
    """إعطاء مكافأة الشكر للمستخدم المشكور"""
    try:
        # التأكد من وجود المستخدم المشكور في قاعدة البيانات
        await get_or_create_user(thanked_user_id, group_id, thanked_username)

        # إعطاء المكافأة
        await update_user_xp(thanked_user_id, group_id, thanked_username, THANK_YOU_REWARD_XP, THANK_YOU_REWARD_COINS)

        # تحديث عداد الشكر المستلم
        res = supabase.table("thank_you_cooldown").select("*").eq("user_id", thanked_user_id).eq("group_id", group_id).execute()
        if res.data:
            new_total_received = res.data[0]["total_thanks_received"] + 1
            supabase.table("thank_you_cooldown").update({
                "total_thanks_received": new_total_received
            }).eq("user_id", thanked_user_id).eq("group_id", group_id).execute()
        else:
            supabase.table("thank_you_cooldown").insert({
                "user_id": thanked_user_id,
                "group_id": group_id,
                "last_used": datetime.utcnow().isoformat(),
                "total_thanks_given": 0,
                "total_thanks_received": 1
            }).execute()

        # تسجيل المعاملة
        await log_transaction(thanked_user_id, group_id, "thank_reward", THANK_YOU_REWARD_XP, f"مكافأة شكر من مستخدم آخر")

        return f"💖 **Successfully thanked** <a href=\"tg://user?id={thanked_user_id}\">{thanked_username}</a>!\n\n🎁 **Reward Granted:**\n💰 **+{THANK_YOU_REWARD_COINS} Coins**\n🧙‍♂️ **+{THANK_YOU_REWARD_XP} XP**"
    except Exception as e:
        print(f"خطأ في give_thank_you_reward: {e}")
        return "حدث خطأ في إرسال المكافأة!"

# دالة للتحقق من صلاحيات الإدارة
async def check_admin_permissions(user_id, chat_id, client):
    """فحص صلاحيات الإدارة"""
    try:
        # التحقق من المطور العام
        if user_id in SUPER_ADMIN_IDS:
            return True

        # التحقق من مالك المجموعة في جدول group_admins
        group_admin_res = supabase.table("group_admins").select("*").eq("group_id", chat_id).eq("admin_id", user_id).execute()
        if group_admin_res.data:
            return True

        # التحقق من أن المستخدم مالك المجموعة عبر Telegram API
        try:
            chat_member = await client.get_chat_member(chat_id, user_id)
            return chat_member.status == "creator"
        except Exception:
            pass

        return False
    except Exception as e:
        print(f"خطأ في check_admin_permissions: {e}")
        return False

# ==================================
# 🎯 نظام المهام اليومية
# ==================================

async def get_user_daily_tasks(user_id, group_id):
    """الحصول على المهام اليومية للمستخدم"""
    try:
        today = date.today().isoformat()  # تحويل التاريخ إلى string

        # الحصول على جميع المهام النشطة
        active_tasks = supabase.table("daily_tasks").select("*").eq("is_active", True).execute()

        # الحصول على تقدم المستخدم في المهام
        user_progress = supabase.table("user_daily_tasks").select("*").eq("user_id", user_id).eq("group_id", group_id).eq("completed_date", today).execute()

        tasks_info = []
        for task in active_tasks.data:
            user_task = next((ut for ut in user_progress.data if ut["task_id"] == task["id"]), None)

            if user_task:
                progress = user_task["progress"]
                is_completed = user_task["is_completed"]
            else:
                progress = 0
                is_completed = False

            tasks_info.append({
                "id": task["id"],
                "name": task["task_name"],
                "description": task["description"],
                "xp_reward": task["xp_reward"],
                "coins_reward": task["coins_reward"],
                "required_count": task["required_count"],
                "progress": progress,
                "is_completed": is_completed
            })

        return tasks_info
    except Exception as e:
        print(f"خطأ في get_user_daily_tasks: {e}")
        return []

async def update_task_progress(user_id, group_id, task_name, increment=1):
    """تحديث تقدم المهمة للمستخدم"""
    try:
        today = date.today().isoformat()  # تحويل التاريخ إلى string

        # الحصول على المهمة
        task_result = supabase.table("daily_tasks").select("*").eq("task_name", task_name).eq("is_active", True).execute()
        if not task_result.data:
            return False

        task = task_result.data[0]

        # البحث عن تقدم المستخدم
        user_task_result = supabase.table("user_daily_tasks").select("*").eq("user_id", user_id).eq("group_id", group_id).eq("task_id", task["id"]).eq("completed_date", today).execute()

        if user_task_result.data:
            # تحديث التقدم الموجود
            user_task = user_task_result.data[0]
            if user_task["is_completed"]:  # إذا كانت المهمة مكتملة بالفعل
                return False

            new_progress = min(user_task["progress"] + increment, task["required_count"])
            is_completed = new_progress >= task["required_count"]

            supabase.table("user_daily_tasks").update({
                "progress": new_progress,
                "is_completed": is_completed,
                "completed_date": today
            }).eq("id", user_task["id"]).execute()
        else:
            # إنشاء سجل جديد
            new_progress = min(increment, task["required_count"])
            is_completed = new_progress >= task["required_count"]

            supabase.table("user_daily_tasks").insert({
                "user_id": user_id,
                "group_id": group_id,
                "task_id": task["id"],
                "progress": new_progress,
                "is_completed": is_completed,
                "completed_date": today
            }).execute()

        # إذا تم إكمال المهمة، أعطي المكافأة
        if is_completed and new_progress == task["required_count"]:
            await give_task_reward(user_id, group_id, task)
            return True

        return False
    except Exception as e:
        print(f"خطأ في update_task_progress: {e}")
        return False

async def give_task_reward(user_id, group_id, task):
    """إعطاء مكافأة المهمة"""
    try:
        # تحديث XP والكوينز
        res = supabase.table("group_members").select("xp, coins").eq("user_id", user_id).eq("group_id", group_id).execute()
        if res.data:
            current_data = res.data[0]
            new_xp = current_data["xp"] + task["xp_reward"]
            new_coins = current_data["coins"] + task["coins_reward"]

            supabase.table("group_members").update({
                "xp": new_xp,
                "coins": new_coins,
                "updated_at": datetime.now().isoformat()
            }).eq("user_id", user_id).eq("group_id", group_id).execute()

        # تسجيل المعاملة
        await log_transaction(user_id, group_id, "task_reward", task["xp_reward"], f"مكافأة إكمال مهمة: {task['task_name']}")
    except Exception as e:
        print(f"خطأ في give_task_reward: {e}")

# ==================================
# 🏆 نظام الشارات
# ==================================

async def check_and_award_badges(user_id, group_id):
    """فحص وإعطاء الشارات المستحقة"""
    try:
        # الحصول على بيانات المستخدم
        user_data = supabase.table("group_members").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        if not user_data.data:
            return []

        user = user_data.data[0]

        # الحصول على الشارات التي يملكها المستخدم
        user_badges = supabase.table("user_badges").select("badge_id").eq("user_id", user_id).eq("group_id", group_id).execute()
        owned_badge_ids = [ub["badge_id"] for ub in user_badges.data]

        # الحصول على جميع الشارات النشطة
        all_badges = supabase.table("badges").select("*").eq("is_active", True).execute()

        new_badges = []
        for badge in all_badges.data:
            if badge["id"] in owned_badge_ids:
                continue

            # فحص متطلبات الشارة
            should_award = False

            if badge["requirement_type"] == "level" and user["level"] >= badge["requirement_value"]:
                should_award = True
            elif badge["requirement_type"] == "xp" and user["xp"] >= badge["requirement_value"]:
                should_award = True
            elif badge["requirement_type"] == "messages" and user.get("total_messages", 0) >= badge["requirement_value"]:
                should_award = True
            elif badge["requirement_type"] == "streak":
                # فحص streak المكافآت اليومية
                daily_data = supabase.table("daily_rewards").select("streak_count").eq("user_id", user_id).eq("group_id", group_id).execute()
                if daily_data.data and daily_data.data[0]["streak_count"] >= badge["requirement_value"]:
                    should_award = True
            elif badge["requirement_type"] == "thanks":
                # فحص عدد مرات الشكر المستلمة
                thanks_data = supabase.table("thank_you_cooldown").select("total_thanks_received").eq("user_id", user_id).eq("group_id", group_id).execute()
                if thanks_data.data and thanks_data.data[0]["total_thanks_received"] >= badge["requirement_value"]:
                    should_award = True
            elif badge["requirement_type"] == "daily_tasks_completed":
                # فحص عدد المهام اليومية المكتملة
                completed_tasks_data = supabase.table("user_daily_tasks").select("id").eq("user_id", user_id).eq("group_id", group_id).eq("is_completed", True).execute()
                if len(completed_tasks_data.data) >= badge["requirement_value"]:
                    should_award = True

            if should_award:
                # منح الشارة
                supabase.table("user_badges").insert({
                    "user_id": user_id,
                    "group_id": group_id,
                    "badge_id": badge["id"]
                }).execute()
                new_badges.append(badge)

        return new_badges
    except Exception as e:
        print(f"خطأ في check_and_award_badges: {e}")
        return []

async def get_user_badges(user_id, group_id):
    """الحصول على شارات المستخدم"""
    try:
        result = supabase.table("user_badges").select("*, badges(*)").eq("user_id", user_id).eq("group_id", group_id).execute()
        return [item["badges"] for item in result.data]
    except Exception as e:
        print(f"خطأ في get_user_badges: {e}")
        return []

# ==================================
# 📊 إحصائيات متقدمة
# ==================================

async def get_user_rank(user_id, group_id):
    """الحصول على ترتيب المستخدم"""
    try:
        # استخدام الدالة المخزنة في قاعدة البيانات
        result = supabase.rpc("get_user_rank", {"input_user_id": user_id, "input_group_id": group_id}).execute()
        return result.data if result.data else 1
    except:
        try:
            # حساب الترتيب يدوياً في حالة عدم وجود الدالة
            user_data = supabase.table("group_members").select("xp").eq("user_id", user_id).eq("group_id", group_id).execute()
            if not user_data.data:
                return 1

            user_xp = user_data.data[0]["xp"]
            higher_users = supabase.table("group_members").select("user_id").eq("group_id", group_id).gt("xp", user_xp).execute()
            return len(higher_users.data) + 1
        except Exception as e:
            print(f"خطأ في get_user_rank: {e}")
            return 1

async def get_leaderboard(group_id, limit=10, order_by="xp"):
    """الحصول على قائمة المتصدرين"""
    try:
        result = supabase.table("group_members").select("user_id, username, xp, coins, level").eq("group_id", group_id).order(order_by, desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"خطأ في get_leaderboard: {e}")
        return []

# ==================================
# 🔧 دوال مساعدة إضافية
# ==================================

async def log_transaction(user_id, group_id, transaction_type, amount, description=""):
    """تسجيل معاملة في سجل المعاملات"""
    try:
        supabase.table("transaction_log").insert({
            "user_id": user_id,
            "group_id": group_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "description": description
        }).execute()
    except Exception as e:
        print(f"خطأ في log_transaction: {e}")

async def get_user_statistics(user_id, group_id):
    """الحصول على إحصائيات مفصلة للمستخدم"""
    try:
        # بيانات المستخدم الأساسية
        user_data = supabase.table("group_members").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()

        # إحصائيات المعاملات
        transactions = supabase.table("transaction_log").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()

        # عدد الشارات
        badges_count = len(await get_user_badges(user_id, group_id))

        # الترتيب
        rank = await get_user_rank(user_id, group_id)

        return {
            "user": user_data.data[0] if user_data.data else None,
            "transactions_count": len(transactions.data),
            "badges_count": badges_count,
            "rank": rank
        }
    except Exception as e:
        print(f"خطأ في get_user_statistics: {e}")
        return {
            "user": None,
            "transactions_count": 0,
            "badges_count": 0,
            "rank": 1
        }

# ==================================
# 👋 معالج الأعضاء الجدد (تم نقله لأعلى)
# ==================================

@app.on_message(filters.new_chat_members & filters.group)
async def new_chat_members_handler(client, message):
    """معالج الأعضاء الجدد وإضافة البوت للمجموعات"""
    try:
        for member in message.new_chat_members:
            if member.id == (await client.get_me()).id:  # البوت تمت إضافته للمجموعة
                chat_id = message.chat.id
                chat_title = message.chat.title or "مجموعة غير معروفة"
                owner_id = message.from_user.id # الشخص الذي أضاف البوت
                owner_username = message.from_user.first_name or "مستخدم"

                print(f"تم إضافة البوت للمجموعة {chat_id} بواسطة {owner_id}")

                # تسجيل المجموعة في جدول group_admins مع الشخص الذي أضاف البوت كأدمن
                try:
                    # التحقق من وجود السجل أولاً
                    existing_record = supabase.table("group_admins").select("*").eq("group_id", chat_id).eq("admin_id", owner_id).execute()

                    if not existing_record.data:
                        supabase.table("group_admins").insert({
                            "group_id": chat_id,
                            "group_name": chat_title,
                            "admin_id": owner_id,
                            "admin_username": owner_username,
                            "is_group_owner": True,
                            "created_at": datetime.now().isoformat()
                        }).execute()
                        print(f"تم تسجيل {owner_username} كمدير للمجموعة {chat_id}")

                except Exception as e:
                    print(f"خطأ في تسجيل المجموعة أو الأدمن: {e}")
                    asyncio.create_task(client.send_message(chat_id, f"👋 أهلاً يا {owner_username}!\nتم تفعيل البوت بنجاح، ولكن حدث خطأ بسيط في التسجيل."))

                # Enhanced Welcome Message
                welcome_msg = (
                    f"🎉 **Welcome, {owner_username}!**\n\n"
                    f"✅ The bot has been successfully activated in **{chat_title}**\n\n"
                    f"🔥 **Available Features:**\n"
                    f"💰 **Coins & Points System**\n"
                    f"🏆 **Levels & Badges**\n"
                    f"🛒 **Temporary Admin Shop**\n"
                    f"📋 **Daily Tasks**\n"
                    f"👑 **Advanced Clan System**\n"
                    f"⚔️ **Clan Wars & Challenges**\n"
                    f"🎁 **Enhanced Rewards System**\n"
                    f"👥 **Member Invitation Rewards**\n"
                    f"📊 **Weekly & Monthly Leaderboards**\n"
                    f"👑 **You've been automatically registered as the bot admin for this group.**\n\n"
                    f"📚 **To get started:**\n"
                    f"• /xp - **View your enhanced profile**\n"
                    f"• /shop - **Open the shop**\n"
                    f"• /cc [name] [tag] - **Create a clan**\n"
                    f"• /help - **Help & Commands**\n\n"
                    f"🚀 **Let the adventure in the world of knowledge begin!**"
                )

                await client.send_message(chat_id, welcome_msg)

            # التحقق مما إذا كان العضو الجديد هو Super Admin
            elif member.id in SUPER_ADMIN_IDS:
                await client.send_message(message.chat.id, f"👑 **مرحباً بعودتك يا Super Admin** <a href=\"tg://user?id={member.id}\">{member.first_name}</a>!\n🔥 **وجودك يشرفنا ويضيف قوة للمجموعة!**")
            
            # معالجة الأعضاء الجدد العاديين
            else:
                # تسجيل العضو الجديد
                new_member_id = member.id
                new_member_username = member.first_name or "عضو جديد"
                inviter_id = message.from_user.id
                inviter_username = message.from_user.first_name or "مستخدم"
                
                # إنشاء حساب للعضو الجديد
                await get_or_create_user(new_member_id, message.chat.id, new_member_username)
                
                # تحديث حقل invited_by للعضو الجديد
                supabase.table("group_members").update({
                    "invited_by": inviter_id
                }).eq("user_id", new_member_id).eq("group_id", message.chat.id).execute()
                
                # إعطاء مكافأة للمدعو (إذا لم يكن البوت)
                if inviter_id != (await client.get_me()).id and inviter_id != new_member_id:
                    reward_msg = await handle_new_member_invitation(inviter_id, new_member_id, message.chat.id, inviter_username)
                    if reward_msg:
                        await client.send_message(message.chat.id, reward_msg)
                
                # رسالة ترحيب للعضو الجديد
                welcome_new_member_msg = (
                    f"🎉 **مرحباً بك** <a href=\"tg://user?id={new_member_id}\">{new_member_username}</a> **في مجتمعنا الرائع!**\n\n"
                    f"✨ **نحن سعداء جداً بانضمامك إلينا!**\n\n"
                    f"🎮 **ابدأ رحلتك الآن:**\n"
                    f"📊 /xp - **شاهد ملفك الشخصي**\n"
                    f"🎁 /daily - **احصل على مكافأتك اليومية**\n"
                    f"🏆 /cc [اسم] [تاج] - **أنشئ كلانك الخاص**\n"
                    f"💖 /ty - **اشكر الأعضاء المفيدين**\n\n"
                    f"🚀 **استمتع بالتفاعل واكسب النقاط والمكافآت!**"
                )
                
                await client.send_message(message.chat.id, welcome_new_member_msg)

    except Exception as e:
        print(f"خطأ في new_chat_members_handler: {e}")

# ==================================
# 🎮 الأوامر الأساسية
# ==================================

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    try:
        if message.chat.type == "private":
            await message.reply_text(
                "🌟 **أهلاً وسهلاً بك في عالم المعرفة والنمو!** 🌟\n\n"
                "🎯 **ما يميزنا:**\n"
                "📚 مجتمع تعليمي تفاعلي\n"
                "💡 تبادل الخبرات والمعرفة\n"
                "🎁 نظام مكافآت متقدم\n"
                "🏆 تحديات ومهام يومية\n\n"
                "⚡ **كيف تربح النقاط:**\n"
                "💬 شارك في النقاشات (+15-30 XP)\n"
                "🎁 اطلب مكافأتك اليومية (+400 XP)\n"
                "💖 اشكر الأعضاء المفيدين (+500 XP للمشكور)\n"
                "📋 أكمل المهام اليومية (مكافآت متنوعة)\n\n"
                "🛒 **متجرنا المميز:**\n"
                "🛡️ اشتري رتبة أدمن مؤقت\n"
                "💱 استبدل XP بكوينز\n"
                "🏅 واكسب شارات حصرية\n\n"
                "🚀 **البداية:**\n"
                "📊 /xp - شاهد تقدمك\n"
                "🛒 /shop - زور المتجر\n"
                "📋 /tasks - المهام اليومية\n"
                "🏆 /badges - شاراتك\n\n"
                "✨ **انضم الآن وكن جزءاً من رحلة التطوير المستمر!**"
            )
        else:
            user_id = message.from_user.id
            username = message.from_user.first_name
            await get_or_create_user(user_id, message.chat.id, username)

        welcome_group_msg = (
    f"🎉 **Welcome, {username}, to our amazing community!**\n\n"
    f"We’re **thrilled** to have you on board. You’ve just taken your first step into a world full of **fun**, **challenges**, and **rewards**! 🚀\n\n"
    f"✅ You’ve been **successfully registered** in our **points and rewards system**.\n"
    f"From now on, everything you do here can help you **level up**, earn **coins**, and unlock **awesome perks**.\n\n"
    f"**Here’s how to get started:**\n"
    f"📚 **/xp** – View your current XP and level\n"
    f"🛒 **/shop** – Browse the exclusive in-group shop\n"
    f"🎁 **/daily** – Claim your daily login reward\n"
    f"🎯 **Complete tasks**, **interact**, and **grow your rank**!\n\n"
    f"✨ Whether you're here to **have fun**, **compete**, or just **chill** — there’s something for everyone.\n"
    f"Feel free to explore, connect with others, and most importantly, **enjoy the journey**. 🌟\n\n"
    f"💬 Got questions? Just type **/help** and we’ll guide you.\n\n"
    f"Once again, **welcome aboard** — let’s make this experience **unforgettable**! 💖"
)

        await message.reply_text(welcome_group_msg)
    except Exception as e:
        print(f"خطأ في start_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

@app.on_message(filters.command("help") & filters.group)
async def help_cmd(client, message):
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎮 Basic commands ", callback_data=f"help_basic_{user_id}"),
                InlineKeyboardButton("🎁 Rewards", callback_data=f"help_rewards_{user_id}")
            ],
            [
                InlineKeyboardButton("📋 Tasks & Badges ", callback_data=f"help_tasks_{user_id}"),
                InlineKeyboardButton("📊 Statistics", callback_data=f"help_stats_{user_id}")
            ],
            [
                InlineKeyboardButton("🛒 Shopping", callback_data=f"help_shop_{user_id}"),
                InlineKeyboardButton("⚙️ Admin Commands ", callback_data=f"help_admin_{user_id}")
            ]
        ])

        help_main_text = (
    "📖 **Welcome to the Help Guide!** 📖\n\n"
    "🎯 **Choose a section you'd like to learn more about:**\n\n"
    "✨ Each category includes **detailed explanations** and a full list of **available commands**.\n"
    "💡 **Tip:** Use the buttons below to navigate easily between sections and discover all the bot's features!\n\n"
    "If you ever feel lost or need guidance, this is the perfect place to start. 😊\n"
    "We're here to make your experience smooth and enjoyable!\n\n"
    "❤️ **Made with love by @Mavdiii**"
)


        await message.reply_text(help_main_text, reply_markup=keyboard)
    except Exception as e:
        print(f"خطأ في help_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

@app.on_message(filters.command("xp") & filters.group)
async def xp_cmd(client, message):
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name
        
        # الحصول على الإحصائيات المحسنة
        enhanced_stats = await get_enhanced_user_stats(user_id, message.chat.id)
        
        # إنشاء الرسالة المحسنة
        msg = enhanced_xp_msg(enhanced_stats, user_id, username)
        
        await message.reply_text(msg)
    except Exception as e:
        print(f"خطأ في xp_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

@app.on_message(filters.command("coins") & filters.group)
async def coins_cmd(client, message):
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name
        user = await get_or_create_user(user_id, message.chat.id, username)
        if user:
            coins = user.get("coins", 0)
            await message.reply_text(f"💰 **Your current coins**: {coins}")
            
        else:
            await message.reply_text("حدث خطأ، حاول مرة أخرى.")
    except Exception as e:
        print(f"خطأ في coins_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# أمر المكافآت اليومية
@app.on_message(filters.command("daily") & filters.group)
async def daily_cmd(client, message):
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name

        # التأكد من وجود المستخدم في قاعدة البيانات
        await get_or_create_user(user_id, message.chat.id, username)

        # محاولة طلب المكافأة اليومية المحسنة
        success, response_msg = await check_and_claim_daily_reward_enhanced(user_id, message.chat.id, username)

        await message.reply_text(response_msg)
    except Exception as e:
        print(f"خطأ في daily_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# أمر الشكر
@app.on_message(filters.command("ty") & filters.group)
async def thank_you_cmd(client, message):
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name

        # التحقق من أن الرسالة رد على رسالة أخرى
        if not message.reply_to_message:
            await message.reply_text("❌ **Oops! To thank someone, you need to reply to their message.**")
            return

        # التحقق من أن المستخدم لا يشكر نفسه
        thanked_user_id = message.reply_to_message.from_user.id
        if user_id == thanked_user_id:
            await message.reply_text("😅 **Nice try... but you can't thank yourself!**")

            return

        # التحقق من أن المستخدم المشكور ليس بوت
        if message.reply_to_message.from_user.is_bot:
            await message.reply_text("🤖 **لا يمكن شكر البوتات!**")
            return

        # التأكد من وجود المستخدم الذي يقوم بالشكر في قاعدة البيانات
        await get_or_create_user(user_id, message.chat.id, username)

        # التحقق من cooldown
        can_thank, cooldown_msg = await check_thank_you_cooldown(user_id, message.chat.id)
        if not can_thank:
            await message.reply_text(cooldown_msg)
            return

        # تسجيل استخدام أمر الشكر
        await record_thank_you_usage(user_id, message.chat.id)

        # إعطاء المكافأة المحسنة للشخص المشكور
        thanked_username = message.reply_to_message.from_user.first_name
        reward_msg = await give_thank_you_reward_enhanced(thanked_user_id, message.chat.id, thanked_username)

        # تحديث تقدم المهام
        await update_task_progress(user_id, message.chat.id, "thank_someone", 1)

        await message.reply_text(reward_msg)
    except Exception as e:
        print(f"خطأ في thank_you_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# ==================================
# 🎮 الأوامر الجديدة المحسنة
# ==================================

# أمر المهام اليومية
@app.on_message(filters.command("tasks") & filters.group)
async def daily_tasks_cmd(client, message):
    try:
        user_id = message.from_user.id
        group_id = message.chat.id
        username = message.from_user.first_name

        await get_or_create_user(user_id, group_id, username)
        tasks = await get_user_daily_tasks(user_id, group_id)

        if not tasks:
            await message.reply_text("❌ لا توجد مهام متاحة حالياً!")
            return

        tasks_text = f"📋 **مهامك اليومية يا {username}:**\n\n"

        for task in tasks:
            status = "✅" if task["is_completed"] else "⏳"
            progress_percentage = (task["progress"] * 100) // task["required_count"] if task["required_count"] > 0 else 0
            progress_bar = "▰" * (progress_percentage // 10) + "▱" * (10 - (progress_percentage // 10))

            tasks_text += f"{status} **{task['description']}**\n"
            tasks_text += f"📊 التقدم: {task['progress']}/{task['required_count']} {progress_bar}\n"
            tasks_text += f"🎁 المكافأة: {task['xp_reward']} XP + {task['coins_reward']} كوينز\n\n"

        await message.reply_text(tasks_text)
    except Exception as e:
        print(f"خطأ في daily_tasks_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# أمر الشارات
@app.on_message(filters.command("badges") & filters.group)
async def user_badges_cmd(client, message):
    try:
        user_id = message.from_user.id
        group_id = message.chat.id
        username = message.from_user.first_name

        await get_or_create_user(user_id, group_id, username)
        badges = await get_user_badges(user_id, group_id)

        if not badges:
            await message.reply_text(f"🏆 {username}، لم تحصل على أي شارات بعد!\nتفاعل أكثر لتحصل على شاراتك الأولى! 💪")
            return

        badges_text = f"🏆 **شارات {username}:**\n\n"

        for badge in badges:
            badges_text += f"{badge['icon']} **{badge['name']}**\n"
            badges_text += f"📝 {badge['description']}\n\n"

        await message.reply_text(badges_text)
    except Exception as e:
        print(f"خطأ في user_badges_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# أمر قائمة المتصدرين
@app.on_message(filters.command("leaderboard") & filters.group)
async def leaderboard_cmd(client, message):
    try:
        group_id = message.chat.id

        leaders = await get_leaderboard(group_id, 10, "xp")

        if not leaders:
            await message.reply_text("📊 لا توجد بيانات كافية لعرض قائمة المتصدرين!")
            return

        leaderboard_text = "🏆 **قائمة المتصدرين (حسب XP):**\n\n"

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for i, leader in enumerate(leaders):
            medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
            leaderboard_text += f"{medal} **{leader['username']}**\n"
            leaderboard_text += f"🧙‍♂️ XP: {leader['xp']} | 🏅 Level: {leader['level']} | 💰 Coins: {leader['coins']}\n\n"

        await message.reply_text(leaderboard_text)
    except Exception as e:
        print(f"خطأ في leaderboard_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# أمر ترتيبي
@app.on_message(filters.command("myrank") & filters.group)
async def my_rank_cmd(client, message):
    try:
        user_id = message.from_user.id
        group_id = message.chat.id
        username = message.from_user.first_name

        await get_or_create_user(user_id, group_id, username)
        rank = await get_user_rank(user_id, group_id)
        stats = await get_user_statistics(user_id, group_id)

        rank_text = f"📊 **Your Stats, {username}:**\n\n"
        rank_text += f"🏆 **Rank**: #{rank} in the group\n"
        rank_text += f"🏅 **Badges Collected**: {stats['badges_count']}\n"
        rank_text += f"📈 **Messages Sent**: {stats['transactions_count']}\n"


        await message.reply_text(rank_text)
    except Exception as e:
        print(f"خطأ في my_rank_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# أمر المستويات المحدث
@app.on_message(filters.command("levels") & filters.group)
async def levels_cmd(client, message):
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ Basic → Elite", callback_data=f"levels_basic_{user_id}_{username}")],
            [InlineKeyboardButton("💎 VIP → Legend", callback_data=f"levels_vip_{user_id}_{username}")],
            [InlineKeyboardButton("🛡 Admin → Manager", callback_data=f"levels_admin_{user_id}_{username}")],
            [InlineKeyboardButton("👑 CEO → CO-OWNER", callback_data=f"levels_leader_{user_id}_{username}")]
        ])

        await message.reply_text("📊 **Please select the level category you'd like to explore:**", reply_markup=keyboard)

    except Exception as e:
        print(f"خطأ في levels_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# ==================================
# 🛒 المتجر والمعاملات
# ==================================

@app.on_message(filters.command("shop") & filters.group)
async def shop_cmd(client, message):
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡 buy temporary Admin ", callback_data=f"shop_admin_{user_id}_{username}")],
            [InlineKeyboardButton("🔁 Reblace XP To Coins ", callback_data=f"exchange_menu_{user_id}_{username}")],
            [InlineKeyboardButton("ℹ️ Important informations ", callback_data=f"important_info_{user_id}_{username}")]
        ])
        await message.reply_text(
             f"🛒**Hey** <a href=\"tg://user?id={user_id}\">{username}</a>, **welcome to the in-game shop!**\n\nYou’ve unlocked access to the **Temporary Admin Rank**! 👑\nTrade your hard-earned 💰 **coins** — collected through your activity and quests — to claim your spot.\n\n🔄 **Low on coins?** No worries! Use the **Exchange** button below to convert your XP into coins and keep progressing.\n⚔️ When you're ready, gear up and claim your admin role right from here. Let the power be yours!\n\n❤️ **Made with love by @Mavdiii**",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"خطأ في shop_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

@app.on_callback_query(filters.regex(r"shop_admin_(\d+)_(.+)"))
async def shop_admin_menu(client, callback_query):
    try:
        owner_id = int(callback_query.data.split("_")[2])
        owner_name = callback_query.data.split("_", 3)[3]
        user_id = callback_query.from_user.id

        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}",
                show_alert=True
            )
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("One day - 1500 Coins", callback_data=f"buy_admin_1_{owner_id}_{owner_name}")],
            [InlineKeyboardButton("Two days - 3000 Coins", callback_data=f"buy_admin_2_{owner_id}_{owner_name}")],
            [InlineKeyboardButton("Three days -4500 Coins", callback_data=f"buy_admin_3_{owner_id}_{owner_name}")]
        ])

        await callback_query.edit_message_text(
            f"**HI** **<a href=\"tg://user?id={user_id}\">{owner_name}</a>** **Choose the appropriate admin period for you:**",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"خطأ في shop_admin_menu: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"buy_admin_(\d+)_(\d+)_(.+)"))
async def buy_admin_cb(client, callback_query):
    try:
        data = callback_query.data.split("_")
        days = int(data[2])
        owner_id = int(data[3])
        owner_name = "_".join(data[4:])
        user_id = callback_query.from_user.id
        user_name = callback_query.from_user.first_name

        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}",
                show_alert=True
            )
            return

        # إصلاح المفتاح لاستخدام str بدلاً من int
        price = ADMIN_PRICES[str(days)]["coins"]
        print(f"محاولة شراء أدمن: المستخدم {user_id}، المدة {days} أيام، السعر {price}")

        ok, msg, pay_msg = await buy_admin(
            user_id, callback_query.message.chat.id, user_name, days, price
        )

        print(f"نتيجة شراء الأدمن: نجح={ok}, رسالة={msg[:50]}...")

        if ok:
            await callback_query.edit_message_text(msg)
        else:
            # إظهار الرسالة الصحيحة للخطأ
            await callback_query.answer(msg if msg else "💔 Unfortunately you don't have enough coins to buy it😔", show_alert=True)
    except Exception as e:
        print(f"خطأ في buy_admin_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"exchange_menu_(\d+)_(.+)"))
async def exchange_menu(client, callback_query):
    try:
        user_id = int(callback_query.data.split("_")[2])
        user_name = callback_query.data.split("_", 3)[3]
        from_user = callback_query.from_user

        if from_user.id != user_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {user_name}", show_alert=True)
            return

        # قائمة أزرار خيارات الاستبدال
        exchange_buttons = [
            [InlineKeyboardButton(f"{opt['xp']} XP ➡️ {opt['coins']} Coins", callback_data=f"exchange_xp_{opt['xp']}_{opt['coins']}_{user_id}_{user_name}")]
            for opt in EXCHANGE_OPTIONS
        ]

        await callback_query.edit_message_text(
            f"💱 Select the amount of **XP** you want to exchange to **Coins** <a href=\"tg://user?id={user_id}\">{user_name}</a>",
            reply_markup=InlineKeyboardMarkup(exchange_buttons)
        )
    except Exception as e:
        print(f"خطأ في exchange_menu: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"exchange_xp_(\d+)_(\d+)_(\d+)_(.+)"))
async def exchange_xp_to_coins_cb(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        xp_needed = int(parts[2])
        coins_reward = int(parts[3])
        user_id = int(parts[4])
        user_name = "_".join(parts[5:])
        from_user = callback_query.from_user

        if from_user.id != user_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {user_name}",
                show_alert=True
            )
            return

        success, msg = await exchange_xp_to_coins(user_id, callback_query.message.chat.id, xp_needed, coins_reward)

        if success:
            await callback_query.edit_message_text(msg)
        else:
            await callback_query.answer(msg, show_alert=True)
    except Exception as e:
        print(f"خطأ في exchange_xp_to_coins_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

# ==================================
# ⚙️ أوامر الإدارة
# ==================================

# أمر إضافة XP (للمالك الرئيسي وأصحاب المجموعات)
@app.on_message(filters.command("addxp") & filters.group)
async def add_xp_cmd(client, message):
    try:
        user_id = message.from_user.id

        # التحقق من الصلاحيات
        has_permission = await check_admin_permissions(user_id, message.chat.id, client)
        if not has_permission:
            await message.reply_text("❌ **ليس لديك صلاحية لاستخدام هذا الأمر!**")
            return

        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
            amount = int(message.command[1]) if len(message.command) > 1 else None
            if amount is None:
                await message.reply_text("❌ **Oops! You forgot to enter the amount.**\nJust reply to a message and use: `/addxp [amount]` 😊")
                return
        else:
            if len(message.command) < 3:
              await message.reply_text("❌ **Oops! That seems like a wrong usage.**\nYou can either use: `/addxp [user_id] [amount]`\n**or simply reply to the user's message with:** `/addxp [amount]` 😊")
              return
            target_user_id = int(message.command[1])
            amount = int(message.command[2])

        # إضافة XP للمستخدم
        success = await add_user_xp(target_user_id, message.chat.id, amount)
        if success:
            await message.reply_text(f"✅ **Successfully added {amount} XP to user ID:** {target_user_id}")
        else:
            await message.reply_text("❌ **لم يتم العثور على العضو في قاعدة البيانات!**")
    except ValueError:
        await message.reply_text("❌ **يرجى إدخال أرقام صحيحة فقط!**")
    except Exception as e:
        print(f"خطأ في add_xp_cmd: {e}")
        await message.reply_text("❌ **حدث خطأ، حاول مرة أخرى!**")

# أمر إضافة الكوينز (محدث مع الصلاحيات الجديدة)
@app.on_message(filters.command("addcoins") & filters.group)
async def add_coins_cmd(client, message):
    try:
        user_id = message.from_user.id

        # التحقق من الصلاحيات
        has_permission = await check_admin_permissions(user_id, message.chat.id, client)
        if not has_permission:
            await message.reply_text("❌ **ليس لديك صلاحية لاستخدام هذا الأمر!**")
            return

        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
            amount = int(message.command[1]) if len(message.command) > 1 else None
            if amount is None:
                await message.reply_text("❌ **يرجى تحديد الكمية!**\nاستخدم: `/addcoins [amount]` بالرد على الرسالة")
                return
        else:
            if len(message.command) < 3:
                await message.reply_text("❌ **استخدام خاطئ!**\nاستخدم: `/addcoins [user_id] [amount]`")
                return
            target_user_id = int(message.command[1])
            amount = int(message.command[2])

        # إضافة الكوينز للمستخدم
        success = await update_user_coins(target_user_id, message.chat.id, amount)
        if success:
            await message.reply_text(f"✅ **تمت إضافة {amount} كوينز لعضو ID**: {target_user_id}")
        else:
            await message.reply_text("❌ **لم يتم العثور على العضو في قاعدة البيانات!**")
    except ValueError:
        await message.reply_text("❌ **يرجى إدخال أرقام صحيحة فقط!**")
    except Exception as e:
        print(f"خطأ في add_coins_cmd: {e}")
        await message.reply_text("❌ **حدث خطأ، حاول مرة أخرى!**")

# ==================================
# 📋 معالجات الواجهات (مبسطة)
# ==================================

@app.on_callback_query(filters.regex(r"important_info_(\d+)_(.+)"))
async def important_info_cb(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        owner_id = int(parts[2])
        owner_name = "_".join(parts[3:])
        user_id = callback_query.from_user.id
        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}", show_alert=True)
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 عرض المستويات", callback_data=f"levels_{owner_id}_{owner_name}")],
            [InlineKeyboardButton("💰 طرق كسب المال والXP", callback_data=f"earning_methods_{owner_id}_{owner_name}")],
            [InlineKeyboardButton("🛡 كيف أصبح أدمن دائم؟", callback_data=f"info_padmin_{owner_id}_{owner_name}")],
            [InlineKeyboardButton("🔙 رجوع للمتجر", callback_data=f"shop_menu_{owner_id}_{owner_name}")]
        ])
        msg = "ℹ️ **اختار نوع المعلومات اللى عايز تعرفها:**"
        await callback_query.edit_message_text(text=msg, reply_markup=keyboard)
    except Exception as e:
        print(f"خطأ في important_info_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"shop_menu_(\d+)_(.+)"))
async def shop_menu_cb(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        user_id = int(parts[2])
        username = "_".join(parts[3:])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡 شراء أدمن", callback_data=f"shop_admin_{user_id}_{username}")],
            [InlineKeyboardButton("متجر الإستبدال 🔁", callback_data=f"exchange_menu_{user_id}_{username}")],
            [InlineKeyboardButton("ℹ️ معلومات مهمة", callback_data=f"important_info_{user_id}_{username}")]
        ])
        await callback_query.edit_message_text(
            f"🛒 **أهلاً بيك يا** <a href=\"tg://user?id={user_id}\">{username}</a> **في المتجر بتاعنا!**\n\nدلوقتي تقدر تشتري **رتبة أدمن مؤقت** في الجروب باستخدام الكوينز 💰 اللي جمّعتها من نشاطك!\n\n🔄 **لو مش معاك كوينز كفاية، استبدل الـ XP بتوعك بكوينز عن طريق زر Exchange بالأسفل**\n👑 **ولما تجمع كوينز كفاية، اطلب الأدمن من هنا مباشرة.**",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"خطأ في shop_menu_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"earning_methods_(\d+)_(.+)"))
async def earning_methods_cb(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        owner_id = int(parts[2])
        owner_name = "_".join(parts[3:])
        user_id = callback_query.from_user.id
        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}", show_alert=True)
            return
        xp_msg = (
            "💰 **طرق كسب الكوينز والـ XP:**\n\n"
            "📝 **من المحادثات والرسائل:**\n"
            "• رسالة قصيرة (أقل من 100 حرف): 15 XP + 10 كوينز\n"
            "• رسالة طويلة (أكثر من 100 حرف): 30 XP + 20 كوينز\n\n"
            "🎁 **من المكافآت اليومية:**\n"
            "• `/daily` كل 24 ساعة: 400 XP + 200 كوينز\n\n"
            "💖 **من الشكر:**\n"
            "• شكر شخص بـ `/ty` (للمشكور): 500 XP + 300 كوينز\n"
            "• فترة الانتظار: 4 ساعات بين كل شكر\n\n"
            "📋 **من المهام اليومية:**\n"
            "• استخدم `/tasks` لرؤية المهام المتاحة\n"
            "• مكافآت متنوعة حسب نوع المهمة\n\n"
            "💱 **الاستبدال:**\n"
            "• يمكنك استبدال الـ XP بكوينز من المتجر"
        )
        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"important_info_{owner_id}_{owner_name}")]
        ])
        await callback_query.edit_message_text(
            text=xp_msg,
            reply_markup=back_button
        )
    except Exception as e:
        print(f"خطأ في earning_methods_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"levels_(\d+)_(.+)"))
async def show_levels_details(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        owner_id = int(parts[1])
        owner_name = "_".join(parts[2:])
        user_id = callback_query.from_user.id
        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}", show_alert=True)
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ Basic → Elite", callback_data=f"levels_basic_{owner_id}_{owner_name}")],
            [InlineKeyboardButton("💎 VIP → Legend", callback_data=f"levels_vip_{owner_id}_{owner_name}")],
            [InlineKeyboardButton("🛡 Admin → Manager", callback_data=f"levels_admin_{owner_id}_{owner_name}")],
            [InlineKeyboardButton("👑 CEO → CO-OWNER", callback_data=f"levels_leader_{owner_id}_{owner_name}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"important_info_{owner_id}_{owner_name}")]
        ])
        msg = "📊 ** Choose the level category you want to view**"
        await callback_query.edit_message_text(text=msg, reply_markup=keyboard)
    except Exception as e:
        print(f"خطأ في show_levels_details: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"levels_basic_(\d+)_(.+)"))
async def show_levels_basic(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        owner_id = int(parts[2])
        owner_name = "_".join(parts[3:])
        user_id = callback_query.from_user.id
        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}", show_alert=True)
            return
        msg = (
            "**Basic I → Basic V**\n"
            "**need Level 1 → Level 5**\n\n"

            "**Pro I → Pro V**\n"
            "**need Level 6 → Level 10**\n\n"

            "**Expert I → Expert V**\n"
            "**need Level 11 → Level 15**\n\n"

            "**Elite I → Elite V**\n"
            "**need Level 16 → Level 20**"
        )
        back_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"levels_{owner_id}_{owner_name}")]
        ])
        await callback_query.edit_message_text(text=msg, reply_markup=back_btn)
    except Exception as e:
        print(f"خطأ في show_levels_basic: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"levels_vip_(\d+)_(.+)"))
async def show_levels_vip(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        owner_id = int(parts[2])
        owner_name = "_".join(parts[3:])
        user_id = callback_query.from_user.id
        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}", show_alert=True)
            return
        msg = (
            "**VIP I → VIP V**\n"
            "**need Level 21 → Level 25**\n\n"

            "**Legend I → Legend V**\n"
            "**need Level 26 → Level 30**"
        )
        back_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"levels_{owner_id}_{owner_name}")]
        ])
        await callback_query.edit_message_text(text=msg, reply_markup=back_btn)
    except Exception as e:
        print(f"خطأ في show_levels_vip: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"levels_admin_(\d+)_(.+)"))
async def show_levels_admin(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        owner_id = int(parts[2])
        owner_name = "_".join(parts[3:])
        user_id = callback_query.from_user.id
        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}", show_alert=True)
            return
        msg = (
            "**Admin I → Admin V**\n"
            "**need Level 26 → Level 30**\n\n"

            "**Staff I → Staff V**\n"
            "**need Level 31 → Level 35**\n\n"

            "**Manager I → Manager V**\n"
            "**need Level 36 → Level 40**"
        )
        back_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"levels_{owner_id}_{owner_name}")]
        ])
        await callback_query.edit_message_text(text=msg, reply_markup=back_btn)
    except Exception as e:
        print(f"خطأ في show_levels_admin: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"levels_leader_(\d+)_(.+)"))
async def show_levels_leader(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        owner_id = int(parts[2])
        owner_name = "_".join(parts[3:])
        user_id = callback_query.from_user.id
        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}", show_alert=True)
            return
        msg = (
            "**CEO I → CEO V**\n"
            "**need Level 41 → Level 45**\n\n"

            "CO-OWNER I → CO-OWNER V\n"
            "**need Level 46 → Level 50**"
        )
        back_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"levels_{owner_id}_{owner_name}")]
        ])
        await callback_query.edit_message_text(text=msg, reply_markup=back_btn)
    except Exception as e:
        print(f"خطأ في show_levels_leader: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"info_padmin_(\d+)_(.+)"))
async def show_padmin_details(client, callback_query):
    try:
        parts = callback_query.data.split("_")
        owner_id = int(parts[2])
        owner_name = "_".join(parts[3:])
        user_id = callback_query.from_user.id
        if user_id != owner_id:
            await callback_query.answer(
                f"عذرا الامر مخصص فقط للمستخدم : {owner_name}",
                show_alert=True
            )
            return
        padmin_msg = """🛡 **How to Become a Permanent Admin in the Group?**\n\nIf you'd like to become a permanent admin (not just temporary), here's what you need to do:\n\n👣 **Stay active and engage regularly in the group.**\n\n💬 **Earn XP by participating, replying, and being part of the conversation.**\n\n🎯 **Keep leveling up until you reach Level 31 – Staff I.**\n\n📌 **Once you reach that level, the bot will automatically promote you and grant you permanent admin rights — no coins or subscriptions needed.**\n\n✨ **Stay consistent, be active, and become part of the leadership team!**"""
        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 back", callback_data=f"important_info_{owner_id}_{owner_name}")]
        ])
        await callback_query.edit_message_text(
            text=padmin_msg,
            reply_markup=back_button
        )
    except Exception as e:
        print(f"خطأ في show_padmin_details: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

# ==================================
# 📱 معالج الرسائل العادية
# ==================================

@app.on_message(filters.group & ~filters.command(["start", "help", "xp", "shop", "coins", "daily", "ty", "tasks", "badges", "leaderboard", "myrank", "levels", "addxp", "addcoins"]))
async def handle_message(client, message):
    try:
        # التحقق من أن الرسالة لها مرسل وليست من قناة
        if not message.from_user or not message.from_user.id:
            return
        
        # تجاهل رسائل البوتات
        if message.from_user.is_bot:
            return

        user_id = message.from_user.id
        username = message.from_user.first_name or "مستخدم"

        # تحديد نقاط XP و Coins بناءً على طول الرسالة
        if len(message.text or "") > 100:  # رسالة طويلة
            plus_xp = 30
            plus_coins = 20
        else:  # رسالة قصيرة
            plus_xp = 15
            plus_coins = 10

        congrats, new_badges = await update_user_xp(user_id, message.chat.id, username, plus_xp, plus_coins)

        # إرسال رسالة التهنئة إذا وُجدت
        if congrats:
            await message.reply_text(congrats)

        # إرسال رسالة الشارات الجديدة إذا وُجدت
        if new_badges:
            badges_text = f"🎉 **تهانينا {username}!** حصلت على شارات جديدة:\n\n"
            for badge in new_badges:
                badges_text += f"{badge['icon']} **{badge['name']}** - {badge['description']}\n"
            await message.reply_text(badges_text)
    except Exception as e:
        print(f"خطأ في handle_message: {e}")

# ==================================
# 🚀 تشغيل البوت
# ==================================

# ==================================
# 📖 معالجات أزرار المساعدة
# ==================================

@app.on_callback_query(filters.regex(r"help_basic_(\d+)"))
async def help_basic_cb(client, callback_query):
    try:
        owner_id = int(callback_query.data.split("_")[2])
        user_id = callback_query.from_user.id

        if user_id != owner_id:
            await callback_query.answer(
                "عذراً، هذا الأمر مخصص لك فقط!",
                show_alert=True
            )
            return

        basic_text = (
            "🎮 **Basic Commands:**\n\n"
            "• `/start` – Welcome message\n"
            "• `/xp` – View your XP and level\n"
            "• `/coins` – Check your coin balance\n"
            "• `/myrank` – See your group ranking\n\n"
            "💡 **Helpful Tip:**\n"
            "These commands are available to all members and can be used anytime!"
        )


        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 back to menu", callback_data=f"help_main_{owner_id}")]
        ])

        await callback_query.edit_message_text(text=basic_text, reply_markup=back_button)
    except Exception as e:
        print(f"خطأ في help_basic_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"help_rewards_(\d+)"))
async def help_rewards_cb(client, callback_query):
    try:
        owner_id = int(callback_query.data.split("_")[2])
        user_id = callback_query.from_user.id

        if user_id != owner_id:
            await callback_query.answer(
                "عذراً، هذا الأمر مخصص لك فقط!",
                show_alert=True
            )
            return

        rewards_text = (
            "🎁 **Rewards:**\n\n"
            "• `/daily` - Daily reward (every 24 hours)\n"
            "• `/ty` - Thank a member (reply to their message)\n\n"
            "🔥 **Other ways to earn points:**\n"
            "• 💬 Short messages: 15 XP + 10 coins\n"
            "• 📝 Long messages: 30 XP + 20 coins\n"
            "• 📋 إكمال المهام اليومية: مكافآت متنوعة"
        )

        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 back to menu", callback_data=f"help_main_{owner_id}")]
        ])

        await callback_query.edit_message_text(text=rewards_text, reply_markup=back_button)
    except Exception as e:
        print(f"خطأ في help_rewards_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"help_tasks_(\d+)"))
async def help_tasks_cb(client, callback_query):
    try:
        owner_id = int(callback_query.data.split("_")[2])
        user_id = callback_query.from_user.id

        if user_id != owner_id:
            await callback_query.answer(
                "عذراً، هذا الأمر مخصص لك فقط!",
                show_alert=True
            )
            return

        tasks_text = (
                "📋 **Tasks & Badges:**\n\n"
                "• `/tasks` – Your daily tasks\n"
                "• `/badges` – Your earned badges\n\n"
                "🎯 **Types of Tasks:**\n"
                "• 💬 Sending a certain number of messages\n"
                "• 🎁 Claiming daily rewards\n"
                "• 💖 Thanking other members\n"
                "• 🏆 Reaching specific levels"
        )

        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 back to menu", callback_data=f"help_main_{owner_id}")]
        ])

        await callback_query.edit_message_text(text=tasks_text, reply_markup=back_button)
    except Exception as e:
        print(f"خطأ في help_tasks_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"help_stats_(\d+)"))
async def help_stats_cb(client, callback_query):
    try:
        owner_id = int(callback_query.data.split("_")[2])
        user_id = callback_query.from_user.id

        if user_id != owner_id:
            await callback_query.answer(
                "عذراً، هذا الأمر مخصص لك فقط!",
                show_alert=True
            )
            return

        stats_text = (
                "📊 **Statistics:**\n\n"
                "• `/leaderboard` – Top players list\n"
                "• `/levels` – Level categories\n\n"
                "🎖️ **Level Tiers:**\n"
                "• ⭐ Basic → Elite (Levels 1–20)\n"
                "• 💎 VIP → Legend (Levels 21–30)\n"
                "• 🛡️ Admin → Manager (Levels 31–40)\n"
                "• 👑 CEO → CO-OWNER (Levels 41–50)"
        )

        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 back to menu", callback_data=f"help_main_{owner_id}")]
        ])

        await callback_query.edit_message_text(text=stats_text, reply_markup=back_button)
    except Exception as e:
        print(f"خطأ في help_stats_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"help_shop_(\d+)"))
async def help_shop_cb(client, callback_query):
    try:
        owner_id = int(callback_query.data.split("_")[2])
        user_id = callback_query.from_user.id

        if user_id != owner_id:
            await callback_query.answer(
                "عذراً، هذا الأمر مخصص لك فقط!",
                show_alert=True
            )
            return

        shop_text = (
               "🛒 **Shopping:**\n\n"
                "• `/shop` – Main shop menu\n\n"
                "💰 **Temporary Admin Prices:**\n"
                "• 1 Day: 1500 Coins\n"
                "• 2 Days: 3000 Coins\n"
                "• 3 Days: 4500 Coins\n"
                "💱 **Exchange XP for Coins:**\n"
                "• You can exchange your XP for coins in the shop\n"
                "• Use the `/exchange` command to see options\n\n"
        )

        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 back to menu", callback_data=f"help_main_{owner_id}")]
        ])

        await callback_query.edit_message_text(text=shop_text, reply_markup=back_button)
    except Exception as e:
        print(f"خطأ في help_shop_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"help_admin_(\d+)"))
async def help_admin_cb(client, callback_query):
    try:
        owner_id = int(callback_query.data.split("_")[2])
        user_id = callback_query.from_user.id

        if user_id != owner_id:
            await callback_query.answer(
                "عذراً، هذا الأمر مخصص لك فقط!",
                show_alert=True
            )
            return

        admin_text = (
                "⚙️ **Admin Commands:**\n\n"
                "• `/addxp` – Add XP to members\n"
                "• `/addcoins` – Add coins to members\n\n"
                "📝 **How to Use:**\n"
                "• `/addxp [amount]` (reply to a user's message)\n"
                "• or: `/addxp [user_id] [amount]`\n\n"
                "👑 **Who Can Use These Commands:**\n"
                "• Super Admins (bot developers like @Mavdiii)\n"
                "• Group Owners\n"
                "• Registered Admins in the system"
        )

        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 back to menu", callback_data=f"help_main_{owner_id}")]
        ])

        await callback_query.edit_message_text(text=admin_text, reply_markup=back_button)
    except Exception as e:
        print(f"خطأ في help_admin_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"help_main_(\d+)"))
async def help_main_cb(client, callback_query):
    try:
        owner_id = int(callback_query.data.split("_")[2])
        user_id = callback_query.from_user.id

        if user_id != owner_id:
            await callback_query.answer(
                "عذراً، هذا الأمر مخصص لك فقط!",
                show_alert=True
            )
            return

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎮 Basic Commands ", callback_data=f"help_basic_{owner_id}"),
                InlineKeyboardButton("🎁 Rewards", callback_data=f"help_rewards_{owner_id}")
            ],
            [
                InlineKeyboardButton("📋 Tasks & Badges ", callback_data=f"help_tasks_{owner_id}"),
                InlineKeyboardButton("📊 Statistics", callback_data=f"help_stats_{owner_id}")
            ],
            [
                InlineKeyboardButton("🛒 Shopiing", callback_data=f"help_shop_{owner_id}"),
                InlineKeyboardButton("⚙️ Admin Commands ", callback_data=f"help_admin_{owner_id}")
            ]
        ])

        help_main_text = (
            "📖 **مرحباً بك في دليل المساعدة!** 📖\n\n"
            "🎯 **اختر القسم الذي تريد معرفة المزيد عنه:**\n\n"
            "✨ **كل قسم يحتوي على الأوامر والشرح المفصل**\n"
            "💡 **نصيحة:** استخدم الأزرار أدناه للتنقل بسهولة!"
        )

        await callback_query.edit_message_text(text=help_main_text, reply_markup=keyboard)
    except Exception as e:
        print(f"خطأ في help_main_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

# ==================================
# 🚀 تشغيل البوت
# ==================================

if __name__ == "__main__":
    print("🤖 البوت المحسن والمصحح يعمل الآن...")
    print("✨ الميزات المتاحة:")
    print("   📋 نظام المهام اليومية")
    print("   🏆 نظام الشارات والألقاب")
    print("   📊 إحصائيات متقدمة")
    print("   💰 نظام مكافآت محسن")
    print("   🛒 متجر تفاعلي مصحح")
    print("   ⚙️ أوامر إدارة شاملة")
    print("   🔧 معالجة أخطاء محسنة")
    print("   👋 تسجيل تلقائي للمجموعات")
    print("🎮 جاهز لاستقبال الرسائل!")
    app.run()

from datetime import timedelta

class ClanManager:
    def __init__(self, supabase):
        self.supabase = supabase

    async def create_clan(self, user_id, group_id, name, tag):
        # التحقق مما إذا كان المستخدم يمتلك كلان بالفعل
        user_clan_res = self.supabase.table("clans").select("*").eq("leader_id", user_id).execute()
        if user_clan_res.data:
            return False, "❌ أنت تمتلك كلان بالفعل! لا يمكنك إنشاء كلان آخر."

        # التحقق مما إذا كان المستخدم عضواً في كلان آخر
        member_clan_res = self.supabase.table("clan_members").select("*").eq("user_id", user_id).execute()
        if member_clan_res.data:
            return False, "❌ أنت عضو في كلان آخر بالفعل! يجب أن تغادر الكلان الحالي أولاً."

        # التحقق من وجود كلان بنفس الاسم أو التاج
        existing_clan_res = self.supabase.table("clans").select("*").or_(f"name.eq.{name}", f"tag.eq.{tag}").execute()
        if existing_clan_res.data:
            return False, "❌ يوجد كلان بنفس الاسم أو التاج بالفعل! اختر اسماً أو تاجاُ آخر."

        # إنشاء الكلان
        new_clan = {
            "name": name,
            "tag": tag,
            "leader_id": user_id,
            "group_id": group_id, # إضافة group_id هنا
            "xp": 0,
            "level": 1,
            "coins": 0,
            "description": "",
            "created_at": datetime.now().isoformat()
        }
        clan_res = self.supabase.table("clans").insert(new_clan).execute()
        clan_id = clan_res.data[0]["id"]

        # إضافة القائد كعضو في الكلان
        clan_member = {
            "clan_id": clan_id,
            "user_id": user_id,
            "role": "leader",
            "joined_at": datetime.now().isoformat()
        }
        self.supabase.table("clan_members").insert(clan_member).execute()

        return True, f"✅ تم إنشاء كلان {name} [{tag}] بنجاح! ID الكلان: `{clan_id}`"

    async def join_clan(self, user_id, clan_id):
        # التحقق مما إذا كان المستخدم عضواً في كلان آخر
        member_clan_res = self.supabase.table("clan_members").select("*").eq("user_id", user_id).execute()
        if member_clan_res.data:
            return False, "❌ أنت عضو في كلان آخر بالفعل! يجب أن تغادر الكلان الحالي أولاً."

        # التحقق من وجود الكلان
        clan_res = self.supabase.table("clans").select("*").eq("id", clan_id).execute()
        if not clan_res.data:
            return False, "❌ الكلان غير موجود! تأكد من ID الكلان الصحيح."

        # إضافة العضو للكلان
        clan_member = {
            "clan_id": clan_id,
            "user_id": user_id,
            "role": "member",
            "joined_at": datetime.now().isoformat()
        }
        self.supabase.table("clan_members").insert(clan_member).execute()

        return True, f"✅ تم الانضمام إلى الكلان بنجاح!"

    async def leave_clan(self, user_id):
        # التحقق مما إذا كان المستخدم عضواً في كلان
        member_clan_res = self.supabase.table("clan_members").select("*").eq("user_id", user_id).execute()
        if not member_clan_res.data:
            return False, "❌ أنت لست في أي كلان!"

        clan_member = member_clan_res.data[0]
        clan_id = clan_member["clan_id"]

        # إذا كان المستخدم هو قائد الكلان، يجب عليه نقل القيادة أو حل الكلان أولاً
        clan_res = self.supabase.table("clans").select("*").eq("id", clan_id).eq("leader_id", user_id).execute()
        if clan_res.data:
            return False, "❌ لا يمكنك مغادرة الكلان كقائد! يجب عليك نقل القيادة أو حل الكلان أولاً."

        # حذف العضوية
        self.supabase.table("clan_members").delete().eq("user_id", user_id).execute()

        return True, "✅ تم مغادرة الكلان بنجاح!"

    async def get_user_clan(self, user_id):
        member_clan_res = self.supabase.table("clan_members").select("clan_id").eq("user_id", user_id).execute()
        if member_clan_res.data:
            clan_id = member_clan_res.data[0]["clan_id"]
            clan_res = self.supabase.table("clans").select("*").eq("id", clan_id).execute()
            return clan_res.data[0] if clan_res.data else None
        return None

    async def get_clan_members(self, clan_id):
        members_res = self.supabase.table("clan_members").select("user_id, role").eq("clan_id", clan_id).execute()
        return members_res.data

    async def get_top_clans(self, limit=10):
        top_clans_res = self.supabase.table("clans").select("*").order("xp", desc=True).limit(limit).execute()
        return top_clans_res.data

    async def add_member_xp(self, user_id, xp_amount):
        # الحصول على الكلان الذي ينتمي إليه العضو
        member_clan_res = self.supabase.table("clan_members").select("clan_id").eq("user_id", user_id).execute()
        if member_clan_res.data:
            clan_id = member_clan_res.data[0]["clan_id"]
            # تحديث XP الكلان (10% من XP العضو)
            clan_res = self.supabase.table("clans").select("xp").eq("id", clan_id).execute()
            if clan_res.data:
                current_clan_xp = clan_res.data[0]["xp"]
                new_clan_xp = current_clan_xp + (xp_amount * 0.1)
                self.supabase.table("clans").update({"xp": new_clan_xp}).eq("id", clan_id).execute()
                # هنا يمكن إضافة منطق لرفع مستوى الكلان بناءً على الـ XP

    # وظائف إضافية للكلانات (سيتم تطويرها لاحقاً)
    async def transfer_leadership(self, clan_id, old_leader_id, new_leader_id):
        # تحقق من الصلاحيات والوجود
        clan = self.supabase.table("clans").select("*").eq("id", clan_id).eq("leader_id", old_leader_id).execute().data
        if not clan: return False, "❌ لا تملك صلاحية نقل القيادة أو الكلان غير موجود."

        new_leader_member = self.supabase.table("clan_members").select("*").eq("clan_id", clan_id).eq("user_id", new_leader_id).execute().data
        if not new_leader_member: return False, "❌ العضو الجديد ليس جزءاً من الكلان."

        # تحديث القائد في جدول الكلانات
        self.supabase.table("clans").update({"leader_id": new_leader_id}).eq("id", clan_id).execute()
        # تحديث الأدوار في جدول الأعضاء
        self.supabase.table("clan_members").update({"role": "member"}).eq("clan_id", clan_id).eq("user_id", old_leader_id).execute()
        self.supabase.table("clan_members").update({"role": "leader"}).eq("clan_id", clan_id).eq("user_id", new_leader_id).execute()
        return True, "✅ تم نقل قيادة الكلان بنجاح."

    async def kick_member(self, clan_id, leader_id, member_to_kick_id):
        # تحقق من الصلاحيات
        clan = self.supabase.table("clans").select("*").eq("id", clan_id).eq("leader_id", leader_id).execute().data
        if not clan: return False, "❌ لا تملك صلاحية طرد الأعضاء أو الكلان غير موجود."

        # لا يمكن للقائد طرد نفسه
        if leader_id == member_to_kick_id: return False, "❌ لا يمكنك طرد نفسك من الكلان."

        # حذف العضو من الكلان
        self.supabase.table("clan_members").delete().eq("clan_id", clan_id).eq("user_id", member_to_kick_id).execute()
        return True, "✅ تم طرد العضو بنجاح."

    async def update_clan_description(self, clan_id, leader_id, new_description):
        # تحقق من الصلاحيات
        clan = self.supabase.table("clans").select("*").eq("id", clan_id).eq("leader_id", leader_id).execute().data
        if not clan: return False, "❌ لا تملك صلاحية تعديل الوصف أو الكلان غير موجود."

        self.supabase.table("clans").update({"description": new_description}).eq("id", clan_id).execute()
        return True, "✅ تم تحديث وصف الكلان بنجاح."

    async def delete_clan(self, clan_id, leader_id):
        # تحقق من الصلاحيات
        clan = self.supabase.table("clans").select("*").eq("id", clan_id).eq("leader_id", leader_id).execute().data
        if not clan: return False, "❌ لا تملك صلاحية حذف الكلان أو الكلان غير موجود."

        # حذف جميع أعضاء الكلان أولاً
        self.supabase.table("clan_members").delete().eq("clan_id", clan_id).execute()
        # ثم حذف الكلان نفسه
        self.supabase.table("clans").delete().eq("id", clan_id).execute()
        return True, "✅ تم حذف الكلان بنجاح."

    async def promote_member(self, clan_id, leader_id, member_id, new_role):
        # تحقق من الصلاحيات
        clan = self.supabase.table("clans").select("*").eq("id", clan_id).eq("leader_id", leader_id).execute().data
        if not clan: return False, "❌ لا تملك صلاحية تعديل الرتب أو الكلان غير موجود."

        # تحقق من أن العضو موجود في الكلان
        member = self.supabase.table("clan_members").select("*").eq("clan_id", clan_id).eq("user_id", member_id).execute().data
        if not member: return False, "❌ العضو ليس جزءاً من الكلان."

        # تحديث دور العضو
        self.supabase.table("clan_members").update({"role": new_role}).eq("clan_id", clan_id).eq("user_id", member_id).execute()
        return True, f"✅ تم ترقية العضو إلى {new_role} بنجاح."

    async def demote_member(self, clan_id, leader_id, member_id, new_role):
        # تحقق من الصلاحيات
        clan = self.supabase.table("clans").select("*").eq("id", clan_id).eq("leader_id", leader_id).execute().data
        if not clan: return False, "❌ لا تملك صلاحية تعديل الرتب أو الكلان غير موجود."

        # تحقق من أن العضو موجود في الكلان
        member = self.supabase.table("clan_members").select("*").eq("clan_id", clan_id).eq("user_id", member_id).execute().data
        if not member: return False, "❌ العضو ليس جزءاً من الكلان."

        # تحديث دور العضو
        self.supabase.table("clan_members").update({"role": new_role}).eq("clan_id", clan_id).eq("user_id", member_id).execute()
        return True, f"✅ تم تخفيض رتبة العضو إلى {new_role} بنجاح."

    async def get_clan_info(self, clan_id):
        clan_res = self.supabase.table("clans").select("*").eq("id", clan_id).execute()
        return clan_res.data[0] if clan_res.data else None

    async def get_clan_level_info(self, clan_level):
        level_res = self.supabase.table("clan_levels").select("*").eq("level", clan_level).execute()
        return level_res.data[0] if level_res.data else None

    async def update_clan_level(self, clan_id, current_xp):
        clan = self.supabase.table("clans").select("level").eq("id", clan_id).execute().data[0]
        current_level = clan["level"]
        next_level_info = await self.get_clan_level_info(current_level + 1)

        if next_level_info and current_xp >= next_level_info["required_xp"]:
            new_level = current_level + 1
            self.supabase.table("clans").update({"level": new_level}).eq("id", clan_id).execute()
            return True, new_level
        return False, current_level

    async def add_clan_coins(self, clan_id, coins_amount):
        clan = self.supabase.table("clans").select("coins").eq("id", clan_id).execute().data[0]
        new_coins = clan["coins"] + coins_amount
        self.supabase.table("clans").update({"coins": new_coins}).eq("id", clan_id).execute()

    async def deduct_clan_coins(self, clan_id, coins_amount):
        clan = self.supabase.table("clans").select("coins").eq("id", clan_id).execute().data[0]
        if clan["coins"] < coins_amount: return False
        new_coins = clan["coins"] - coins_amount
        self.supabase.table("clans").update({"coins": new_coins}).eq("id", clan_id).execute()
        return True

    async def get_clan_leaderboard_weekly(self, group_id, limit=10):
        # هذه الدالة تتطلب جدولاً لتتبع XP الأسبوعي للكلانات
        # أو حسابها بناءً على المعاملات الأسبوعية
        # حالياً، سنعيد قائمة المتصدرين العامة
        return await self.get_top_clans(limit)

    async def get_clan_leaderboard_monthly(self, group_id, limit=10):
        # هذه الدالة تتطلب جدولاً لتتبع XP الشهري للكلانات
        # أو حسابها بناءً على المعاملات الشهرية
        # حالياً، سنعيد قائمة المتصدرين العامة
        return await self.get_top_clans(limit)

    async def get_clan_wars(self, clan_id=None):
        # تتطلب جدول clan_wars
        if clan_id:
            return self.supabase.table("clan_wars").select("*").or_(f"clan1_id.eq.{clan_id}", f"clan2_id.eq.{clan_id}").execute().data
        return self.supabase.table("clan_wars").select("*").execute().data

    async def start_clan_war(self, clan1_id, clan2_id, war_type, duration_hours):
        # تتطلب جدول clan_wars
        war_data = {
            "clan1_id": clan1_id,
            "clan2_id": clan2_id,
            "war_type": war_type,
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=duration_hours)).isoformat(),
            "status": "active",
            "clan1_score": 0,
            "clan2_score": 0
        }
        return self.supabase.table("clan_wars").insert(war_data).execute().data

    async def update_clan_war_score(self, war_id, clan_id, score_increase):
        # تتطلب جدول clan_wars
        war = self.supabase.table("clan_wars").select("*").eq("id", war_id).execute().data[0]
        if war["clan1_id"] == clan_id:
            new_score = war["clan1_score"] + score_increase
            self.supabase.table("clan_wars").update({"clan1_score": new_score}).eq("id", war_id).execute()
        elif war["clan2_id"] == clan_id:
            new_score = war["clan2_score"] + score_increase
            self.supabase.table("clan_wars").update({"clan2_score": new_score}).eq("id", war_id).execute()

    async def end_clan_war(self, war_id):
        # تتطلب جدول clan_wars
        war = self.supabase.table("clan_wars").select("*").eq("id", war_id).execute().data[0]
        winner_id = None
        if war["clan1_score"] > war["clan2_score"]:
            winner_id = war["clan1_id"]
        elif war["clan2_score"] > war["clan1_score"]:
            winner_id = war["clan2_id"]

        self.supabase.table("clan_wars").update({"status": "ended", "winner_clan_id": winner_id}).eq("id", war_id).execute()
        return winner_id

    async def get_clan_challenges(self, clan_id=None):
        # تتطلب جدول clan_challenges
        if clan_id:
            return self.supabase.table("clan_challenges").select("*").eq("clan_id", clan_id).execute().data
        return self.supabase.table("clan_challenges").select("*").execute().data

    async def create_clan_challenge(self, clan_id, challenge_name, description, reward_xp, reward_coins, required_progress):
        # تتطلب جدول clan_challenges
        challenge_data = {
            "clan_id": clan_id,
            "challenge_name": challenge_name,
            "description": description,
            "reward_xp": reward_xp,
            "reward_coins": reward_coins,
            "required_progress": required_progress,
            "current_progress": 0,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        return self.supabase.table("clan_challenges").insert(challenge_data).execute().data

    async def update_clan_challenge_progress(self, challenge_id, progress_increase):
        # تتطلب جدول clan_challenges
        challenge = self.supabase.table("clan_challenges").select("*").eq("id", challenge_id).execute().data[0]
        new_progress = challenge["current_progress"] + progress_increase
        is_completed = new_progress >= challenge["required_progress"]
        status = "completed" if is_completed else "active"
        self.supabase.table("clan_challenges").update({"current_progress": new_progress, "status": status}).eq("id", challenge_id).execute()
        return is_completed

    async def award_clan_challenge_reward(self, challenge_id):
        # تتطلب جدول clan_challenges
        challenge = self.supabase.table("clan_challenges").select("*").eq("id", challenge_id).execute().data[0]
        clan_id = challenge["clan_id"]
        reward_xp = challenge["reward_xp"]
        reward_coins = challenge["reward_coins"]

        # إضافة المكافآت للكلان
        await self.add_clan_xp(clan_id, reward_xp)
        await self.add_clan_coins(clan_id, reward_coins)

        self.supabase.table("clan_challenges").update({"status": "awarded"}).eq("id", challenge_id).execute()

    async def add_clan_xp(self, clan_id, xp_amount):
        clan = self.supabase.table("clans").select("xp").eq("id", clan_id).execute().data[0]
        new_xp = clan["xp"] + xp_amount
        self.supabase.table("clans").update({"xp": new_xp}).eq("id", clan_id).execute()
        await self.update_clan_level(clan_id, new_xp)







# ==============================
# 🏆 أوامر الكلانات المتقدمة
# ==============================

# نقل قيادة الكلان: /ctransfer @username
@app.on_message(filters.command("ctransfer") & filters.group)
async def clan_transfer_cmd(client, message):
    user_id = message.from_user.id
    
    # التحقق من أن الرسالة رد على رسالة أخرى
    if not message.reply_to_message:
        await message.reply_text("❌ يجب الرد على رسالة العضو الذي تريد نقل القيادة إليه!")
        return
    
    new_leader_id = message.reply_to_message.from_user.id
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    ok, msg = await clan_manager.transfer_leadership(clan["id"], user_id, new_leader_id)
    await message.reply_text(msg)

# طرد عضو من الكلان: /ckick @username
@app.on_message(filters.command("ckick") & filters.group)
async def clan_kick_cmd(client, message):
    user_id = message.from_user.id
    
    # التحقق من أن الرسالة رد على رسالة أخرى
    if not message.reply_to_message:
        await message.reply_text("❌ يجب الرد على رسالة العضو الذي تريد طرده!")
        return
    
    member_to_kick_id = message.reply_to_message.from_user.id
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    ok, msg = await clan_manager.kick_member(clan["id"], user_id, member_to_kick_id)
    await message.reply_text(msg)

# ترقية عضو في الكلان: /cpromote @username رتبة
@app.on_message(filters.command("cpromote") & filters.group)
async def clan_promote_cmd(client, message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    # التحقق من أن الرسالة رد على رسالة أخرى
    if not message.reply_to_message:
        await message.reply_text("❌ يجب الرد على رسالة العضو الذي تريد ترقيته!")
        return
    
    if len(args) < 2:
        await message.reply_text("❌ استخدم: /cpromote [الرتبة الجديدة] (بالرد على رسالة العضو)")
        return
    
    member_id = message.reply_to_message.from_user.id
    new_role = args[1]
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    ok, msg = await clan_manager.promote_member(clan["id"], user_id, member_id, new_role)
    await message.reply_text(msg)

# تخفيض رتبة عضو في الكلان: /cdemote @username رتبة
@app.on_message(filters.command("cdemote") & filters.group)
async def clan_demote_cmd(client, message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    # التحقق من أن الرسالة رد على رسالة أخرى
    if not message.reply_to_message:
        await message.reply_text("❌ يجب الرد على رسالة العضو الذي تريد تخفيض رتبته!")
        return
    
    if len(args) < 2:
        await message.reply_text("❌ استخدم: /cdemote [الرتبة الجديدة] (بالرد على رسالة العضو)")
        return
    
    member_id = message.reply_to_message.from_user.id
    new_role = args[1]
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    ok, msg = await clan_manager.demote_member(clan["id"], user_id, member_id, new_role)
    await message.reply_text(msg)

# تحديث وصف الكلان: /cdesc وصف_جديد
@app.on_message(filters.command("cdesc") & filters.group)
async def clan_desc_cmd(client, message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply_text("❌ استخدم: /cdesc [الوصف الجديد]")
        return
    
    new_description = args[1]
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    ok, msg = await clan_manager.update_clan_description(clan["id"], user_id, new_description)
    await message.reply_text(msg)

# حذف الكلان: /cdelete
@app.on_message(filters.command("cdelete") & filters.group)
async def clan_delete_cmd(client, message):
    user_id = message.from_user.id
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    # طلب تأكيد
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ نعم، احذف الكلان", callback_data=f"confirm_delete_clan_{clan['id']}_{user_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_delete_clan_{user_id}")
        ]
    ])
    
    await message.reply_text(
        f"⚠️ هل أنت متأكد من حذف كلان {clan['name']} [{clan['tag']}]؟\n"
        "هذا الإجراء لا يمكن التراجع عنه!",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex(r"confirm_delete_clan_(\d+)_(\d+)"))
async def confirm_delete_clan_cb(client, callback_query):
    try:
        clan_id = int(callback_query.data.split("_")[3])
        owner_id = int(callback_query.data.split("_")[4])
        user_id = callback_query.from_user.id
        
        if user_id != owner_id:
            await callback_query.answer("❌ هذا الأمر ليس لك!", show_alert=True)
            return
        
        ok, msg = await clan_manager.delete_clan(clan_id, user_id)
        await callback_query.edit_message_text(msg)
    except Exception as e:
        print(f"خطأ في confirm_delete_clan_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

@app.on_callback_query(filters.regex(r"cancel_delete_clan_(\d+)"))
async def cancel_delete_clan_cb(client, callback_query):
    try:
        owner_id = int(callback_query.data.split("_")[3])
        user_id = callback_query.from_user.id
        
        if user_id != owner_id:
            await callback_query.answer("❌ هذا الأمر ليس لك!", show_alert=True)
            return
        
        await callback_query.edit_message_text("✅ تم إلغاء حذف الكلان.")
    except Exception as e:
        print(f"خطأ في cancel_delete_clan_cb: {e}")
        await callback_query.answer("حدث خطأ، حاول مرة أخرى.", show_alert=True)

# ==============================
# 🏆 حروب الكلانات
# ==============================

# بدء حرب كلان: /cwar ID_الكلان_المنافس نوع_الحرب مدة_بالساعات
@app.on_message(filters.command("cwar") & filters.group)
async def clan_war_cmd(client, message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 4:
        await message.reply_text("❌ استخدم: /cwar [ID الكلان المنافس] [نوع الحرب] [المدة بالساعات]")
        return
    
    try:
        opponent_clan_id = int(args[1])
        war_type = args[2]
        duration_hours = int(args[3])
    except ValueError:
        await message.reply_text("❌ تأكد من صحة البيانات المدخلة!")
        return
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    # التحقق من أن المستخدم هو قائد الكلان
    if clan["leader_id"] != user_id:
        await message.reply_text("❌ فقط قائد الكلان يمكنه بدء الحروب!")
        return
    
    # التحقق من وجود الكلان المنافس
    opponent_clan = await clan_manager.get_clan_info(opponent_clan_id)
    if not opponent_clan:
        await message.reply_text("❌ الكلان المنافس غير موجود!")
        return
    
    # بدء الحرب
    try:
        war_data = await clan_manager.start_clan_war(clan["id"], opponent_clan_id, war_type, duration_hours)
        await message.reply_text(
            f"⚔️ بدأت حرب الكلانات!\n\n"
            f"🏷️ {clan['name']} [{clan['tag']}] ضد {opponent_clan['name']} [{opponent_clan['tag']}]\n"
            f"🎯 نوع الحرب: {war_type}\n"
            f"⏰ المدة: {duration_hours} ساعة\n"
            f"🆔 ID الحرب: {war_data[0]['id']}"
        )
    except Exception as e:
        print(f"خطأ في بدء حرب الكلان: {e}")
        await message.reply_text("❌ حدث خطأ في بدء الحرب!")

# عرض حروب الكلان: /cwars
@app.on_message(filters.command("cwars") & filters.group)
async def clan_wars_cmd(client, message):
    user_id = message.from_user.id
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    # الحصول على حروب الكلان
    wars = await clan_manager.get_clan_wars(clan["id"])
    
    if not wars:
        await message.reply_text("📊 لا توجد حروب للكلان حالياً!")
        return
    
    wars_text = f"⚔️ حروب كلان {clan['name']}:\n\n"
    
    for war in wars:
        status_emoji = "🔥" if war["status"] == "active" else "✅" if war["status"] == "ended" else "❌"
        wars_text += f"{status_emoji} **حرب #{war['id']}**\n"
        wars_text += f"🎯 النوع: {war['war_type']}\n"
        wars_text += f"📊 النتيجة: {war['clan1_score']} - {war['clan2_score']}\n"
        wars_text += f"📅 بدأت: {war['start_time'][:10]}\n\n"
    
    await message.reply_text(wars_text)

# ==============================
# 🎯 تحديات الكلانات
# ==============================

# عرض تحديات الكلان: /cchallenges
@app.on_message(filters.command("cchallenges") & filters.group)
async def clan_challenges_cmd(client, message):
    user_id = message.from_user.id
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    # الحصول على تحديات الكلان
    challenges = await clan_manager.get_clan_challenges(clan["id"])
    
    if not challenges:
        await message.reply_text("📋 لا توجد تحديات للكلان حالياً!")
        return
    
    challenges_text = f"🎯 تحديات كلان {clan['name']}:\n\n"
    
    for challenge in challenges:
        status_emoji = "⏳" if challenge["status"] == "active" else "✅" if challenge["status"] == "completed" else "🎁"
        progress_percentage = (challenge.get("current_progress", 0) * 100) // challenge["required_progress"] if challenge["required_progress"] > 0 else 0
        progress_bar = "▰" * (progress_percentage // 10) + "▱" * (10 - (progress_percentage // 10))
        
        challenges_text += f"{status_emoji} **{challenge['challenge_name']}**\n"
        challenges_text += f"📝 {challenge['description']}\n"
        challenges_text += f"📊 التقدم: {challenge.get('current_progress', 0)}/{challenge['required_progress']} {progress_bar}\n"
        challenges_text += f"🎁 المكافأة: {challenge['reward_xp']} XP + {challenge['reward_coins']} كوينز\n\n"
    
    await message.reply_text(challenges_text)

# ==============================
# 📊 إحصائيات الكلانات المتقدمة
# ==============================

# إحصائيات مفصلة للكلان: /cstats
@app.on_message(filters.command("cstats") & filters.group)
async def clan_stats_cmd(client, message):
    user_id = message.from_user.id
    
    # الحصول على كلان المستخدم
    clan = await clan_manager.get_user_clan(user_id)
    if not clan:
        await message.reply_text("❌ أنت لست في أي كلان!")
        return
    
    # الحصول على أعضاء الكلان
    members = await clan_manager.get_clan_members(clan["id"])
    
    # الحصول على حروب الكلان
    wars = await clan_manager.get_clan_wars(clan["id"])
    active_wars = [w for w in wars if w["status"] == "active"]
    completed_wars = [w for w in wars if w["status"] == "ended"]
    
    # الحصول على تحديات الكلان
    challenges = await clan_manager.get_clan_challenges(clan["id"])
    completed_challenges = [c for c in challenges if c["status"] == "completed"]
    
    stats_text = f"📊 **إحصائيات كلان {clan['name']} [{clan['tag']}]**\n\n"
    stats_text += f"🏆 **المستوى:** {clan['level']}\n"
    stats_text += f"🧙‍♂️ **XP:** {clan['xp']:,}\n"
    stats_text += f"💰 **كوينز:** {clan['coins']:,}\n"
    stats_text += f"👥 **عدد الأعضاء:** {len(members)}\n"
    stats_text += f"⚔️ **الحروب النشطة:** {len(active_wars)}\n"
    stats_text += f"🏅 **الحروب المكتملة:** {len(completed_wars)}\n"
    stats_text += f"🎯 **التحديات المكتملة:** {len(completed_challenges)}\n"
    stats_text += f"📅 **تاريخ الإنشاء:** {clan['created_at'][:10]}\n"
    
    if clan.get("description"):
        stats_text += f"\n📝 **الوصف:** {clan['description']}"
    
    await message.reply_text(stats_text)

# لوحة متصدرين الكلانات الأسبوعية: /ctopweek
@app.on_message(filters.command("ctopweek") & filters.group)
async def clan_top_weekly_cmd(client, message):
    group_id = message.chat.id
    
    # الحصول على لوحة المتصدرين الأسبوعية
    top_clans = await clan_manager.get_clan_leaderboard_weekly(group_id, 10)
    
    if not top_clans:
        await message.reply_text("📊 لا توجد بيانات كافية لعرض قائمة المتصدرين الأسبوعية!")
        return
    
    leaderboard_text = "🏆 **قائمة متصدري الكلانات (أسبوعياً):**\n\n"
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, clan in enumerate(top_clans):
        medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
        leaderboard_text += f"{medal} **{clan['name']} [{clan['tag']}]**\n"
        leaderboard_text += f"🏆 المستوى: {clan['level']} | 🧙‍♂️ XP: {clan['xp']:,} | 💰 كوينز: {clan['coins']:,}\n\n"
    
    await message.reply_text(leaderboard_text)

# لوحة متصدرين الكلانات الشهرية: /ctopmonth
@app.on_message(filters.command("ctopmonth") & filters.group)
async def clan_top_monthly_cmd(client, message):
    group_id = message.chat.id
    
    # الحصول على لوحة المتصدرين الشهرية
    top_clans = await clan_manager.get_clan_leaderboard_monthly(group_id, 10)
    
    if not top_clans:
        await message.reply_text("📊 لا توجد بيانات كافية لعرض قائمة المتصدرين الشهرية!")
        return
    
    leaderboard_text = "🏆 **قائمة متصدري الكلانات (شهرياً):**\n\n"
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, clan in enumerate(top_clans):
        medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
        leaderboard_text += f"{medal} **{clan['name']} [{clan['tag']}]**\n"
        leaderboard_text += f"🏆 المستوى: {clan['level']} | 🧙‍♂️ XP: {clan['xp']:,} | 💰 كوينز: {clan['coins']:,}\n\n"
    
    await message.reply_text(leaderboard_text)



# ==============================
# 🎁 نظام دعوة الأعضاء المحسن
# ==============================

# مكافآت دعوة الأعضاء
INVITATION_REWARD_XP = 500
INVITATION_REWARD_COINS = 300

async def handle_new_member_invitation(inviter_id, invited_id, group_id, inviter_username):
    """معالجة دعوة عضو جديد وإعطاء مكافآت"""
    try:
        # التأكد من وجود المدعو في قاعدة البيانات
        await get_or_create_user(inviter_id, group_id, inviter_username)
        
        # تسجيل الدعوة
        supabase.table("invitations").insert({
            "inviter_id": inviter_id,
            "invited_id": invited_id,
            "group_id": group_id,
            "created_at": datetime.now().isoformat()
        }).execute()
        
        # إعطاء مكافأة للمدعو
        await update_user_xp(inviter_id, group_id, inviter_username, INVITATION_REWARD_XP, INVITATION_REWARD_COINS)
        
        # تحديث تقدم المهام
        await update_task_progress(inviter_id, group_id, "invite_members", 1)
        
        # تسجيل المعاملة
        await log_transaction(inviter_id, group_id, "invitation_reward", INVITATION_REWARD_XP, f"دعوة عضو جديد: +{INVITATION_REWARD_XP} XP")
        
        return f"🎉 **تهانينا** <a href=\"tg://user?id={inviter_id}\">{inviter_username}</a>!\n\n🎁 **مكافأة دعوة عضو جديد:**\n💰 **+{INVITATION_REWARD_COINS} كوينز**\n🧙‍♂️ **+{INVITATION_REWARD_XP} XP**\n\n✨ **استمر في دعوة الأصدقاء لتحصل على المزيد من المكافآت!**"
    except Exception as e:
        print(f"خطأ في handle_new_member_invitation: {e}")
        return None

# ==============================
# 🎁 تحسين نظام المكافآت اليومية
# ==============================

# مكافآت يومية محسنة بناءً على streak
DAILY_REWARDS_ENHANCED = {
    1: {"xp": 400, "coins": 200},      # اليوم الأول
    2: {"xp": 450, "coins": 225},      # اليوم الثاني
    3: {"xp": 500, "coins": 250},      # اليوم الثالث
    4: {"xp": 550, "coins": 275},      # اليوم الرابع
    5: {"xp": 600, "coins": 300},      # اليوم الخامس
    6: {"xp": 650, "coins": 325},      # اليوم السادس
    7: {"xp": 800, "coins": 400},      # اليوم السابع (مكافأة أسبوعية)
    14: {"xp": 1200, "coins": 600},    # أسبوعين
    30: {"xp": 2000, "coins": 1000},   # شهر كامل
}

async def check_and_claim_daily_reward_enhanced(user_id, group_id, username):
    """فحص وطلب المكافأة اليومية المحسنة"""
    try:
        now = datetime.utcnow()

        # التحقق من آخر مرة طلب فيها المستخدم المكافأة
        res = supabase.table("daily_rewards").select("*").eq("user_id", user_id).eq("group_id", group_id).execute()
        daily_record = res.data[0] if res.data else None

        if daily_record:
            last_claimed = datetime.fromisoformat(daily_record["last_claimed"].replace("Z", "+00:00"))
            time_diff = now - last_claimed

            # التحقق إذا مر 24 ساعة منذ آخر مطالبة
            if time_diff < timedelta(hours=24):
                remaining_time = timedelta(hours=24) - time_diff
                hours = int(remaining_time.seconds // 3600)
                minutes = int((remaining_time.seconds % 3600) // 60)
                return False, f"⏰ يجب انتظار {hours} ساعة و {minutes} دقيقة قبل طلب المكافأة التالية!"

            # تحديث streak count
            if time_diff <= timedelta(hours=48):  # إذا كان أقل من 48 ساعة (يوم متتالي)
                new_streak = daily_record["streak_count"] + 1
            else:  # إذا انقطع التسلسل
                new_streak = 1

            new_total_claims = daily_record["total_claims"] + 1

            # تحديث السجل
            supabase.table("daily_rewards").update({
                "last_claimed": now.isoformat(),
                "streak_count": new_streak,
                "total_claims": new_total_claims
            }).eq("user_id", user_id).eq("group_id", group_id).execute()
        else:
            # إنشاء سجل جديد للمستخدم
            new_streak = 1
            new_total_claims = 1
            supabase.table("daily_rewards").insert({
                "user_id": user_id,
                "group_id": group_id,
                "last_claimed": now.isoformat(),
                "streak_count": new_streak,
                "total_claims": new_total_claims
            }).execute()

        # تحديد المكافأة بناءً على streak
        if new_streak in DAILY_REWARDS_ENHANCED:
            reward = DAILY_REWARDS_ENHANCED[new_streak]
        elif new_streak >= 30:
            reward = DAILY_REWARDS_ENHANCED[30]  # مكافأة شهرية للأيام 30+
        elif new_streak >= 14:
            reward = DAILY_REWARDS_ENHANCED[14]  # مكافأة أسبوعين للأيام 14-29
        elif new_streak >= 7:
            reward = DAILY_REWARDS_ENHANCED[7]   # مكافأة أسبوعية للأيام 7-13
        else:
            # مكافأة تدريجية للأيام 1-6
            base_reward = DAILY_REWARDS_ENHANCED[min(new_streak, 6)]
            reward = base_reward

        reward_xp = reward["xp"]
        reward_coins = reward["coins"]

        # إعطاء المكافأة للمستخدم
        await update_user_xp(user_id, group_id, username, reward_xp, reward_coins)

        # تحديث تقدم المهام
        await update_task_progress(user_id, group_id, "daily_login", 1)

        # تسجيل المعاملة
        await log_transaction(user_id, group_id, "daily_reward", reward_xp, f"مكافأة يومية محسنة: streak {new_streak}")

        # رسالة مخصصة بناءً على streak
        streak_message = ""
        if new_streak == 7:
            streak_message = "\n🎊 **مكافأة أسبوعية خاصة!** 🎊"
        elif new_streak == 14:
            streak_message = "\n🔥 **مكافأة أسبوعين رائعة!** 🔥"
        elif new_streak == 30:
            streak_message = "\n👑 **مكافأة شهرية أسطورية!** 👑"
        elif new_streak >= 30:
            streak_message = f"\n🌟 **أنت أسطورة! {new_streak} يوم متتالي!** 🌟"

        return True, f"🎁 <a href=\"tg://user?id={user_id}\">{username}</a> **حصل على المكافأة اليومية المحسنة!**\n\n💰 **+{reward_coins} كوينز**\n🧙‍♂️ **+{reward_xp} XP**\n🔥 **Streak**: **{new_streak}** **يوم**{streak_message}"
    except Exception as e:
        print(f"خطأ في check_and_claim_daily_reward_enhanced: {e}")
        return False, "حدث خطأ في النظام!"

# ==============================
# 💖 تحسين نظام الشكر
# ==============================

# مكافآت شكر محسنة بناءً على عدد مرات الشكر المستلمة
THANK_YOU_REWARDS_ENHANCED = {
    "base": {"xp": 200, "coins": 150},
    "frequent": {"xp": 250, "coins": 200},  # للأشخاص الذين تم شكرهم أكثر من 10 مرات
    "popular": {"xp": 300, "coins": 250},   # للأشخاص الذين تم شكرهم أكثر من 50 مرة
    "legend": {"xp": 400, "coins": 350},    # للأشخاص الذين تم شكرهم أكثر من 100 مرة
}

async def give_thank_you_reward_enhanced(thanked_user_id, group_id, thanked_username):
    """إعطاء مكافأة شكر محسنة للمستخدم المشكور"""
    try:
        # التأكد من وجود المستخدم المشكور في قاعدة البيانات
        await get_or_create_user(thanked_user_id, group_id, thanked_username)

        # الحصول على عدد مرات الشكر المستلمة
        res = supabase.table("thank_you_cooldown").select("total_thanks_received").eq("user_id", thanked_user_id).eq("group_id", group_id).execute()
        current_thanks = res.data[0]["total_thanks_received"] if res.data else 0

        # تحديد نوع المكافأة بناءً على عدد مرات الشكر
        if current_thanks >= 100:
            reward_type = "legend"
            tier_name = "أسطوري"
            tier_emoji = "👑"
        elif current_thanks >= 50:
            reward_type = "popular"
            tier_name = "شعبي"
            tier_emoji = "🌟"
        elif current_thanks >= 10:
            reward_type = "frequent"
            tier_name = "متكرر"
            tier_emoji = "🔥"
        else:
            reward_type = "base"
            tier_name = "عادي"
            tier_emoji = "💖"

        reward = THANK_YOU_REWARDS_ENHANCED[reward_type]
        reward_xp = reward["xp"]
        reward_coins = reward["coins"]

        # إعطاء المكافأة
        await update_user_xp(thanked_user_id, group_id, thanked_username, reward_xp, reward_coins)

        # تحديث عداد الشكر المستلم
        if res.data:
            new_total_received = current_thanks + 1
            supabase.table("thank_you_cooldown").update({
                "total_thanks_received": new_total_received
            }).eq("user_id", thanked_user_id).eq("group_id", group_id).execute()
        else:
            supabase.table("thank_you_cooldown").insert({
                "user_id": thanked_user_id,
                "group_id": group_id,
                "last_used": datetime.utcnow().isoformat(),
                "total_thanks_given": 0,
                "total_thanks_received": 1
            }).execute()

        # تسجيل المعاملة
        await log_transaction(thanked_user_id, group_id, "thank_reward", reward_xp, f"مكافأة شكر محسنة ({tier_name})")

        return f"{tier_emoji} **تم شكر** <a href=\"tg://user?id={thanked_user_id}\">{thanked_username}</a> **بنجاح!**\n\n🎁 **مكافأة {tier_name}:**\n💰 **+{reward_coins} كوينز**\n🧙‍♂️ **+{reward_xp} XP**\n📊 **إجمالي مرات الشكر:** {current_thanks + 1}"
    except Exception as e:
        print(f"خطأ في give_thank_you_reward_enhanced: {e}")
        return "حدث خطأ في إرسال المكافأة!"

# ==============================
# 📊 لوحات المتصدرين المحسنة
# ==============================

async def get_weekly_leaderboard(group_id, limit=10):
    """الحصول على قائمة المتصدرين الأسبوعية"""
    try:
        # حساب بداية الأسبوع الحالي
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        # محاولة الحصول من جدول weekly_leaderboard أولاً
        result = supabase.table("weekly_leaderboard").select("*, group_members(username)").eq("group_id", group_id).eq("week_start_date", week_start.isoformat()).order("xp_earned", desc=True).limit(limit).execute()
        
        if result.data:
            return result.data
        else:
            # إذا لم توجد بيانات أسبوعية، استخدم البيانات العامة
            return await get_leaderboard(group_id, limit, "xp")
    except Exception as e:
        print(f"خطأ في get_weekly_leaderboard: {e}")
        return await get_leaderboard(group_id, limit, "xp")

async def get_monthly_leaderboard(group_id, limit=10):
    """الحصول على قائمة المتصدرين الشهرية"""
    try:
        # حساب بداية الشهر الحالي
        today = date.today()
        month_start = today.replace(day=1)
        
        # محاولة الحصول من جدول monthly_leaderboard أولاً
        result = supabase.table("monthly_leaderboard").select("*, group_members(username)").eq("group_id", group_id).eq("month_start_date", month_start.isoformat()).order("xp_earned", desc=True).limit(limit).execute()
        
        if result.data:
            return result.data
        else:
            # إذا لم توجد بيانات شهرية، استخدم البيانات العامة
            return await get_leaderboard(group_id, limit, "xp")
    except Exception as e:
        print(f"خطأ في get_monthly_leaderboard: {e}")
        return await get_leaderboard(group_id, limit, "xp")

async def update_leaderboard_data(user_id, group_id, xp_gained):
    """تحديث بيانات لوحات المتصدرين الأسبوعية والشهرية"""
    try:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # تحديث البيانات الأسبوعية
        weekly_data = supabase.table("weekly_leaderboard").select("*").eq("user_id", user_id).eq("group_id", group_id).eq("week_start_date", week_start.isoformat()).execute()
        
        if weekly_data.data:
            current_weekly_xp = weekly_data.data[0]["xp_earned"]
            supabase.table("weekly_leaderboard").update({
                "xp_earned": current_weekly_xp + xp_gained
            }).eq("user_id", user_id).eq("group_id", group_id).eq("week_start_date", week_start.isoformat()).execute()
        else:
            supabase.table("weekly_leaderboard").insert({
                "user_id": user_id,
                "group_id": group_id,
                "xp_earned": xp_gained,
                "week_start_date": week_start.isoformat()
            }).execute()
        
        # تحديث البيانات الشهرية
        monthly_data = supabase.table("monthly_leaderboard").select("*").eq("user_id", user_id).eq("group_id", group_id).eq("month_start_date", month_start.isoformat()).execute()
        
        if monthly_data.data:
            current_monthly_xp = monthly_data.data[0]["xp_earned"]
            supabase.table("monthly_leaderboard").update({
                "xp_earned": current_monthly_xp + xp_gained
            }).eq("user_id", user_id).eq("group_id", group_id).eq("month_start_date", month_start.isoformat()).execute()
        else:
            supabase.table("monthly_leaderboard").insert({
                "user_id": user_id,
                "group_id": group_id,
                "xp_earned": xp_gained,
                "month_start_date": month_start.isoformat()
            }).execute()
            
    except Exception as e:
        print(f"خطأ في update_leaderboard_data: {e}")

# ==============================
# 🎯 عرض تقدم XP بشكل مرئي جذاب
# ==============================

def create_xp_progress_bar(current_xp, next_level_xp, length=20):
    """إنشاء شريط تقدم XP مرئي"""
    if next_level_xp <= current_xp:
        return "▰" * length + " 100%"
    
    progress = current_xp / next_level_xp
    filled_length = int(length * progress)
    bar = "▰" * filled_length + "▱" * (length - filled_length)
    percentage = int(progress * 100)
    
    return f"{bar} {percentage}%"

def get_level_emoji(level):
    """الحصول على emoji مناسب للمستوى"""
    if level >= 50:
        return "👑"
    elif level >= 40:
        return "💎"
    elif level >= 30:
        return "🏆"
    elif level >= 20:
        return "🥇"
    elif level >= 10:
        return "🥈"
    elif level >= 5:
        return "🥉"
    else:
        return "⭐"

async def get_enhanced_user_stats(user_id, group_id):
    """الحصول على إحصائيات المستخدم المحسنة"""
    try:
        # الحصول على الإحصائيات الأساسية
        basic_stats = await get_user_stats(user_id, group_id)
        
        # الحصول على الترتيب
        rank = await get_user_rank(user_id, group_id)
        
        # الحصول على عدد الشارات
        badges = await get_user_badges(user_id, group_id)
        badges_count = len(badges)
        
        # الحصول على إحصائيات الشكر
        thanks_data = supabase.table("thank_you_cooldown").select("total_thanks_given, total_thanks_received").eq("user_id", user_id).eq("group_id", group_id).execute()
        thanks_given = thanks_data.data[0]["total_thanks_given"] if thanks_data.data else 0
        thanks_received = thanks_data.data[0]["total_thanks_received"] if thanks_data.data else 0
        
        # الحصول على streak المكافآت اليومية
        daily_data = supabase.table("daily_rewards").select("streak_count, total_claims").eq("user_id", user_id).eq("group_id", group_id).execute()
        daily_streak = daily_data.data[0]["streak_count"] if daily_data.data else 0
        total_daily_claims = daily_data.data[0]["total_claims"] if daily_data.data else 0
        
        # إنشاء شريط التقدم
        progress_bar = create_xp_progress_bar(basic_stats["xp"], basic_stats["next_xp"])
        level_emoji = get_level_emoji(basic_stats["level"])
        
        return {
            **basic_stats,
            "rank": rank,
            "badges_count": badges_count,
            "thanks_given": thanks_given,
            "thanks_received": thanks_received,
            "daily_streak": daily_streak,
            "total_daily_claims": total_daily_claims,
            "progress_bar": progress_bar,
            "level_emoji": level_emoji
        }
    except Exception as e:
        print(f"خطأ في get_enhanced_user_stats: {e}")
        return await get_user_stats(user_id, group_id)

def enhanced_xp_msg(stats, user_id, username):
    """رسالة XP محسنة مع عرض مرئي جذاب"""
    return (
        f"📊 **ملفك الشخصي المتكامل** 📊\n\n"
        f"👤 **الاسم**: <a href=\"tg://user?id={user_id}\">{username}</a>\n"
        f"{stats['level_emoji']} **المستوى**: **{stats['level']}** - **{stats['level_name']}**\n"
        f"🧙‍♂️ **XP**: **{stats['xp']:,}**/**{stats['next_xp']:,}**\n"
        f"📊 **التقدم**: {stats['progress_bar']}\n"
        f"💰 **الكوينز**: **{stats['coins']:,}**\n"
        f"🏆 **الترتيب**: **#{stats['rank']}** في المجموعة\n"
        f"🏅 **الشارات**: **{stats['badges_count']}** شارة\n"
        f"💖 **الشكر**: أعطى **{stats['thanks_given']}** | استلم **{stats['thanks_received']}**\n"
        f"🔥 **Streak يومي**: **{stats['daily_streak']}** يوم\n"
        f"🎁 **إجمالي المكافآت**: **{stats['total_daily_claims']}** مكافأة\n\n"
        f"✨ **استمر في التفاعل لتحصل على المزيد من المكافآت!**"
    )


# ==============================
# 📊 أوامر لوحات المتصدرين المحسنة
# ==============================

# لوحة المتصدرين الأسبوعية: /topweek
@app.on_message(filters.command("topweek") & filters.group)
async def top_weekly_cmd(client, message):
    try:
        group_id = message.chat.id
        
        # الحصول على لوحة المتصدرين الأسبوعية
        top_users = await get_weekly_leaderboard(group_id, 10)
        
        if not top_users:
            await message.reply_text("📊 لا توجد بيانات كافية لعرض قائمة المتصدرين الأسبوعية!")
            return
        
        leaderboard_text = "🏆 **قائمة المتصدرين الأسبوعية:**\n\n"
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, user in enumerate(top_users):
            medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
            username = user.get("username", "مستخدم")
            xp_earned = user.get("xp_earned", user.get("xp", 0))
            
            leaderboard_text += f"{medal} **{username}**\n"
            leaderboard_text += f"🧙‍♂️ XP هذا الأسبوع: **{xp_earned:,}**\n\n"
        
        await message.reply_text(leaderboard_text)
    except Exception as e:
        print(f"خطأ في top_weekly_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# لوحة المتصدرين الشهرية: /topmonth
@app.on_message(filters.command("topmonth") & filters.group)
async def top_monthly_cmd(client, message):
    try:
        group_id = message.chat.id
        
        # الحصول على لوحة المتصدرين الشهرية
        top_users = await get_monthly_leaderboard(group_id, 10)
        
        if not top_users:
            await message.reply_text("📊 لا توجد بيانات كافية لعرض قائمة المتصدرين الشهرية!")
            return
        
        leaderboard_text = "🏆 **قائمة المتصدرين الشهرية:**\n\n"
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, user in enumerate(top_users):
            medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
            username = user.get("username", "مستخدم")
            xp_earned = user.get("xp_earned", user.get("xp", 0))
            
            leaderboard_text += f"{medal} **{username}**\n"
            leaderboard_text += f"🧙‍♂️ XP هذا الشهر: **{xp_earned:,}**\n\n"
        
        await message.reply_text(leaderboard_text)
    except Exception as e:
        print(f"خطأ في top_monthly_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# ==============================
# 🎁 أوامر إضافية محسنة
# ==============================

# أمر عرض إحصائيات الدعوات: /invites
@app.on_message(filters.command("invites") & filters.group)
async def invites_cmd(client, message):
    try:
        user_id = message.from_user.id
        group_id = message.chat.id
        username = message.from_user.first_name
        
        # الحصول على عدد الدعوات
        invites_data = supabase.table("invitations").select("*").eq("inviter_id", user_id).eq("group_id", group_id).execute()
        invites_count = len(invites_data.data)
        
        # الحصول على الأشخاص الذين دعاهم
        invited_users = []
        for invite in invites_data.data:
            invited_user_data = supabase.table("group_members").select("username").eq("user_id", invite["invited_id"]).eq("group_id", group_id).execute()
            if invited_user_data.data:
                invited_users.append(invited_user_data.data[0]["username"])
        
        # حساب إجمالي المكافآت المكتسبة من الدعوات
        total_xp_from_invites = invites_count * INVITATION_REWARD_XP
        total_coins_from_invites = invites_count * INVITATION_REWARD_COINS
        
        invites_text = f"👥 **إحصائيات الدعوات لـ {username}:**\n\n"
        invites_text += f"📊 **عدد الدعوات:** {invites_count}\n"
        invites_text += f"🧙‍♂️ **XP مكتسب:** {total_xp_from_invites:,}\n"
        invites_text += f"💰 **كوينز مكتسبة:** {total_coins_from_invites:,}\n\n"
        
        if invited_users:
            invites_text += f"👥 **الأعضاء المدعوون:**\n"
            for i, invited_user in enumerate(invited_users[:10]):  # عرض أول 10 فقط
                invites_text += f"{i+1}. {invited_user}\n"
            
            if len(invited_users) > 10:
                invites_text += f"... و {len(invited_users) - 10} آخرين\n"
        else:
            invites_text += "🔍 **لم تقم بدعوة أي أعضاء بعد!**\n"
            invites_text += "💡 **ادع أصدقاءك واحصل على مكافآت رائعة!**"
        
        await message.reply_text(invites_text)
    except Exception as e:
        print(f"خطأ في invites_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")

# أمر عرض إحصائيات الشكر: /thanks
@app.on_message(filters.command("thanks") & filters.group)
async def thanks_stats_cmd(client, message):
    try:
        user_id = message.from_user.id
        group_id = message.chat.id
        username = message.from_user.first_name
        
        # الحصول على إحصائيات الشكر
        thanks_data = supabase.table("thank_you_cooldown").select("total_thanks_given, total_thanks_received").eq("user_id", user_id).eq("group_id", group_id).execute()
        
        if thanks_data.data:
            thanks_given = thanks_data.data[0]["total_thanks_given"]
            thanks_received = thanks_data.data[0]["total_thanks_received"]
        else:
            thanks_given = 0
            thanks_received = 0
        
        # تحديد المستوى بناءً على عدد مرات الشكر المستلمة
        if thanks_received >= 100:
            tier = "👑 أسطوري"
        elif thanks_received >= 50:
            tier = "🌟 شعبي"
        elif thanks_received >= 10:
            tier = "🔥 متكرر"
        else:
            tier = "💖 عادي"
        
        thanks_text = f"💖 **إحصائيات الشكر لـ {username}:**\n\n"
        thanks_text += f"📤 **شكر أعطيته:** {thanks_given}\n"
        thanks_text += f"📥 **شكر استلمته:** {thanks_received}\n"
        thanks_text += f"🏆 **مستواك:** {tier}\n\n"
        
        # نصائح لتحسين المستوى
        if thanks_received < 10:
            thanks_text += "💡 **نصيحة:** كن مفيداً أكثر لتحصل على المزيد من الشكر!"
        elif thanks_received < 50:
            thanks_text += "🎯 **هدفك التالي:** الوصول لـ 50 شكر لتصبح شعبياً!"
        elif thanks_received < 100:
            thanks_text += "🚀 **قريباً من الأسطورة!** فقط تحتاج لـ 100 شكر!"
        else:
            thanks_text += "👑 **أنت أسطورة حقيقية في المساعدة!**"
        
        await message.reply_text(thanks_text)
    except Exception as e:
        print(f"خطأ في thanks_stats_cmd: {e}")
        await message.reply_text("حدث خطأ، حاول مرة أخرى.")


# ==============================
# 🎮 تحديث أمر المساعدة المحسن
# ==============================

# تحديث أمر المساعدة ليشمل جميع الأوامر الجديدة
@app.on_message(filters.command("help") & filters.group)
async def help_enhanced_cmd(client, message):
    try:
        help_text = """
🤖 **دليل البوت الشامل** 🤖

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# ============================
# نظام الحماية والأمان
# ============================

class SecurityManager:
    def __init__(self, supabase):
        self.supabase = supabase
        self.rate_limits = {}
        self.spam_detection = {}
        self.banned_users = set()
        
    def check_rate_limit(self, user_id, action, limit=5, window=60):
        """فحص حد المعدل للمستخدم"""
        current_time = datetime.now()
        key = f"{user_id}_{action}"
        
        if key not in self.rate_limits:
            self.rate_limits[key] = []
        
        # إزالة الطلبات القديمة
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key]
            if (current_time - timestamp).seconds < window
        ]
        
        # فحص الحد
        if len(self.rate_limits[key]) >= limit:
            return False
        
        # إضافة الطلب الحالي
        self.rate_limits[key].append(current_time)
        return True
    
    def detect_spam(self, user_id, message_text):
        """كشف الرسائل المكررة والسبام"""
        current_time = datetime.now()
        
        if user_id not in self.spam_detection:
            self.spam_detection[user_id] = []
        
        # إزالة الرسائل القديمة (آخر 5 دقائق)
        self.spam_detection[user_id] = [
            (timestamp, text) for timestamp, text in self.spam_detection[user_id]
            if (current_time - timestamp).seconds < 300
        ]
        
        # فحص الرسائل المتشابهة
        similar_count = sum(
            1 for _, text in self.spam_detection[user_id]
            if text.lower() == message_text.lower()
        )
        
        if similar_count >= 3:
            return True
        
        # إضافة الرسالة الحالية
        self.spam_detection[user_id].append((current_time, message_text))
        return False
    
    def ban_user(self, user_id, reason="مخالفة القوانين"):
        """حظر مستخدم"""
        self.banned_users.add(user_id)
        
        # حفظ في قاعدة البيانات
        try:
            self.supabase.table('banned_users').insert({
                'user_id': user_id,
                'reason': reason,
                'banned_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            print(f"خطأ في حفظ الحظر: {e}")
    
    def unban_user(self, user_id):
        """إلغاء حظر مستخدم"""
        self.banned_users.discard(user_id)
        
        # حذف من قاعدة البيانات
        try:
            self.supabase.table('banned_users').delete().eq('user_id', user_id).execute()
        except Exception as e:
            print(f"خطأ في إلغاء الحظر: {e}")
    
    def is_banned(self, user_id):
        """فحص إذا كان المستخدم محظور"""
        return user_id in self.banned_users
    
    def validate_clan_name(self, name):
        """التحقق من صحة اسم الكلان"""
        if len(name) < 3 or len(name) > 20:
            return False, "اسم الكلان يجب أن يكون بين 3 و 20 حرف"
        
        if not name.replace(' ', '').replace('_', '').isalnum():
            return False, "اسم الكلان يجب أن يحتوي على أحرف وأرقام فقط"
        
        # فحص الكلمات المحظورة
        banned_words = ['admin', 'bot', 'spam', 'hack']
        if any(word in name.lower() for word in banned_words):
            return False, "اسم الكلان يحتوي على كلمات محظورة"
        
        return True, "صحيح"
    
    def log_action(self, user_id, action, details=""):
        """تسجيل الأنشطة"""
        try:
            self.supabase.table('activity_logs').insert({
                'user_id': user_id,
                'action': action,
                'details': details,
                'timestamp': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            print(f"خطأ في تسجيل النشاط: {e}")

# تهيئة مدير الأمان
security_manager = SecurityManager(supabase)

# ============================
# فلاتر الحماية
# ============================

def security_check(func):
    """ديكوريتر للفحص الأمني"""
    async def wrapper(client, message):
        user_id = message.from_user.id
        
        # فحص الحظر
        if security_manager.is_banned(user_id):
            await message.reply("⛔ أنت محظور من استخدام البوت")
            return
        
        # فحص السبام
        if security_manager.detect_spam(user_id, message.text or ""):
            await message.reply("⚠️ تم اكتشاف رسائل مكررة. يرجى التوقف عن الإرسال المتكرر")
            return
        
        # فحص حد المعدل
        if not security_manager.check_rate_limit(user_id, "command"):
            await message.reply("⏰ يرجى الانتظار قبل استخدام الأوامر مرة أخرى")
            return
        
        return await func(client, message)
    return wrapper

# ============================
# أوامر الإدارة والحماية
# ============================

@app.on_message(filters.command("ban") & filters.user(ADMIN_IDS))
async def ban_user_command(client, message):
    """أمر حظر مستخدم"""
    try:
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            user_name = message.reply_to_message.from_user.first_name
            
            reason = " ".join(message.command[1:]) if len(message.command) > 1 else "مخالفة القوانين"
            
            security_manager.ban_user(user_id, reason)
            security_manager.log_action(message.from_user.id, "ban_user", f"حظر {user_name} - السبب: {reason}")
            
            await message.reply(f"🚫 تم حظر {user_name}\nالسبب: {reason}")
        else:
            await message.reply("يرجى الرد على رسالة المستخدم المراد حظره")
    except Exception as e:
        await message.reply(f"خطأ في تنفيذ الأمر: {str(e)}")

@app.on_message(filters.command("unban") & filters.user(ADMIN_IDS))
async def unban_user_command(client, message):
    """أمر إلغاء حظر مستخدم"""
    try:
        if len(message.command) > 1:
            user_id = int(message.command[1])
            
            security_manager.unban_user(user_id)
            security_manager.log_action(message.from_user.id, "unban_user", f"إلغاء حظر {user_id}")
            
            await message.reply(f"✅ تم إلغاء حظر المستخدم {user_id}")
        else:
            await message.reply("يرجى إدخال معرف المستخدم\nمثال: /unban 123456789")
    except Exception as e:
        await message.reply(f"خطأ في تنفيذ الأمر: {str(e)}")

@app.on_message(filters.command("logs") & filters.user(ADMIN_IDS))
async def view_logs_command(client, message):
    """عرض سجل الأنشطة"""
    try:
        # جلب آخر 20 نشاط
        response = supabase.table('activity_logs').select('*').order('timestamp', desc=True).limit(20).execute()
        
        if not response.data:
            await message.reply("📝 لا توجد أنشطة مسجلة")
            return
        
        logs_text = "📋 **سجل الأنشطة الأخيرة:**\n\n"
        
        for log in response.data:
            timestamp = datetime.fromisoformat(log['timestamp']).strftime("%Y-%m-%d %H:%M")
            logs_text += f"🕐 {timestamp}\n"
            logs_text += f"👤 المستخدم: {log['user_id']}\n"
            logs_text += f"⚡ النشاط: {log['action']}\n"
            if log['details']:
                logs_text += f"📝 التفاصيل: {log['details']}\n"
            logs_text += "─────────────\n"
        
        await message.reply(logs_text)
    except Exception as e:
        await message.reply(f"خطأ في جلب السجلات: {str(e)}")

@app.on_message(filters.command("stats") & filters.user(ADMIN_IDS))
async def admin_stats_command(client, message):
    """إحصائيات شاملة للإدارة"""
    try:
        # إحصائيات المستخدمين
        users_response = supabase.table('users').select('*').execute()
        total_users = len(users_response.data)
        
        # إحصائيات الكلانات
        clans_response = supabase.table('clans').select('*').execute()
        total_clans = len(clans_response.data)
        
        # إحصائيات الرسائل (آخر 24 ساعة)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        messages_response = supabase.table('user_stats').select('messages').gte('last_message', yesterday).execute()
        daily_messages = sum(user['messages'] for user in messages_response.data)
        
        # إحصائيات المحظورين
        banned_response = supabase.table('banned_users').select('*').execute()
        banned_count = len(banned_response.data)
        
        stats_text = f"""📊 **إحصائيات البوت الشاملة**

👥 **المستخدمين:**
• العدد الكلي: {total_users:,}
• المحظورين: {banned_count}
• النشطين (24 ساعة): {len(messages_response.data)}

🏰 **الكلانات:**
• العدد الكلي: {total_clans}

💬 **الرسائل:**
• آخر 24 ساعة: {daily_messages:,}

🔒 **الأمان:**
• المستخدمين المحظورين: {banned_count}
• معدل الرسائل: {daily_messages/24:.1f} رسالة/ساعة
"""
        
        await message.reply(stats_text)
    except Exception as e:
        await message.reply(f"خطأ في جلب الإحصائيات: {str(e)}")

# ============================
# نظام النسخ الاحتياطي
# ============================

@app.on_message(filters.command("backup") & filters.user(ADMIN_IDS))
async def backup_data_command(client, message):
    """إنشاء نسخة احتياطية من البيانات"""
    try:
        backup_data = {}
        
        # نسخ احتياطية للجداول الرئيسية
        tables = ['users', 'clans', 'clan_members', 'clan_wars', 'challenges']
        
        for table in tables:
            response = supabase.table(table).select('*').execute()
            backup_data[table] = response.data
        
        # حفظ النسخة الاحتياطية
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        import json
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        await message.reply_document(
            backup_filename,
            caption=f"💾 **النسخة الاحتياطية جاهزة**\n\n📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n📊 الجداول: {', '.join(tables)}"
        )
        
        # حذف الملف المؤقت
        import os
        os.remove(backup_filename)
        
    except Exception as e:
        await message.reply(f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}")

# ============================
# تطبيق فلاتر الحماية على الأوامر الموجودة
# ============================

# تطبيق الحماية على أوامر XP
@app.on_message(filters.command("xp") & filters.group)
@security_check
async def xp_command_secure(client, message):
    """أمر XP مع الحماية"""
    await xp_command(client, message)

# تطبيق الحماية على أوامر الكلانات
@app.on_message(filters.command("create_clan") & filters.group)
@security_check
async def create_clan_command_secure(client, message):
    """أمر إنشاء كلان مع الحماية"""
    await create_clan_command(client, message)
