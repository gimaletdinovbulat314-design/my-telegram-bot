import os
import json
import uuid
import logging
import threading
import telebot
import re
from telebot import types, apihelper

# ==========================================
# 1. НАСТРОЙКА НАДЁЖНОГО ЛОГИРОВАНИЯ
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ==========================================
# 2. НАСТРОЙКА АДМИНИСТРАТОРА, ТОКЕНА И ПОДДЕРЖКИ
# ==========================================
# Владелец (Главный админ) — ТОЛЬКО ОН может добавлять и удалять других админов
OWNER_ID =  993051853

# Изначальный список администраторов (статические)
ADMIN_IDS = [8771182636, 993051853, 8360149272]  

BOT_TOKEN = "8737283848:AAEHsjQSwj_j9Gd1MMcF7xUWuR4vqV0gLWo"

IMAGE_PATH = "image_gpg" 

# Сюда впишите юзернейм аккаунта поддержки БЕЗ знака @
SUPPORT_USERNAME = "otcelftosupport" 

# ==========================================
# 3. АВТОМАТИЧЕСКИЙ ОБХОД СЕТЕВЫХ БЛОКИРОВОК
# ==========================================
USE_PROXY = False
PROXY_DATA = {
    'http': 'socks5://username:password@proxy_address:port',
    'https': 'socks5://username:password@proxy_address:port'
}

if USE_PROXY:
    apihelper.proxy = PROXY_DATA
    logging.info("Активирован обход блокировок через прокси-сервер.")

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# 4. ЛОКАЛЬНОЕ ХРАНИЛИЩЕ ДАННЫХ (ФАЙЛЫ JSON)
# ==========================================
DEALS_FILE = 'deals.json'
USER_DATA_FILE = 'user_data.json'
USER_DEALS_FILE = 'user_deals.json'

deals_lock = threading.Lock()
user_data_lock = threading.Lock()
user_deals_lock = threading.Lock()

