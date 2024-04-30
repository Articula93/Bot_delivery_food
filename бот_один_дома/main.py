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
from  constants_list import*
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
        {ID_USER} {self.user_id}
        {ADDRESS} {self.address}
        {TIME_DELIVERY} {self.time if self.time!=None else FASTER}
        {COUNT_PERSON} {self.number_person}
        {TABLEWARE} {self.cultery}
        {PAYMENT} {self.payment}
        {NUMBER_PHONE} {self.phone}
        {WHISHER} {self.wishes if self.wishes!=None else NO_PROMOCODE}"""


def get_food_by_id(storage, food_id):
    return storage.get(MENU,{}).get(food_id,None)

def get_food_by_query_data(storage, food_group, food_id):
    menu = storage.get(MENU,{})
    food_id = int(food_id)
    food = None
    list_food = menu.get(food_group,[])
    for item in list_food:
        if item.id == food_id:
            food = item
    return food

def get_quantity_from_cart(storage, food_id):
    return storage.get(CART,{}).get(food_id,0)

def change_quantity_from_cart(storage, food_id, valeu):
    cart = storage.get(CART,{})
    cart[food_id]=valeu
    storage[CART] = cart

def get_food_id_and_quantity_from_cart(storage):
    cart = storage.get(CART,{})
    return list(cart.items()) #[(1,2),(2,4)]

def clear_cart(storage):
    storage[CART] = {}

def add_deleted_msg(storage, msg):
    if DELETE_MSG not in storage:
        storage[DELETE_MSG]=[]

    print(storage[DELETE_MSG])
    storage[DELETE_MSG].append(msg)


async def delete_old_msg(storage):
    for msg in storage.get(DELETE_MSG,[]):
        await msg.delete()
    storage[DELETE_MSG]=[]

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
    reply_keyboard = [[CHIEF_MENU], [BASKET], [COMPANY_INFORMATION ]]
    await update.message.reply_text(text = CHECKOUT, reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder=CLICK_MENU))
    

async def button_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = []
    for item in context.bot_data[MENU]:
        if type(item)!=int:
            keyboard.append([InlineKeyboardButton(item, callback_data="group_"+item)])
    keyboard.append([InlineKeyboardButton(BASKET,callback_data=CART)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(CLICK_HERE, reply_markup=reply_markup)
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(CLICK_HERE, reply_markup=reply_markup)


async def button_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    food_group = query.data.split("_",1)[-1]#group_суп [group, суп] \ group_салат [group, салат] \ group_кофе_чай [group, кофе_чай]
    list_food = context.bot_data[MENU][food_group]
    keyboard = []
    for item in list_food:
        keyboard.append([InlineKeyboardButton(item.name,callback_data=f'food_{food_group}_{item.id}')])

    keyboard.append([InlineKeyboardButton(IN_MAIN_MENU,callback_data=f"{MAIN_MENU}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(SELECT_POSITION, reply_markup=reply_markup)


async def food_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action, food_group, food_id = query.data.split("_",2) 
    food = get_food_by_query_data(context.bot_data, food_group, food_id)

    if not food:
        await query.edit_message_text(f"{TRY_AGAIN}")
    else:
        quantity = get_quantity_from_cart(context.user_data, food_id)
        if action=="add":
            quantity+=1
        elif action=="sub" and quantity>0:
            quantity-=1

        change_quantity_from_cart(context.user_data, food_id, quantity)
        keyboard = []
        if quantity>0:
            keyboard.append([InlineKeyboardButton(UN_CART,callback_data=f'sub_{food_group}_{food_id}')])#sub_суп_1
        keyboard.append([InlineKeyboardButton(ADD_CART,callback_data=f'add_{food_group}_{food_id}')])#add_суп_1
        keyboard.append([InlineKeyboardButton(IN_MAIN_MENU,callback_data=f"{MAIN_MENU}")])
        keyboard.append([InlineKeyboardButton(GO_TO_CART,callback_data=f"{CART}")])
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
            [InlineKeyboardButton(PURGE, callback_data=CLEAR_CART)],
            [InlineKeyboardButton(EDIT, callback_data=EDIT_CART)],
            [InlineKeyboardButton(PLACE_ORDER,callback_data=ORDER)],
            [InlineKeyboardButton(IN_MAIN_MENU,callback_data=MAIN_MENU)]
        ]
    else:
        text = EMPTY_CART
        keyboard = [
            [InlineKeyboardButton(IN_MAIN_MENU,callback_data=MAIN_MENU)]
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
        [InlineKeyboardButton(IN_MAIN_MENU,callback_data=MAIN_MENU)]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = CART_CLEARD
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
                keyboard.append([InlineKeyboardButton(UN_CART,callback_data=f'sub_{food.type}_{food.id}')])#sub_суп_1
            keyboard.append([InlineKeyboardButton(ADD_CART,callback_data=f'add_{food.type}_{food.id}')])#add_суп_1
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
    await context.bot.send_message(update.effective_user.id, text = DELIVERY_ADDRESS)
    return ADDRESS

async def input_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    address_name = update.message.text
    context.user_data[ORDER_INFO] = OrderInfo(update.effective_user.id)
    context.user_data[ORDER_INFO].address = address_name
    keyboard = []
    keyboard.append([InlineKeyboardButton(DELIVERY_IN_TIME, callback_data=DELIVERY_TIME)])
    keyboard.append([InlineKeyboardButton(DELIVERY_FASTER, callback_data=NEAR_FUTURE)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=SELECT_TIME_DELIVERY, reply_markup=reply_markup)
    return ORDER

async def confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"{SPECIFY_TIME_DELIVERY}")
    return CONFIRM

async def confirm_time(update: Update, context: ContextTypes.DEFAULT_TYPE)-> int:
    text = update.message.text
    text = "".join(text.split())
    time = text.split(":")
    if len(time)!=2:
        await update.message.reply_text(SPECIFY_TIME_DELIVERY)
        return CONFIRM
    hh = int(time[0])
    mm = int(time[1])
    if not(hh>=0 and hh<=23 and mm>=0 and mm<=59):
        await update.message.reply_text(CHECK_INPUT_TIME)
        return CONFIRM
    context.user_data[ORDER_INFO].time = f"{hh:02}:{mm:02}"
    await update.message.reply_text(INDICATE_COUNT_PERSON)
    return PERSON
    

async def number_of_people(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"{INDICATE_COUNT_PERSON}")
    return PERSON

async def input_number_of_people(update: Update, context: ContextTypes.DEFAULT_TYPE)-> int:
    text = update.message.text
    text = "".join(text.split())
    if not text.isdigit():
        await update.message.reply_text(CHECK_DIGIT)
        return PERSON
    number = int(text)
    context.user_data[ORDER_INFO].number_person = number
    keyboard = []
    keyboard.append([InlineKeyboardButton(YES, callback_data=YES)])
    keyboard.append([InlineKeyboardButton(NO, callback_data=NO)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = NEED_TABLEWARE
    await update.message.reply_text(text,reply_markup=reply_markup)
    return AVAILABLE_CULTERY

async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data[ORDER_INFO].cultery=query.data
    keyboard = []
    keyboard.append([InlineKeyboardButton(CARD, callback_data=CARD)])
    keyboard.append([InlineKeyboardButton(CASH, callback_data=CASH)])
    keyboard.append([InlineKeyboardButton(TRANSFER, callback_data=TRANSFER)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = QUESTION_PAYMENT
    await query.edit_message_text(text,reply_markup=reply_markup)
    return PAYMENT_CHOICE

async def payment_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data[ORDER_INFO].payment=query.data
    keyboard =  [
            [KeyboardButton(SEND_PHONE, request_contact=True)],
            [KeyboardButton(ANOTHER_NUMBER)]
        ]
    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder=CLICK)
    text = f"{WHAT_PHONE_NUMBER}"
    if query.data == TRANSFER:
        number_text2 = f"{TRANSFER_PHONE}"
        await query.edit_message_text(number_text2,parse_mode=MODE_PHONE)
        await context.bot.send_message(chat_id=update.effective_user.id, text=text,parse_mode=MODE_PHONE,reply_markup=reply_markup)
        return PHONE
    else:
        await query.delete_message()
        await context.bot.send_message(update.effective_user.id, text,reply_markup=reply_markup)
    return PHONE

async def choice_this_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
    context.user_data[ORDER_INFO].phone = update.message.contact.phone_number

    keyboard = [
        [InlineKeyboardButton(NO_WHISHER,callback_data='no')]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"{NOT_PROMOCODE}", reply_markup=reply_markup)
    return WISHES


async def choice_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f"{INDICATE_NUMBER_PHONE}")
    return NEW_NUMBER

async def choice_other_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
    text = update.message.text
    text = "".join(text.split())
    if not text.isdigit():
        await update.message.reply_text(PHONE_DIGIT)
        return NEW_NUMBER
    
    context.user_data[ORDER_INFO].phone = text
    keyboard = [
        [InlineKeyboardButton(NO_WHISHER,callback_data="no")]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"{NOT_PROMOCODE}", reply_markup=reply_markup)
    return WISHES
    

async def wishes_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
    print("whishes_client",context.bot_data["chenal_id"])
    if update.message:
        text = update.message.text
        context.user_data[ORDER_INFO].wishes = text
    else:
        await update.callback_query.answer()

    text, total_price, total_quantity = reservation(context.bot_data,context.user_data)

    await context.bot.send_message(context.bot_data["chenal_id"],text=str(context.user_data[ORDER_INFO])+f'\n{text}',parse_mode="HTML")

    text_client = f"{ORDER_ACCEPTED}"
    reply_keyboard = [[CHIEF_MENU], [BASKET], [COMPANY_INFORMATION ]]
    await context.bot.send_message(update._effective_user.id, text_client, reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder=CLICK_MENU))
    
    del context.user_data[ORDER_INFO]
    del context.user_data[CART]
    return ConversationHandler.END

async def information(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:  
    await update.message.reply_text(f"{INFO_COMPANY}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("")

async def update_menu(context: ContextTypes.DEFAULT_TYPE) -> None:
    print("update_menu")
    fl = FoodLoader(context.bot_data["document_id"], context.bot_data["cell_range"])
    fl.load_menu()
    if not fl.error:
        context.bot_data[MENU] = fl.menu
        print(context.bot_data[MENU])

  
def main() -> None:
    conf = load_config()
    TOKEN = conf["bot_token"]
    application = Application.builder().token(TOKEN).build()

    for key in conf:
        application.bot_data[key] = conf[key]


    job = application.job_queue.run_repeating(update_menu, interval=30*60, first=1)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Regex(CHIEF_MENU), button_menu))
    application.add_handler(MessageHandler(filters.Regex(COMPANY_INFORMATION ), information))
    application.add_handler(MessageHandler(filters.Regex(BASKET), cart))
    application.add_handler(CallbackQueryHandler(button_food, pattern="group_"))
    application.add_handler(CallbackQueryHandler(food_info, pattern="food_"))
    application.add_handler(CallbackQueryHandler(food_info, pattern="add_"))
    application.add_handler(CallbackQueryHandler(food_info, pattern="sub_"))
    application.add_handler(CallbackQueryHandler(button_menu, pattern=MAIN_MENU))
    application.add_handler(CallbackQueryHandler(edit_cart, pattern=EDIT_CART))
    application.add_handler(CallbackQueryHandler(clear_cart_callback, pattern=CLEAR_CART))
    application.add_handler(CallbackQueryHandler(cart, pattern=CART))
    # application.add_handler(CallbackQueryHandler(order_placement, pattern="order"))

    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(delivery_address, pattern=ORDER)],
        states={
            ADDRESS: [
                    MessageHandler(filters.TEXT | ~ filters.COMMAND, input_address)
                ],
            ORDER: [
                    CallbackQueryHandler(confirmation, pattern=DELIVERY_TIME), 
                    CallbackQueryHandler(number_of_people, pattern=NEAR_FUTURE)
                ],
            CONFIRM:[
                    MessageHandler(filters.TEXT | ~ filters.COMMAND, confirm_time)
                ],    
            PERSON: [
                    CallbackQueryHandler(number_of_people),
                    MessageHandler(filters.TEXT | ~ filters.COMMAND, input_number_of_people),
                  
                ],
            
            AVAILABLE_CULTERY:[
                CallbackQueryHandler(payment_method, pattern=YES),
                CallbackQueryHandler(payment_method, pattern=NO),
            ],
            PAYMENT_CHOICE:[
                CallbackQueryHandler(payment_option),
            ],
            PHONE:[
                MessageHandler(filters.Regex(ANOTHER_NUMBER), choice_phone),
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