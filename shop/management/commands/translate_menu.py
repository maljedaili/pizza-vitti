from django.core.management.base import BaseCommand
from shop.models import Category, Product, CategoryTranslation, ProductTranslation

LANGS = ['en','es','it','pt','nl','zh','ja','ar']
CATEGORY_NAMES = {
    'Nos Pizza': {'en':'Our Pizzas','es':'Nuestras Pizzas','it':'Le Nostre Pizze','pt':'Nossas Pizzas','nl':'Onze Pizza’s','zh':'我们的披萨','ja':'ピザ','ar':'البيتزا'},
    'Nos Pizzas': {'en':'Our Pizzas','es':'Nuestras Pizzas','it':'Le Nostre Pizze','pt':'Nossas Pizzas','nl':'Onze Pizza’s','zh':'我们的披萨','ja':'ピザ','ar':'البيتزا'},
    'Nos Pastas': {'en':'Our Pastas','es':'Nuestras Pastas','it':'Le Nostre Paste','pt':'Nossas Massas','nl':'Onze Pasta’s','zh':'我们的意面','ja':'パスタ','ar':'الباستا'},
    'Nos Pasta': {'en':'Our Pasta','es':'Nuestra Pasta','it':'La Nostra Pasta','pt':'Nossa Massa','nl':'Onze Pasta','zh':'我们的意面','ja':'パスタ','ar':'الباستا'},
    'Nos douceurs': {'en':'Desserts','es':'Postres','it':'Dolci','pt':'Sobremesas','nl':'Desserts','zh':'甜点','ja':'デザート','ar':'الحلويات'},
    'Nos Salades': {'en':'Salads','es':'Ensaladas','it':'Insalate','pt':'Saladas','nl':'Salades','zh':'沙拉','ja':'サラダ','ar':'السلطات'},
    'Menu Bambino': {'en':'Kids Menu','es':'Menú Infantil','it':'Menu Bambino','pt':'Menu Infantil','nl':'Kindermenu','zh':'儿童菜单','ja':'キッズメニュー','ar':'قائمة الأطفال'},
    'Suppléments pizza': {'en':'Pizza Extras','es':'Extras de Pizza','it':'Supplementi Pizza','pt':'Extras de Pizza','nl':'Pizza Extra’s','zh':'披萨加料','ja':'ピザ追加トッピング','ar':'إضافات البيتزا'},
}