def load_deals():
    with deals_lock:
        if not os.path.exists(DEALS_FILE): return {}
        try:
            with open(DEALS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: return {}

def save_deals(data):
    with deals_lock:
        try:
            with open(DEALS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e: logging.error(f"Ошибка записи сделок: {e}")

def load_user_data():
    with user_data_lock:
        if not os.path.exists(USER_DATA_FILE): return {}
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: return {}

def save_user_data(data):
    with user_data_lock:
        try:
            with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e: logging.error(f"Ошибка записи данных пользователей: {e}")

def load_user_deals():
    with user_deals_lock:
        if not os.path.exists(USER_DEALS_FILE): return {}
        try:
            with open(USER_DEALS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: return {}

def save_user_deals(data):
    with user_deals_lock:
        try:
            with open(USER_DEALS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e: logging.error(f"Ошибка записи счетчика сделок: {e}")

deals = load_deals()
user_data = load_user_data()
user_deals = load_user_deals()
referrals = {} 
language_message_ids = {}

logging.info("Базы данных успешно инициализированы.")

# ==========================================
# 5. МУЛЬТИЯЗЫЧНЫЙ СЛОВАРЬ (РУС / ENG)
# ==========================================
user_language = {}

def get_language(user_id):
    return user_language.get(user_id, 'ru')

def set_language(user_id, language):
    user_language[user_id] = language

localized_text = {
    'ru': {
        'welcome_message': "*Добро пожаловать в ELF OTC – надежный P2P-гарант*\n\n"
                           "*💼 Покупайте и продавайте всё, что угодно – безопасно!*\n"
                           "От Telegram-подарков и NFT до токенов и фиата – сделки проходят легко и без риска.\n\n"
                           "🔹 Поддержка валют: TON, USDT, RUB (₽), UAH (₴)\n"
                           "🔹 Управление кошельками и банковскими картами РФ/Украины\n"
                           "🔹 Реферальная система\n\n"
                           "Выберите нужный раздел ниже:",
        'requisites_menu': "🔑 *Управление вашими реквизитами для выплат*\n\nВыберите тип реквизитов для добавления или изменения:",
        'ton_wallet_prompt_new': "🔑 Добавьте ваш TON-кошелек:\n\nПожалуйста, отправьте адрес вашего кошелька.",
        'ton_wallet_prompt_existing': "💼 Ваш текущий кошелек: `{}`\n\nОтправьте новый адрес кошелька для изменения или нажмите кнопку ниже для возврата в меню.",
        'card_prompt_new': "💳 Добавьте ваши реквизиты карты (RUB / UAH):\n\nПожалуйста, отправьте реквизиты в таком формате:\n\nСбербанк - 1234567890123456",
        'card_prompt_existing': "💳 Ваши текущие реквизиты карты: `{}`\n\nОтправьте новые реквизиты для изменения или нажмите кнопку ниже для возврата в меню.",
        'create_deal_amount_prompt': "💼 *Создание сделки*\n\nВыберите валюту сделки:",
        'deal_created_message': "*✅ Сделка успешно создана!*\n\n💰 Сумма: {} {}\n📜 Описание: {}\n🔗 Ссылка для покупателя: t.me/{}?start={}",
        'deal_info_buyer': """💳 Информация о сделке #{}\n\n👤 Вы покупатель в сделке.\n📌 Продавец: @{} ({})\n• Успешные сделки: {}\n\n• Вы покупаете: {}\n\n🏦 Реквизиты продавца для оплаты:\n`{}`\n\n💰 Сумма к оплате: {} {}\n\n⚠️ Пожалуйста, убедитесь в правильности данных перед оплатой. После оплаты загрузите скриншот чека в этот чат!""",
        'cancel_deal_confirmation': "❌ Вы уверены, что хотите отменить сделку #{}?\n\nЭто действие нельзя будет отменить.",
        'success_leave_deal': "Сделка успешно отменена.",
        'referral_message': """🔗 Ваша реферальная ссылка:\n\n{}\n\n👥 Количество рефералов: {}\n💰 Заработано с рефералов: {:.2f} TON\n20% от комиссии бота""",
        'admin_payment_confirmation': "💼 Админ-панель управления сделкой #{}\n\nСумма: {} {}\nОписание: {}\nПродавец: {}\nПокупатель: {}\n\nПодтвердить получение оплаты от покупателя на счета гаранта?",
        'admin_payment_confirmed': "✅ Оплата подтверждена для сделки #{}.\nОжидайте подтверждения от продавца.", 
        'admin_payment_confirmed_buyer': "💳 Оплата по сделке #{} подтверждена.\nПродавец: @{}\nСумма: {} {}\nОписание: {}\n\nОжидайте, пока продавец отправит товар/услугу.", 
        'seller_payment_confirmation': "✅ Оплата подтверждена для сделки {}.\nСумма: {} {}\nОписание: {}\nПокупатель: @{}\n\nСледуйте указаниям, согласованным в сделке.\n\n⚠️ После отправки подарка нажмите кнопку ниже:",
        'seller_sent_confirmation': "✅ Вы подтвердили отправку подарка для сделки #{}.\nОжидайте подтверждение от покупателя.",
        'buyer_received_confirmation': "✅ Вы подтвердили получение подарка для сделки #{}. Сделка успешно завершена!",
        'set_deals_success': "Успешные сделки установлены на {}.",
        'buy_command_usage': "Пожалуйста, укажите код сделки после команды /buy", 
        'deal_not_found': "Сделка не найдена.", 
        'payment_confirmed_for_seller': "✅ Сделка {} успешно завершена!\nПокупатель @{} подтвердил получение подарка.", 
        "wallet_added_successfully": "✅ Реквизиты успешно сохранены!",
        "no_wallet_message": "❌ У вас не добавлены реквизиты! Пожалуйста, добавьте кошелек или карту перед созданием сделки.",
        "add_wallet_button_text": "Добавить реквизиты",
        'create_deal_prompt': "*💼 Создание сделки*\n\nТекущая сумма: {} {}\n\n*📝 Укажите, что вы предлагаете в этой сделке:*\n\nПример: 10 Кепок и Пепе...",
        "invalid_wallet_format": "❌ Неверный формат TON-кошелька. Попробуйте еще раз.", 
        "invalid_card_format": "❌ Неверный формат реквизитов карты. Пожалуйста, укажите название банка и номер карты/счета.",
        "wait_buyer": "Ожидайте подтверждение от покупателя"
    },
    'en': {
        'welcome_message': "*Welcome to ELF OTC – reliable P2P guarantor*\n\n"
                           "*💼 Buy and sell anything safely!*\n\n"
                           "Choose a section below:",
        'requisites_menu': "🔑 *Requisites Management*\n\nChoose payment method to add or modify:",
        'ton_wallet_prompt_new': "🔑 Add your TON wallet:\n\nPlease send your wallet address.",
        'ton_wallet_prompt_existing': "*💼 Your current wallet:* `{}`\n\nSend a new wallet address.",
        'card_prompt_new': "💳 Add your card details (RUB / UAH):\n\nPlease send details in this format:\n\nBankName - 1234567890123456",
        'card_prompt_existing': "💳 Your current card details: `{}`\n\nSend new details.",
        'create_deal_amount_prompt': "💼 *Creating a deal*\n\nSelect deal currency:",
        'deal_created_message': "*✅ Deal created successfully!*\n\n💰 Amount: {} {}\n📜 Description: {}\n🔗 Link: https://t.me{}?start={}",
        'deal_info_buyer': """💳 Deal information #{}\n\n🏦 Payment details:\n`{}`\n\n💰 Amount: {} {}""",
        'cancel_deal_confirmation': "❌ Are you sure you want to cancel deal #{}?",
        'success_leave_deal': "✅ Deal cancelled successfully.",
        'referral_message': """🔗 Your referral link:\n\n{}\n\n👥 Referrals: {}\n💰 Earned: {:.2f} TON""",
        'admin_payment_confirmation': "💼 Admin Deal Manager #{}\n\nAmount: {} {}\nConfirm payment?",
        'admin_payment_confirmed': "✅ Payment confirmed for deal #{}.", 
        'admin_payment_confirmed_buyer': "💳 Payment for deal #{} confirmed.\nSeller: @{}\nAmount: {} {}\nItem: {}", 
        'seller_payment_confirmation': "✅ Payment confirmed for deal {}.\nAmount: {} {}\nBuyer: @{}\n\n⚠️ After sending the gift, click the button below:",
        'seller_sent_confirmation': "✅ You confirmed sending the items for deal #{}.",
        'buyer_received_confirmation': "✅ Deal completed successfully!",
        'create_deal_prompt': "*💼 Creating a deal*\n\nCurrent amount: {} {}\n\n*📝 Specify what you are offering:*",
        'invalid_wallet_format': "❌ Invalid TON wallet format.",
        'invalid_card_format': "❌ Invalid card format.",
        'wait_buyer': "Waiting for confirmation from the buyer",
        'wallet_added_successfully': "✅ Requisites saved successfully!",
        'no_wallet_message': "❌ Requisites are missing! Please add a wallet or card before creating a deal.",
        'add_wallet_button_text': "Add Requisites",
        'deal_not_found': "Deal not found.",
        'payment_confirmed_for_seller': "✅ Deal {} completed! Buyer @{} confirmed receipt."
    }
}

def get_localized_text(key, user_id, *args):
    language = get_language(user_id)
    try:
        return localized_text[language][key].format(*args)
    except KeyError:
        logging.warning(f"Key '{key}' not found for language '{language}'. Using Russian instead.")
        return localized_text['ru'].get(key, "Ошибка текста").format(*args)
    except Exception:
        return "Ошибка локализации"

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ==========================================
# 6. ВСПОМОГАТЕЛЬНЫЕ МЕДИАФУНКЦИИ
# ==========================================

def log_jpg_link(media_result):
    try:
        if isinstance(media_result, types.Message) and media_result.photo:
            file_id = media_result.photo[-1].file_id
            file_info = bot.get_file(file_id)
            file_path = file_info.file_path
            direct_jpg_url = f"https://telegram.org{BOT_TOKEN}/{file_path}"
            logging.info(f"🔗 Сгенерирована прямая JPG ссылка фонового изображения: {direct_jpg_url}")
    except Exception as e:
        logging.error(f"Не удалось сгенерировать JPG-ссылку: {e}")

def edit_message_with_photo(chat_id, message_id, photo_path, text, reply_markup=None):
    try:
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                res = bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=types.InputMediaPhoto(photo, caption=text, parse_mode="Markdown"),
                    reply_markup=reply_markup
                )
                log_jpg_link(res)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения с фото: {e}")

def send_photo_with_caption(chat_id, photo_path, text, reply_markup=None):
    try:
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                res = bot.send_photo(chat_id, photo=photo, caption=text, reply_markup=reply_markup, parse_mode="Markdown")
                log_jpg_link(res)
        else:
            bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка отправки фото: {e}")

def send_main_menu(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_create = types.InlineKeyboardButton("💼 Создать сделку" if language == 'ru' else "💼 Create Deal", callback_data='create_deal')
    btn_reqs = types.InlineKeyboardButton("🔑 Реквизиты" if language == 'ru' else "🔑 Requisites", callback_data='requisites_menu')
    btn_ref = types.InlineKeyboardButton("👥 Рефералы" if language == 'ru' else "👥 Referrals", callback_data='referral')
    btn_lang = types.InlineKeyboardButton("🌍 Язык / Language", callback_data='change_language')
    
    # Кнопка теперь отправляет callback_data вместо внешней ссылки
    btn_support = types.InlineKeyboardButton("✍️ Поддержка" if language == 'ru' else "✍️ Support", callback_data='open_support')
    
    markup.add(btn_create, btn_reqs)
    markup.add(btn_ref, btn_lang)
    markup.add(btn_support)
    
    if is_admin(chat_id):
        markup.add(types.InlineKeyboardButton("👑 Админ-Панель", callback_data='admin_main_menu'))
        
    text = get_localized_text('welcome_message', chat_id)
    
    if message_id is not None:
        try: 
            bot.delete_message(chat_id, message_id)
        except Exception: 
            pass
            
    send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_requisites_menu(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💎 TON кошелек", callback_data='edit_req_ton'),
        types.InlineKeyboardButton("💳 Банковская карта (RUB / UAH)", callback_data='edit_req_card'),
        types.InlineKeyboardButton("🔙 В меню", callback_data='back_to_menu')
    )
    text = get_localized_text('requisites_menu', chat_id)
    if message_id: edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else: send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_ton_wallet_prompt(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Назад", callback_data='requisites_menu'))
    str_chat_id = str(chat_id)
    if str_chat_id in user_data and 'ton_wallet' in user_data[str_chat_id]:
        text = get_localized_text('ton_wallet_prompt_existing', chat_id, user_data[str_chat_id]['ton_wallet'])
    else:
        text = get_localized_text('ton_wallet_prompt_new', chat_id)
    if message_id: edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else: send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_card_prompt(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Назад", callback_data='requisites_menu'))
    str_chat_id = str(chat_id)
    if str_chat_id in user_data and 'card' in user_data[str_chat_id]:
        text = get_localized_text('card_prompt_existing', chat_id, user_data[str_chat_id]['card'])
    else:
        text = get_localized_text('card_prompt_new', chat_id)
    if message_id: edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else: send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

# ==========================================
# 7. СЦЕНАРИИ СДЕЛКИ И АДМИН-ПАНЕЛЬ
# ==========================================
def send_create_deal_currency_prompt(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💎 TON", callback_data='deal_currency_TON'),
        types.InlineKeyboardButton("💵 USDT", callback_data='deal_currency_USDT'),
        types.InlineKeyboardButton("🇷🇺 RUB", callback_data='deal_currency_RUB'),
        types.InlineKeyboardButton("🇺🇦 UAH", callback_data='deal_currency_UAH'),
        types.InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
    )
    text = get_localized_text('create_deal_amount_prompt', chat_id)
    if message_id: edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else: send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_create_deal_description_prompt(chat_id, currency, amount, message_id=None):
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 В меню", callback_data='back_to_menu'))
    text = get_localized_text('create_deal_prompt', chat_id, amount, currency)
    if message_id: edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else: send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_deal_created_message(chat_id, deal_id=None, amount=None, currency="TON", description=None):
    language = get_language(chat_id)
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Отменить сделку" if language == 'ru' else "❌ Cancel deal", callback_data=f"cancel_deal_{deal_id}"))
    bot_username = bot.get_me().username.replace("@", "")
    text = get_localized_text('deal_created_message', chat_id, amount, currency, description, bot_username, deal_id)
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def send_buyer_deal_page(chat_id, deal_id, message_id=None):
    deals_dict = load_deals()
    if deal_id not in deals_dict: return
    data = deals_dict[deal_id]
    currency = data.get('currency', 'TON')
    seller_id_str = str(data['seller_id'])
    
    if currency in ['TON', 'USDT']:
        payment_requisites = user_data.get(seller_id_str, {}).get('ton_wallet', "Не указан")
    else:
        payment_requisites = user_data.get(seller_id_str, {}).get('card', "Не указаны")
        
    seller_deals = user_deals.get(seller_id_str, 0)
    try: seller_username = bot.get_chat_member(data['seller_id'], data['seller_id']).user.username or f"id{data['seller_id']}"
    except Exception: seller_username = f"id{data['seller_id']}"
    
    text = get_localized_text('deal_info_buyer', chat_id, deal_id, seller_username, data['seller_id'], seller_deals, data['description'], payment_requisites, data['amount'], currency)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Покинуть сделку", callback_data=f"buyer_leave_deal_{deal_id}"))
    if message_id: edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else: send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_admin_main_menu(chat_id, message_id=None):
    if not is_admin(chat_id): return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📊 Список активных сделок", callback_data="admin_list_deals_0"),
        types.InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")
    )
    text = "👑 Панель Администратора ELF OTC\n\nЗдесь вы можете вручную подтверждать оплаты чеков."
    if message_id: edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else: send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_admin_deal_card(chat_id, deal_id, message_id=None):
    deals_dict = load_deals()
    if deal_id not in deals_dict: return
    deal = deals_dict[deal_id]
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔙 К списку сделок", callback_data="admin_list_deals_0")
    )
    text = f"⚙️ Управление сделкой #{deal_id}\n\n💰 Сумма: {deal['amount']} {deal.get('currency', 'TON')}\n📝 Описание: {deal['description']}\n👤 Продавец: {deal['seller_id']}\n👥 Покупатель: {deal.get('buyer_id', 'Не присоединен')}"
    if message_id: edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else: send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

# ==========================================
# 8. ОБРАБОТКА НАЖАТИЙ НА КНОПКИ (CALLBACKS)
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global deals, referrals, user_deals, language_message_ids, user_data
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data
    language = get_language(chat_id)
    str_chat_id = str(chat_id)

    if data == 'requisites_menu':
        send_requisites_menu(chat_id, message_id)

    # ОБРАБОТЧИК КНОПКИ ПОДДЕРЖКИ (ОКНО С ЮЗЕРНЕЙМОМ)
    elif data == 'open_support':
        clean_support = SUPPORT_USERNAME.replace("@", "").strip()
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 В меню" if language == 'ru' else "🔙 Menu", callback_data='back_to_menu')
        )
        if language == 'ru':
            support_text = f"✍️ *Служба поддержки ELF OTC*\n\nЕсли у вас возникли вопросы, спорная ситуация в сделке или проблемы с оплатой, напишите нашему менеджеру:\n\n🔗 *@{clean_support}*"
        else:
            support_text = f"✍️ *ELF OTC Support Service*\n\nIf you have any questions, a dispute in a deal, or payment issues, please message our manager:\n\n🔗 *@{clean_support}*"
        
        edit_message_with_photo(chat_id, message_id, IMAGE_PATH, support_text, markup)

    elif data == 'edit_req_ton':
        user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_ton_wallet'
        save_user_data(user_data)
        send_ton_wallet_prompt(chat_id, message_id)

    elif data == 'edit_req_card':
        user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_card'
        save_user_data(user_data)
        send_card_prompt(chat_id, message_id)

    elif data == 'create_deal':
        if str_chat_id not in user_data or ('ton_wallet' not in user_data[str_chat_id] and 'card' not in user_data[str_chat_id]):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(get_localized_text('add_wallet_button_text', chat_id), callback_data='requisites_menu'))
            edit_message_with_photo(chat_id, message_id, IMAGE_PATH, get_localized_text('no_wallet_message', chat_id), markup)
            return
        send_create_deal_currency_prompt(chat_id, message_id)

    elif data.startswith('deal_currency_'):
        parts = data.split('_')
        if len(parts) >= 3:
            selected_currency = parts[2]
            if selected_currency in ['TON', 'USDT'] and 'ton_wallet' not in user_data.get(str_chat_id, {}):
                bot.answer_callback_query(call.id, "❌ У вас не добавлен TON кошелек!", show_alert=True)
                return
            if selected_currency in ['RUB', 'UAH'] and 'card' not in user_data.get(str_chat_id, {}):
                bot.answer_callback_query(call.id, "❌ У вас не добавлены реквизиты карты!", show_alert=True)
                return
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_deal_amount'
            user_data[str_chat_id]['deal_currency'] = selected_currency
            save_user_data(user_data)
            edit_message_with_photo(chat_id, message_id, IMAGE_PATH, "💼 Создание сделки\n\nВведите сумму сделки числом (например, 150.50):", None)

    elif data == 'referral':
        bot_username = bot.get_me().username.replace("@", "")
        referral_link = f"https://t.me{bot_username}?start=ref={chat_id}"
        num_referrals = referrals.get(chat_id, {}).get('referrals', 0)
        earned_from_referrals = referrals.get(chat_id, {}).get('earned', 0.0)
        bot.send_message(chat_id, get_localized_text('referral_message', chat_id, referral_link, num_referrals, earned_from_referrals), parse_mode="Markdown")

    elif data == 'change_language':
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Русский", callback_data='set_language_ru'), types.InlineKeyboardButton("English", callback_data='set_language_en'))
        sent_message = bot.send_message(chat_id=chat_id, text="🌍 Choose language / Выберите язык:", reply_markup=markup)
        language_message_ids[chat_id] = sent_message.message_id

    elif data.startswith('set_language_'):
        parts = data.split('_')
        if len(parts) >= 3:
            set_language(chat_id, parts[2])
            if chat_id in language_message_ids:
                try: bot.delete_message(chat_id, language_message_ids[chat_id])
                except Exception: pass
            send_main_menu(chat_id, message_id)

    elif data == 'back_to_menu':
        if str_chat_id in user_data: user_data[str_chat_id]['state'] = None
        save_user_data(user_data)
        send_main_menu(chat_id, message_id)

    elif data.startswith('cancel_deal_'):
        parts = data.split('_')
        if len(parts) >= 3: 
            deal_id = parts[2]
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Да, отменить", callback_data=f"confirm_leave_deal_{deal_id}"), types.InlineKeyboardButton("НЕТ", callback_data="back_to_menu"))
            try:
                bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=get_localized_text('cancel_deal_confirmation', chat_id, deal_id), reply_markup=markup, parse_mode="Markdown")
            except Exception:
                try: bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=get_localized_text('cancel_deal_confirmation', chat_id, deal_id), reply_markup=markup, parse_mode="Markdown")
                except Exception: pass

    elif data.startswith('buyer_leave_deal_'):
        parts = data.split('_')
        if len(parts) >= 4: 
            deal_id = parts[3]
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ ДА, ПОКИНУТЬ", callback_data=f"confirm_buyer_leave_deal_{deal_id}"), types.InlineKeyboardButton("НЕТ", callback_data=f"deal_info_{deal_id}"))
            edit_message_with_photo(chat_id, message_id, IMAGE_PATH, get_localized_text('cancel_deal_confirmation', chat_id, deal_id), markup)

    elif data.startswith('confirm_leave_deal_'):
        parts = data.split('_')
        if len(parts) >= 4:
            deal_id = parts[3]
            deals_dict = load_deals()
            if deal_id in deals_dict:
                seller_id = deals_dict[deal_id]['seller_id']
                del deals_dict[deal_id]
                save_deals(deals_dict)
                try: bot.delete_message(chat_id, message_id)
                except Exception: pass
                bot.send_message(chat_id, "Сделка успешно удалена.")
                bot.send_message(seller_id, f"Сделка #{deal_id} была полностью отменена.")

    elif data.startswith('confirm_buyer_leave_deal_'):
        parts = data.split('_')
        if len(parts) >= 5:
            deal_id = parts[4]
            deals_dict = load_deals()
            if deal_id in deals_dict:
                seller_id = deals_dict[deal_id]['seller_id']
                if 'buyer_id' in deals_dict[deal_id]: del deals_dict[deal_id]['buyer_id']
                save_deals(deals_dict)
                bot.send_message(seller_id, f"Покупатель покинул сделку #{deal_id}.")
                if message_id:
                    try: bot.delete_message(chat_id, message_id)
                    except Exception: pass
                bot.send_message(chat_id, "✅ Вы успешно покинули сделку.")

    elif data == 'admin_main_menu':
        send_admin_main_menu(chat_id, message_id)

    elif data.startswith('admin_list_deals_'):
        parts = data.split('_')
        if len(parts) >= 4: 
            page = int(parts[3])
            deals_dict = load_deals() 
            markup = types.InlineKeyboardMarkup(row_width=1) 
            all_keys = list(deals_dict.keys()) 
            if not all_keys: 
                markup.add(types.InlineKeyboardButton("🔙 В админку", callback_data="admin_main_menu")) 
                edit_message_with_photo(chat_id, message_id, IMAGE_PATH, "📋 Активных сделок нет.", markup) 
                return 
            for d_id in all_keys[page*5:(page+1)*5]: 
                markup.add(types.InlineKeyboardButton(f"Сделка #{d_id} | {deals_dict[d_id]['amount']}", callback_data=f"admin_manage_deal_{d_id}"))

            nav = []
            if page > 0: nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_list_deals_{page-1}"))
            if (page+1)*5 < len(all_keys): nav.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"admin_list_deals_{page+1}"))
            if nav: markup.row(*nav)
            markup.add(types.InlineKeyboardButton("🔙 В админку", callback_data="admin_main_menu"))
            edit_message_with_photo(chat_id, message_id, IMAGE_PATH, f"📋 Активные сделки (Страница {page+1}):", markup)

    elif data.startswith('admin_manage_deal_'):
        parts = data.split('_')
        if len(parts) >= 4:
            send_admin_deal_card(chat_id, parts[3], message_id)

    elif data.startswith('admin_confirm_payment_'):
        parts = data.split('_')
        if len(parts) >= 4:
            deal_id = parts[3]
            deals_dict = load_deals()
            if deal_id in deals_dict:
                seller_id = deals_dict[deal_id]['seller_id']
                buyer_id = deals_dict[deal_id].get('buyer_id')
                if not buyer_id:
                    bot.answer_callback_query(call.id, "Покупатель еще не присоединен!", show_alert=True)
                    return
                deals_dict[deal_id]['status'] = 'paid'
                save_deals(deals_dict)
                try:
                    bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=get_localized_text('admin_payment_confirmed', language, deal_id))
                except Exception:
                    try: bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=get_localized_text('admin_payment_confirmed', language, deal_id))
                    except Exception: pass

                try:
                    s_name = bot.get_chat_member(seller_id, seller_id).user.username or f"id{seller_id}"
                except Exception:
                    s_name = f"id{seller_id}"
                try:
                    b_name = bot.get_chat_member(buyer_id, buyer_id).user.username or f"id{buyer_id}"
                except Exception:
                    b_name = f"id{buyer_id}"

                bot.send_message(buyer_id, get_localized_text('admin_payment_confirmed_buyer', language, deal_id, s_name, deals_dict[deal_id]['amount'], deals_dict[deal_id].get('currency', 'TON'), deals_dict[deal_id]['description']), parse_mode="Markdown")
                markup_s = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Я отправил подарок", callback_data=f"seller_sent_{deal_id}"))
                bot.send_message(seller_id, get_localized_text('seller_payment_confirmation', language, deal_id, deals_dict[deal_id]['amount'], deals_dict[deal_id].get('currency', 'TON'), deals_dict[deal_id]['description'], b_name), reply_markup=markup_s)

    elif data.startswith('seller_sent_'):
        parts = data.split('_')
        if len(parts) >= 3:
            deal_id = parts[2]
            deals_dict = load_deals()
            if deal_id in deals_dict:
                deals_dict[deal_id]['seller_sent'] = True
                save_deals(deals_dict)
                try:
                    bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
                bot.send_message(chat_id, get_localized_text('seller_sent_confirmation', language, deal_id))
                markup_b = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Подтвердить получение", callback_data=f"buyer_received_{deal_id}"))
                bot.send_message(deals_dict[deal_id]['buyer_id'], "🎁 Продавец подтвердил отправку подарка!\nПодтвердите получение ниже:", reply_markup=markup_b)

    elif data.startswith('buyer_received_'):
        parts = data.split('_')
        if len(parts) >= 3:
            deal_id = parts[2]
            deals_dict = load_deals()
            if deal_id in deals_dict:
                s_id = deals_dict[deal_id]['seller_id']
                b_id = deals_dict[deal_id]['buyer_id']
                try:
                    b_uname = bot.get_chat_member(b_id, b_id).user.username or f"id{b_id}"
                except Exception:
                    b_uname = f"id{b_id}"
                bot.send_message(s_id, get_localized_text('payment_confirmed_for_seller', language, deal_id, b_uname))
                bot.send_message(b_id, get_localized_text('buyer_received_confirmation', language, deal_id))
                user_deals[str(s_id)] = user_deals.get(str(s_id), 0) + 1
                save_user_deals(user_deals)
                del deals_dict[deal_id]
                save_deals(deals_dict)
                try:
                    bot.answer_callback_query(call.id)
                except Exception:
                    pass

