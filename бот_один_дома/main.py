from datetime import datetime
from datetime import timedelta
from telegram import ForceReply, Update
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.ext import CallbackQueryHandler
from telegram.ext import ConversationHandler
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, KeyboardButton
import re
from menu_loader import FoodLoader
from load_config import load_config
from stages import*
import os


class OrderInfo:
    def __init__(self,user_id):
        self.user_id = user_id
        self.address = None
        self.time = None
        self.number_person = None
        self.cultery = None
        self.payment = None
        self.phone = None
        self.wishes = None

    def __str__(self):
        return f""" 
        ID пользователя: {self.user_id}
        Адрес доставки: {self.address}
        Время доставки: {self.time if self.time!=None else "Как можно быстрее"}
        Количество персон: {self.number_person}
        Нужны ли столовые приборы: {self.cultery}
        Способ оплаты: {self.payment}
        Номер телефона: {self.phone}
        Пожелания к заказу: {self.wishes if self.wishes!=None else "Пожеланий или промокода нет"}"""


def get_food_by_id(storage, food_id):
    return storage.get('menu',{}).get(food_id,None)

def get_food_by_query_data(storage, food_group, food_id):
    menu = storage.get('menu',{})
    food_id = int(food_id)
    food = None
    list_food = menu.get(food_group,[])
    for item in list_food:
        if item.id == food_id:
            food = item
    return food

def get_quantity_from_cart(storage, food_id):
    return storage.get('cart',{}).get(food_id,0)

def change_quantity_from_cart(storage, food_id, valeu):
    cart = storage.get('cart',{})
    cart[food_id]=valeu
    storage["cart"] = cart

def get_food_id_and_quantity_from_cart(storage):
    cart = storage.get('cart',{})
    return list(cart.items()) #[(1,2),(2,4)]

def clear_cart(storage):
    storage["cart"] = {}

def add_deleted_msg(storage, msg):
    if 'deleted_msg' not in storage:
        storage["deleted_msg"]=[]

    print(storage["deleted_msg"])
    storage["deleted_msg"].append(msg)


async def delete_old_msg(storage):
    for msg in storage.get("deleted_msg",[]):
        await msg.delete()
    storage["deleted_msg"]=[]