PHRASES = {
'en': [('Sauce tomate','Tomato sauce'),('mozzarella fior di latte','fior di latte mozzarella'),('tomates cerise','cherry tomatoes'),('olives','olives'),('basilic','basil'),('jambon blanc cuit aux herbes','herb cooked ham'),('champignons','mushrooms'),('origan','oregano'),('Crème fraîche','fresh cream'),('oignons rouges','red onions'),('piments doux','sweet peppers'),('olives noires','black olives'),('œuf','egg'),('parmesan','parmesan'),('roquette','arugula'),('burrata fraîche','fresh burrata'),('copeaux de parmesan','parmesan shavings'),('Saumon frais','fresh salmon'),('Dessert italien au mascarpone et café','Italian mascarpone and coffee dessert'),('Viande de bœuf','beef'),('sauce tomate','tomato sauce'),('pignons grillés','toasted pine nuts'),('Lasagnes maison du chef','Chef’s homemade lasagna')],
'es': [('Sauce tomate','Salsa de tomate'),('mozzarella fior di latte','mozzarella fior di latte'),('tomates cerise','tomates cherry'),('olives','aceitunas'),('basilic','albahaca'),('jambon blanc cuit aux herbes','jamón cocido con hierbas'),('champignons','champiñones'),('origan','orégano'),('Crème fraîche','crema fresca'),('oignons rouges','cebollas rojas'),('piments doux','pimientos dulces'),('olives noires','aceitunas negras'),('œuf','huevo'),('parmesan','parmesano'),('roquette','rúcula'),('burrata fraîche','burrata fresca'),('copeaux de parmesan','lascas de parmesano'),('Saumon frais','salmón fresco'),('Dessert italien au mascarpone et café','postre italiano de mascarpone y café'),('Viande de bœuf','carne de ternera'),('sauce tomate','salsa de tomate'),('pignons grillés','piñones tostados'),('Lasagnes maison du chef','lasaña casera del chef')],
'it': [('Sauce tomate','Salsa di pomodoro'),('tomates cerise','pomodorini'),('olives','olive'),('basilic','basilico'),('jambon blanc cuit aux herbes','prosciutto cotto alle erbe'),('champignons','funghi'),('origan','origano'),('Crème fraîche','panna fresca'),('oignons rouges','cipolle rosse'),('piments doux','peperoni dolci'),('olives noires','olive nere'),('œuf','uovo'),('roquette','rucola'),('burrata fraîche','burrata fresca'),('copeaux de parmesan','scaglie di parmigiano'),('Saumon frais','salmone fresco'),('Dessert italien au mascarpone et café','dolce italiano con mascarpone e caffè'),('Viande de bœuf','carne di manzo'),('sauce tomate','salsa di pomodoro'),('pignons grillés','pinoli tostati'),('Lasagnes maison du chef','lasagne fatte in casa dello chef')],
'pt': [('Sauce tomate','Molho de tomate'),('tomates cerise','tomates-cereja'),('olives','azeitonas'),('basilic','manjericão'),('jambon blanc cuit aux herbes','fiambre cozido com ervas'),('champignons','cogumelos'),('origan','orégano'),('Crème fraîche','natas frescas'),('oignons rouges','cebolas roxas'),('piments doux','pimentos doces'),('olives noires','azeitonas pretas'),('œuf','ovo'),('parmesan','parmesão'),('roquette','rúcula'),('burrata fraîche','burrata fresca'),('copeaux de parmesan','lascas de parmesão'),('Saumon frais','salmão fresco'),('Dessert italien au mascarpone et café','sobremesa italiana com mascarpone e café'),('Viande de bœuf','carne de vaca'),('sauce tomate','molho de tomate'),('pignons grillés','pinhões tostados'),('Lasagnes maison du chef','lasanha caseira do chef')],
'nl': [('Sauce tomate','Tomatensaus'),('tomates cerise','cherrytomaten'),('olives','olijven'),('basilic','basilicum'),('jambon blanc cuit aux herbes','gekookte ham met kruiden'),('champignons','champignons'),('origan','oregano'),('Crème fraîche','crème fraîche'),('oignons rouges','rode uien'),('piments doux','zoete pepers'),('olives noires','zwarte olijven'),('œuf','ei'),('parmesan','parmezaan'),('roquette','rucola'),('burrata fraîche','verse burrata'),('copeaux de parmesan','parmezaanschilfers'),('Saumon frais','verse zalm'),('Dessert italien au mascarpone et café','Italiaans dessert met mascarpone en koffie'),('Viande de bœuf','rundvlees'),('sauce tomate','tomatensaus'),('pignons grillés','geroosterde pijnboompitten'),('Lasagnes maison du chef','huisgemaakte lasagne van de chef')],
'zh': [('Sauce tomate','番茄酱'),('mozzarella fior di latte','鲜奶马苏里拉'),('tomates cerise','樱桃番茄'),('olives','橄榄'),('basilic','罗勒'),('jambon blanc cuit aux herbes','香草熟火腿'),('champignons','蘑菇'),('origan','牛至'),('Crème fraîche','鲜奶油'),('oignons rouges','红洋葱'),('piments doux','甜椒'),('olives noires','黑橄榄'),('œuf','鸡蛋'),('parmesan','帕尔马干酪'),('roquette','芝麻菜'),('burrata fraîche','新鲜布拉塔'),('copeaux de parmesan','帕尔马干酪片'),('Saumon frais','新鲜三文鱼'),('Dessert italien au mascarpone et café','马斯卡彭咖啡意式甜点'),('Viande de bœuf','牛肉'),('sauce tomate','番茄酱'),('pignons grillés','烤松子'),('Lasagnes maison du chef','主厨自制千层面')],
'ja': [('Sauce tomate','トマトソース'),('mozzarella fior di latte','フィオール・ディ・ラッテ・モッツァレラ'),('tomates cerise','チェリートマト'),('olives','オリーブ'),('basilic','バジル'),('jambon blanc cuit aux herbes','ハーブ入りハム'),('champignons','マッシュルーム'),('origan','オレガノ'),('Crème fraîche','クレームフレッシュ'),('oignons rouges','赤玉ねぎ'),('piments doux','甘唐辛子'),('olives noires','ブラックオリーブ'),('œuf','卵'),('parmesan','パルメザン'),('roquette','ルッコラ'),('burrata fraîche','フレッシュブッラータ'),('copeaux de parmesan','パルメザンチーズスライス'),('Saumon frais','新鮮なサーモン'),('Dessert italien au mascarpone et café','マスカルポーネとコーヒーのイタリアンデザート'),('Viande de bœuf','牛肉'),('sauce tomate','トマトソース'),('pignons grillés','ロースト松の実'),('Lasagnes maison du chef','シェフ特製ラザニア')],
'ar': [('Sauce tomate','صلصة الطماطم'),('mozzarella fior di latte','موزاريلا فيور دي لاتيه'),('tomates cerise','طماطم كرزية'),('olives','زيتون'),('basilic','ريحان'),('jambon blanc cuit aux herbes','لحم مطبوخ بالأعشاب'),('champignons','فطر'),('origan','أوريغانو'),('Crème fraîche','كريمة طازجة'),('oignons rouges','بصل أحمر'),('piments doux','فلفل حلو'),('olives noires','زيتون أسود'),('œuf','بيض'),('parmesan','بارميزان'),('roquette','جرجير'),('burrata fraîche','بوراتا طازجة'),('copeaux de parmesan','رقائق بارميزان'),('Saumon frais','سلمون طازج'),('Dessert italien au mascarpone et café','حلوى إيطالية بالماسكاربوني والقهوة'),('Viande de bœuf','لحم بقري'),('sauce tomate','صلصة الطماطم'),('pignons grillés','صنوبر محمص'),('Lasagnes maison du chef','لازانيا منزلية من الشيف')],
}