# ==========================================
# 9. ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ССЫЛОК И СТАРТА
# ==========================================
@bot.message_handler(commands=['start'])
def handle_start_deep_linking(message):
    chat_id = message.chat.id
    parts = message.text.split()

    if len(parts) > 1:
        param = parts[1]

        if param.startswith('ref='):
            try:
                ref_parts = param.split('=')
                if len(ref_parts) == 2:
                    ref_id = int(ref_parts[1])
                    if ref_id != chat_id:
                        referrals.setdefault(ref_id, {'referrals': 0, 'earned': 0.0})['referrals'] += 1
                        bot.send_message(chat_id, "🎁 Вы перешли по реферальной ссылке!")
            except Exception as e:
                logging.error(f"Ошибка реферальной системы: {e}")
            send_main_menu(chat_id)
            return

        deals_dict = load_deals()
        if param in deals_dict:
            if deals_dict[param]['seller_id'] == chat_id:
                bot.send_message(chat_id, "❌ Вы не можете войти в собственную сделку.")
                send_main_menu(chat_id)
                return
            if deals_dict[param].get('buyer_id') is not None:
                bot.send_message(chat_id, "❌ В этой сделке уже есть покупатель.")
                send_main_menu(chat_id)
                return
            deals_dict[param]['buyer_id'] = chat_id
            save_deals(deals_dict)
            send_buyer_deal_page(chat_id, param, None)
            try:
                bot.send_message(deals_dict[param]['seller_id'], f"🔔 Покупатель присоединился к вашей сделке #{param}!")
            except Exception:
                pass
            return

    send_main_menu(chat_id)