def reservation(bot_data, user_data):
    text = ""
    total_price = 0
    total_quantity = 0
    for id, quantity in get_food_id_and_quantity_from_cart(user_data):
        total_quantity += quantity
        if quantity>0:
            food = get_food_by_id(bot_data, int(id))
            if food:
                text +=f"<b>{food.name}</b>, {quantity} шт. Цена: <u>{food.price * quantity} руб</u>.\n"
                total_price += food.price * quantity
             
    if total_quantity>0:
        text += f"<i><b>Общая цена</b></i>: {total_price} руб."
    return text,total_price,total_quantity
    

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_old_msg(context.user_data)
    reply_keyboard = [["Главное меню"], ["Корзина"], ["Информация о нас"]]
    await update.message.reply_text(text = "Оформление заказа", reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Нажмите меню"))
    

async def button_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = []
    for item in context.bot_data["menu"]:
        if type(item)!=int:
            keyboard.append([InlineKeyboardButton(item, callback_data="group_"+item)])
    keyboard.append([InlineKeyboardButton("корзина",callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Нажмите сюда:", reply_markup=reply_markup)
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Нажмите сюда:", reply_markup=reply_markup)


async def button_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    food_group = query.data.split("_",1)[-1]#group_суп [group, суп] \ group_салат [group, салат] \ group_кофе_чай [group, кофе_чай]
    list_food = context.bot_data["menu"][food_group]
    keyboard = []
    for item in list_food:
        keyboard.append([InlineKeyboardButton(item.name,callback_data=f'food_{food_group}_{item.id}')])

    keyboard.append([InlineKeyboardButton("в главное меню",callback_data=f'main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("выберите позицию:", reply_markup=reply_markup)


async def food_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action, food_group, food_id = query.data.split("_",2) 
    food = get_food_by_query_data(context.bot_data, food_group, food_id)

    if not food:
        await query.edit_message_text(f"Что-то пошло не так попробуйте заново")
    else:
        quantity = get_quantity_from_cart(context.user_data, food_id)
        if action=="add":
            quantity+=1
        elif action=="sub" and quantity>0:
            quantity-=1

        change_quantity_from_cart(context.user_data, food_id, quantity)
        keyboard = []
        if quantity>0:
            keyboard.append([InlineKeyboardButton("удалить из корзины",callback_data=f'sub_{food_group}_{food_id}')])#sub_суп_1
        keyboard.append([InlineKeyboardButton("добавить в корзину",callback_data=f'add_{food_group}_{food_id}')])#add_суп_1
        keyboard.append([InlineKeyboardButton("в главное меню",callback_data=f'main_menu')])
        keyboard.append([InlineKeyboardButton("перейти в корзину",callback_data=f'cart')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (f"""<b>{food.name}</b>
<b>Цена: </b> {food.price} руб.
<b>Вес: </b> {food.weight} г.
<b>Cостав: </b> {food.composition}
<b>К/Б/Ж/У: </b> {food.cal}/{food.p}/{food.t}/{food.c} 
<b>количество: </b> {quantity}""")
        await query.edit_message_text(text=text,parse_mode='HTML',reply_markup=reply_markup)
        

async def cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_old_msg(context.user_data)
    text, total_price, total_quantity = reservation(context.bot_data,context.user_data)            
    if total_quantity>0:
        keyboard = [
            [InlineKeyboardButton("очистить", callback_data="clear_cart")],
            [InlineKeyboardButton("реактировать", callback_data="edit_cart")],
            [InlineKeyboardButton("оформить заказ",callback_data='order')],
            [InlineKeyboardButton("в главное меню",callback_data='main_menu')]
        ]
    else:
        text = "Ваша корзина пуста"
        keyboard = [
            [InlineKeyboardButton("в главное меню",callback_data='main_menu')]
        ]


    reply_markup = InlineKeyboardMarkup(keyboard)

    if  update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text,parse_mode='HTML',reply_markup=reply_markup)
    else:
        await update.message.reply_text(text,parse_mode='HTML',reply_markup=reply_markup)

async def clear_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_old_msg(context.user_data)
    query = update.callback_query
    await query.answer()
    clear_cart(context.user_data)
    keyboard = [
        [InlineKeyboardButton("в главное меню",callback_data='main_menu')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Корзина очищена"
    await query.edit_message_text(text,reply_markup=reply_markup)


async def edit_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if  update.callback_query:
        query = update.callback_query
        await query.answer()
        query.delete_message()

    await delete_old_msg(context.user_data)
    for id, quantity in get_food_id_and_quantity_from_cart(context.user_data):
        food = get_food_by_id(context.bot_data, int(id))
        if food:
            keyboard = []
            if quantity>0:
                keyboard.append([InlineKeyboardButton("удалить из корзины",callback_data=f'sub_{food.type}_{food.id}')])#sub_суп_1
            keyboard.append([InlineKeyboardButton("добавить в корзину",callback_data=f'add_{food.type}_{food.id}')])#add_суп_1
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = (f"""<b>{food.name}</b>
<b>Цена: </b>{food.price} руб.
<b>Вес: </b>{food.weight} г.
<b>состав: </b>{food.composition}
<b>К/Б/Ж/У: </b>{food.cal}/{food.p}/{food.t}/{food.c} 
<b>Количество: </b>{quantity}""")
            msg = await context.bot.send_message(update.effective_user.id, text, parse_mode='HTML', reply_markup=reply_markup)
            add_deleted_msg(context.user_data, msg)

            

async def delivery_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await context.bot.send_message(update.effective_user.id, text = "Укажите адрес доставки (Формат: Улица, дом, подъезд, этаж, квартира)")
    return ADDRESS

async def input_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    address_name = update.message.text
    context.user_data['order_info'] = OrderInfo(update.effective_user.id)
    context.user_data['order_info'].address = address_name
    keyboard = []
    keyboard.append([InlineKeyboardButton("доставить ко времени", callback_data='delivery_time')])
    keyboard.append([InlineKeyboardButton("доставить как можно быстрее", callback_data='near_furure')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text="Выберите время доставки", reply_markup=reply_markup)
    return ORDER

async def confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"Укажите время доставки в формате чч:мм(12:40)")
    return CONFIRM

async def confirm_time(update: Update, context: ContextTypes.DEFAULT_TYPE)-> int:
    text = update.message.text
    text = "".join(text.split())
    time = text.split(":")
    if len(time)!=2:
        await update.message.reply_text("Укажите время доставки в формате чч:мм(12:40)")
        return CONFIRM
    hh = int(time[0])
    mm = int(time[1])
    if not(hh>=0 and hh<=23 and mm>=0 and mm<=59):
        await update.message.reply_text("Проверьте верность ввода времени")
        return CONFIRM
    context.user_data['order_info'].time = f"{hh:02}:{mm:02}"
    await update.message.reply_text("Укажите количество персон")
    return PERSON
    

async def number_of_people(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"Укажите количество персон")
    return PERSON

async def input_number_of_people(update: Update, context: ContextTypes.DEFAULT_TYPE)-> int:
    text = update.message.text
    text = "".join(text.split())
    if not text.isdigit():
        await update.message.reply_text("Укажите количество персон числом, не прописью ")
        return PERSON
    number = int(text)
    context.user_data['order_info'].number_person = number
    keyboard = []
    keyboard.append([InlineKeyboardButton("Да", callback_data="да")])
    keyboard.append([InlineKeyboardButton("Нет", callback_data="нет")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Нужны ли вам столовые приборы?"
    await update.message.reply_text(text,reply_markup=reply_markup)
    return AVAILABLE_CULTERY

async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['order_info'].cultery=query.data
    keyboard = []
    keyboard.append([InlineKeyboardButton("карта", callback_data="карта")])
    keyboard.append([InlineKeyboardButton("наличные", callback_data="наличные")])
    keyboard.append([InlineKeyboardButton("перевод", callback_data="перевод")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Какой способ оплаты вам удобен?"
    await query.edit_message_text(text,reply_markup=reply_markup)
    return PAYMENT_CHOICE

async def payment_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['order_info'].payment=query.data
    keyboard =  [
            [KeyboardButton("отправить номер телефона", request_contact=True)],
            [KeyboardButton("другой номер")]
        ]
    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder="Нажмите")
    text = f"По какому номеру телефона с вами может свзаться оператор?"
    if query.data == "перевод":
        number_text2 = f"Вы можете сделать перевод на сбербанк по номеру телефона: [\+79138673700](tel:\+79138673700)"
        await query.edit_message_text(number_text2,parse_mode='MarkdownV2')
        await context.bot.send_message(chat_id=update.effective_user.id, text=text,parse_mode='MarkdownV2',reply_markup=reply_markup)
        return PHONE
    else:
        await query.delete_message()
        await context.bot.send_message(update.effective_user.id, text,reply_markup=reply_markup)
    return PHONE

async def choice_this_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
    context.user_data['order_info'].phone = update.message.contact.phone_number

    keyboard = [
        [InlineKeyboardButton('пожеланий нет',callback_data='no')]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f'Есть ли у вас еще пожелания к заказу или промокод?:', reply_markup=reply_markup)
    return WISHES


async def choice_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f'Укажите номер телефона для связи:')
    return NEW_NUMBER

async def choice_other_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
    text = update.message.text
    text = "".join(text.split())
    if not text.isdigit():
        await update.message.reply_text("Укажите телефон только цифрами")
        return NEW_NUMBER
    
    context.user_data['order_info'].phone = text
    keyboard = [
        [InlineKeyboardButton('пожеланий нет',callback_data="no")]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f'Есть ли у вас еще пожелания к заказу или промокод?:', reply_markup=reply_markup)
    return WISHES
    

async def wishes_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
    print("whishes_client",context.bot_data["chenal_id"])
    if update.message:
        text = update.message.text
        context.user_data['order_info'].wishes = text
    else:
        await update.callback_query.answer()

    text, total_price, total_quantity = reservation(context.bot_data,context.user_data)

    await context.bot.send_message(context.bot_data["chenal_id"],text=str(context.user_data['order_info'])+f'\n{text}',parse_mode="HTML")

    text_client = f'Ваш заказ принят, скоро с вами свяжется оператор для уточнения заказа.'
    reply_keyboard = [["Главное меню"], ["Корзина"], ["Информация о нас"]]
    await context.bot.send_message(update._effective_user.id, text_client, reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Нажмите меню"))
    
    del context.user_data['order_info']
    del context.user_data['cart']
    return ConversationHandler.END

async def information(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:  
    await update.message.reply_text(f"""Один дома - доставка еды домашней кухни. 
    Наш номер телефона: 8-906-954-30-00.
    Прием заказов: ПН - ВС с 11:00 до 21:00. 
    Бесплатная доставка от 500 рублей. 
    Наш сайт: https://odindoma-seversk.ru/.
    Наш инстаграм: @odin_doma_seversk""")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("")

async def update_menu(context: ContextTypes.DEFAULT_TYPE) -> None:
    print("update_menu")
    fl = FoodLoader(context.bot_data["document_id"], context.bot_data["cell_range"])
    fl.load_menu()
    if not fl.error:
        context.bot_data["menu"] = fl.menu
        print(context.bot_data["menu"])

  
def main() -> None:
    conf = load_config()
    TOKEN = conf["bot_token"]
    application = Application.builder().token(TOKEN).build()

    for key in conf:
        application.bot_data[key] = conf[key]


    job = application.job_queue.run_repeating(update_menu, interval=30*60, first=1)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Regex("Главное меню"), button_menu))
    application.add_handler(MessageHandler(filters.Regex("Информация о нас"), information))
    application.add_handler(MessageHandler(filters.Regex("Корзина"), cart))
    application.add_handler(CallbackQueryHandler(button_food, pattern="group_"))
    application.add_handler(CallbackQueryHandler(food_info, pattern="food_"))
    application.add_handler(CallbackQueryHandler(food_info, pattern="add_"))
    application.add_handler(CallbackQueryHandler(food_info, pattern="sub_"))
    application.add_handler(CallbackQueryHandler(button_menu, pattern="main_menu"))
    application.add_handler(CallbackQueryHandler(edit_cart, pattern="edit_cart"))
    application.add_handler(CallbackQueryHandler(clear_cart_callback, pattern="clear_cart"))
    application.add_handler(CallbackQueryHandler(cart, pattern="cart"))
    # application.add_handler(CallbackQueryHandler(order_placement, pattern="order"))

    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(delivery_address, pattern="order")],
        states={
            ADDRESS: [
                    MessageHandler(filters.TEXT | ~ filters.COMMAND, input_address)
                ],
            ORDER: [
                    CallbackQueryHandler(confirmation, pattern="delivery_time"), 
                    CallbackQueryHandler(number_of_people, pattern="near_furure")
                ],
            CONFIRM:[
                    MessageHandler(filters.TEXT | ~ filters.COMMAND, confirm_time)
                ],    
            PERSON: [
                    CallbackQueryHandler(number_of_people),
                    MessageHandler(filters.TEXT | ~ filters.COMMAND, input_number_of_people),
                  
                ],
            
            AVAILABLE_CULTERY:[
                CallbackQueryHandler(payment_method, pattern="да"),
                CallbackQueryHandler(payment_method, pattern="нет"),
            ],
            PAYMENT_CHOICE:[
                CallbackQueryHandler(payment_option),
            ],
            PHONE:[
                MessageHandler(filters.Regex("другой номер"), choice_phone),
                MessageHandler(filters.CONTACT, choice_this_phone),
            ],
            NEW_NUMBER:[
                MessageHandler(filters.TEXT | ~ filters.COMMAND, choice_other_phone)
            ],
            WISHES:[
                MessageHandler(filters.TEXT | ~ filters.COMMAND, wishes_client),
                CallbackQueryHandler(wishes_client),
            ],
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("help", help_command),],
        allow_reentry=True
        ))
    application.run_polling()


if __name__=="__main__":
    main()