PREFIX = {
'en': [('La ','The '),('Le ','The '),('Les ','The '),('Nos ','Our ')],
'es': [('La ','La '),('Le ','El '),('Les ','Los '),('Nos ','Nuestras ')],
'it': [('La ','La '),('Le ','Le '),('Les ','I '),('Nos ','Le nostre ')],
'pt': [('La ','A '),('Le ','O '),('Les ','Os '),('Nos ','Nossas ')],
'nl': [('La ','De '),('Le ','De '),('Les ','De '),('Nos ','Onze ')],
'zh': [('La ',''),('Le ',''),('Les ',''),('Nos ','我们的')],
'ja': [('La ',''),('Le ',''),('Les ',''),('Nos ','私たちの')],
'ar': [('La ',''),('Le ',''),('Les ',''),('Nos ','')],
}

def tr_name(name, lang):
    base = name
    replacements = {
        'La Margherita': {'en':'Margherita Pizza','es':'Pizza Margherita','it':'Pizza Margherita','pt':'Pizza Margherita','nl':'Pizza Margherita','zh':'玛格丽塔披萨','ja':'マルゲリータピザ','ar':'بيتزا مارغريتا'},
        'La Regina': {'en':'Regina Pizza','es':'Pizza Regina','it':'Pizza Regina','pt':'Pizza Regina','nl':'Pizza Regina','zh':'雷吉娜披萨','ja':'レジーナピザ','ar':'بيتزا ريجينا'},
        'La Quattro fromaggi': {'en':'Four Cheese Pizza','es':'Pizza Cuatro Quesos','it':'Pizza Quattro Formaggi','pt':'Pizza Quatro Queijos','nl':'Vierkazenpizza','zh':'四奶酪披萨','ja':'4種チーズピザ','ar':'بيتزا الأجبان الأربعة'},
        'La Calzone': {'en':'Calzone','es':'Calzone','it':'Calzone','pt':'Calzone','nl':'Calzone','zh':'卡尔佐内','ja':'カルツォーネ','ar':'كالزوني'},
        'Spaghetti à la Carbonara': {'en':'Spaghetti Carbonara','es':'Espaguetis Carbonara','it':'Spaghetti alla Carbonara','pt':'Esparguete Carbonara','nl':'Spaghetti Carbonara','zh':'培根蛋酱意面','ja':'スパゲッティ・カルボナーラ','ar':'سباغيتي كاربونارا'},
        'Spaghetti à la Bolognaise': {'en':'Spaghetti Bolognese','es':'Espaguetis Boloñesa','it':'Spaghetti alla Bolognese','pt':'Esparguete à Bolonhesa','nl':'Spaghetti Bolognese','zh':'肉酱意面','ja':'スパゲッティ・ボロネーゼ','ar':'سباغيتي بولونيز'},
        'Tiramisu': {'en':'Tiramisu','es':'Tiramisú','it':'Tiramisù','pt':'Tiramisù','nl':'Tiramisu','zh':'提拉米苏','ja':'ティラミス','ar':'تيراميسو'},
    }
    if name in replacements:
        return replacements[name][lang]
    for old, new in PREFIX.get(lang, []):
        if base.startswith(old):
            base = new + base[len(old):]
            break
    return base

def tr_desc(text, lang):
    out = text
    for old, new in PHRASES.get(lang, []):
        out = out.replace(old, new)
    return out

class Command(BaseCommand):
    help = 'Create / update Pizza Vitti menu translations in the 9 site languages.'
    def handle(self, *args, **kwargs):
        total = 0
        for category in Category.objects.all():
            for lang in LANGS:
                name = CATEGORY_NAMES.get(category.name, {}).get(lang, category.name)
                CategoryTranslation.objects.update_or_create(category=category, language=lang, defaults={'name': name, 'description': tr_desc(category.description, lang)})
                total += 1
        for product in Product.objects.all():
            for lang in LANGS:
                ProductTranslation.objects.update_or_create(product=product, language=lang, defaults={'name': tr_name(product.name, lang), 'description': tr_desc(product.description, lang)})
                total += 1
        self.stdout.write(self.style.SUCCESS(f'Created/updated {total} menu translations for EN, ES, IT, PT, NL, ZH, JA, AR. French remains original.'))