# ==========================================
# 10. ТЕКСТОВЫЕ КОМАНДЫ АДМИНИСТРАТОРА
# ==========================================
@bot.message_handler(commands=['admin'])
def cmd_admin(message):
    if is_admin(message.chat.id):
        send_admin_main_menu(message.chat.id, None)

@bot.message_handler(commands=['buy'])
def cmd_buy(message):
    if not is_admin(message.chat.id): return
    parts = message.text.split()
    if len(parts) == 2:
        send_admin_deal_card(message.chat.id, parts[1], None)

@bot.message_handler(commands=['set_my_deals'])
def cmd_set_deals(message):
    if not is_admin(message.chat.id): return
    parts = message.text.split()
    if len(parts) == 2:
        try:
            num = int(parts[1])
            user_deals[str(message.chat.id)] = num
            save_user_deals(user_deals)
            bot.reply_to(message, f"Успешные сделки установлены на {num}.")
        except Exception:
            pass

# ==========================================
# 11. ПОШАГОВЫЙ ОБРАБОТЧИК ВВОДА И ТЕКСТА
# ==========================================
@bot.message_handler(func=lambda msg: True, content_types=['text', 'photo'])
def handle_messages(message):
    global user_data
    chat_id = message.chat.id
    str_chat_id = str(chat_id)
    language = get_language(chat_id)

    # Прием скриншотов чеков от покупателей
    if message.content_type == 'photo':
        deals_dict = load_deals()
        target_id, target_deal = None, None
        for d_id, d_data in deals_dict.items():
            if d_data.get('buyer_id') == chat_id and d_data.get('status') == 'waiting_payment':
                target_id, target_deal = d_id, d_data
                break
        if target_deal:
            for adm in ADMIN_IDS:
                try:
                    bot.send_message(adm, f"💰 Загружен новый чек об оплате!\nСделка: {target_id}\nПокупатель: {chat_id}\nСумма: {target_deal['amount']} {target_deal.get('currency')}")
                    bot.forward_message(adm, chat_id, message.message_id)
                    bot.send_message(adm, "Управление сделкой:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_payment_{target_id}")))
                except Exception:
                    pass
            bot.send_message(chat_id, "✉️ Ваш чек успешно отправлен Администратору на верификацию.")
        else:
            bot.send_message(chat_id, "❌ У вас нет активных сделок на стадии оплаты для прикрепления чека.")
        return

    text = message.text.strip()

    # Поиск сделки по текстовому ID из чата
    if len(text) == 10 and (str_chat_id not in user_data or user_data[str_chat_id].get('state') is None):
        deals_dict = load_deals()
        if text in deals_dict:
            send_buyer_deal_page(chat_id, text, None)
            return

    if str_chat_id in user_data and user_data[str_chat_id].get('state') is not None:
        state = user_data[str_chat_id]['state']

        if state == 'waiting_for_deal_amount':
            try:
                amount = float(text.replace(',', '.'))
                if amount <= 0: raise ValueError
                user_data[str_chat_id]['deal_amount'] = amount
                user_data[str_chat_id]['state'] = 'waiting_for_deal_description'
                save_user_data(user_data)
                currency = user_data[str_chat_id].get('deal_currency', 'TON')
                send_create_deal_description_prompt(chat_id, currency, amount, None)
            except ValueError:
                bot.send_message(chat_id, "❌ Неверный формат суммы. Введите число больше 0:")

        elif state == 'waiting_for_deal_description':
            amount = user_data[str_chat_id]['deal_amount']
            currency = user_data[str_chat_id].get('deal_currency', 'TON')
            deal_id = uuid.uuid4().hex[:10]
            deals_dict = load_deals()
            deals_dict[deal_id] = {
                'seller_id': chat_id,
                'amount': amount,
                'currency': currency,
                'description': text,
                'seller_sent': False,
                'status': 'waiting_payment'
            }
            save_deals(deals_dict)
            user_data[str_chat_id]['state'] = None
            if 'deal_amount' in user_data[str_chat_id]:
                del user_data[str_chat_id]['deal_amount']
            save_user_data(user_data)
            send_deal_created_message(chat_id, deal_id, amount, currency, text)

        elif state == 'waiting_for_ton_wallet':
            if len(text) >= 40 and (text.startswith('EQ') or text.startswith('UQ')):
                user_data[str_chat_id]['ton_wallet'] = text
                user_data[str_chat_id]['state'] = None
                save_user_data(user_data)
                bot.send_message(chat_id, get_localized_text('wallet_added_successfully', chat_id), reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 В меню", callback_data='requisites_menu')))
            else:
                bot.send_message(chat_id, get_localized_text('invalid_wallet_format', chat_id))

        elif state == 'waiting_for_card':
            if len(text) >= 10 and any(c.isdigit() for c in text):
                user_data[str_chat_id]['card'] = text
                user_data[str_chat_id]['state'] = None
                save_user_data(user_data)
                bot.send_message(chat_id, get_localized_text('wallet_added_successfully', chat_id), reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 В меню", callback_data='requisites_menu')))
            else:
                bot.send_message(chat_id, get_localized_text('invalid_card_format', chat_id))

# ==========================================
# 12. ПОЛЛИНГ И ЗАПУСК СКРИПТА
# ==========================================
if __name__ == '__main__':
    logging.info("P2P Гарант-Бот ELF OTC успешно запущен!")
    bot.polling(none_stop=True, timeout=90)
