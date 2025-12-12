from flask import Blueprint, jsonify, request
import json
import os

menu_api = Blueprint("menu_api", __name__)

MENU_FILE = "menu.json"
BACKEND_URL = "https://asiancafebackend.onrender.com/static/images/"

# ------------------- Инициализация меню -------------------
def init_menu():
    if not os.path.exists(MENU_FILE):
        menu_data = [
            {"id": 1, "name": "Классический рамен", "category": "Рамен", "price": 1800, "description": "Ароматный бульон, лапша, яйцо и зелень", "img": "ramen.png"},
            {"id": 2, "name": "Рамен с сыром", "category": "Рамен", "price": 2000, "description": "Добавь сыр и выбери уровень остроты", "img": "ramen_cheese.png"},
            {"id": 3, "name": "Острый рамен с говядиной", "category": "Рамен", "price": 2200, "description": "Пряный бульон и нежная говядина в фирменном соусе", "img": "ramen_beef.png"},
            {"id": 4, "name": "Филадельфия", "category": "Роллы", "price": 2400, "description": "Лосось, сливочный сыр, авокадо, рис, нори", "img": "roll_phila.png"},
            {"id": 5, "name": "Цезарь ролл", "category": "Роллы", "price": 2000, "description": "Курица, салат, пармезан, соус цезарь", "img": "roll_caesar.png"},
            {"id": 6, "name": "Калифорния", "category": "Роллы", "price": 2300, "description": "Крабовое мясо, огурец, авокадо, икра тобико", "img": "roll_california.png"},
            {"id": 7, "name": "Острый тунец", "category": "Роллы", "price": 2500, "description": "Тунец, острый соус, зелёный лук", "img": "roll_tuna.png"},
            {"id": 8, "name": "Кока-Кола", "category": "Напитки", "price": 500, "description": "Классическая Coca-Cola 0.33 л", "img": "cola.png"},
            {"id": 9, "name": "Кола Зеро", "category": "Напитки", "price": 500, "description": "Без сахара", "img": "cola_zero.png"},
            {"id": 10, "name": "Фанта", "category": "Напитки", "price": 500, "description": "Апельсиновая газировка 0.33 л", "img": "fanta.png"},
            {"id": 11, "name": "Молоко обычное", "category": "Напитки", "price": 400, "description": "Классическое молоко", "img": "milk_plain.png"},
            {"id": 12, "name": "Молоко клубничное", "category": "Напитки", "price": 450, "description": "Сладкое молоко с клубничным сиропом", "img": "milk_strawberry.png"},
            {"id": 13, "name": "Молоко банановое", "category": "Напитки", "price": 450, "description": "Молоко с банановым вкусом", "img": "milk_banana.png"},
            {"id": 14, "name": "Вода с газом", "category": "Напитки", "price": 300, "description": "Освежающая вода с пузырьками", "img": "water_sparkling.png"},
            {"id": 15, "name": "Вода без газа", "category": "Напитки", "price": 300, "description": "Чистая минеральная вода", "img": "water_still.png"},
            {"id": 16, "name": "Бабл-ти с орео", "category": "Бабл-ти", "price": 1500, "description": "Молочный чай с кусочками печенья орео", "img": "bubble_oreo.png"},
            {"id": 17, "name": "Матча бабл-ти", "category": "Бабл-ти", "price": 1600, "description": "Матча с молоком и тапиокой", "img": "bubble_matcha.png"},
            {"id": 18, "name": "Клубничный бабл-ти", "category": "Бабл-ти", "price": 1500, "description": "Клубничный сироп и тапиока", "img": "bubble_strawberry.png"},
            {"id": 19, "name": "Моти с клубникой", "category": "Десерты", "price": 800, "description": "Рисовое пирожное с клубничной начинкой", "img": "mochi_strawberry.png"},
            {"id": 20, "name": "Моти с орео", "category": "Десерты", "price": 850, "description": "Моти с кремом и печеньем орео", "img": "mochi_oreo.png"},
            {"id": 21, "name": "Моти с голубикой", "category": "Десерты", "price": 850, "description": "Моти с голубичной начинкой", "img": "mochi_blueberry.png"},
            {"id": 22, "name": "Японский чизкейк", "category": "Десерты", "price": 1200, "description": "Лёгкий воздушный десерт с нежным сливочным вкусом", "img": "cheesecake.png"}
        ]
        with open(MENU_FILE, "w", encoding="utf-8") as f:
            json.dump(menu_data, f, ensure_ascii=False, indent=4)

# ------------------- Получить всё меню (группами) -------------------
@menu_api.route("/api/menu", methods=["GET"])
def get_menu():
    if not os.path.exists(MENU_FILE):
        init_menu()

    with open(MENU_FILE, "r", encoding="utf-8") as f:
        menu_data = json.load(f)

    result = []
    for category in menu_data:
        category_name = category["category"]
        items = []

        for dish in category["items"]:
            items.append({
                "name": dish["name"],
                "price": dish["price"],
                "desc": dish["desc"],
                "img": f"{BACKEND_URL}{dish['img']}"
            })

        result.append({
            "category": category_name,
            "items": items
        })

    return jsonify(result)

