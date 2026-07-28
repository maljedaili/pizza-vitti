from django.core.management.base import BaseCommand
from django.db.models import Q

from shop.models import Category, CategoryTranslation, Product


CATEGORY_DATA = [
    ('caffe-the', 'Café', 'Un espresso italien court, intense et aromatique.', 'cafe.webp', ('Café',)),
    ('cafe-allonge', 'Café allongé', 'Un café plus long, équilibré et délicatement corsé.', 'cafe-allonge.webp', ('Café allongé',)),
    ('cafe-double', 'Café double', 'Deux doses d’espresso pour une dégustation plus intense.', 'cafe-double.webp', ('Café double',)),
    ('cappuccino', 'Cappuccino', 'Espresso et mousse de lait onctueuse dans la tradition italienne.', 'cappuccino.webp', ('Cappuccino',)),
    ('chocolat-chaud', 'Chocolat chaud', 'Un chocolat chaud crémeux et gourmand.', 'chocolat-chaud.webp', ('Chocolat chaud',)),
    ('thes-et-infusions', 'Thés et infusions', 'Une sélection réconfortante de thés et plantes infusées.', 'thes-infusions.webp', ('Thés et Infusions', 'Thés et infusions')),
    ('carte-des-vins-rouges', 'Carte des vins – rouges', 'Vins rouges italiens et sélection de la maison.', 'vins-rouges.webp', ()),
    ('carte-des-vins-blancs', 'Carte des vins – blancs', 'Vins blancs frais et élégants pour accompagner votre repas.', 'vins-blancs.webp', ()),
    ('carte-des-vins-roses', 'Carte des vins – rosés', 'Rosés lumineux et délicats servis frais.', 'vins-roses.webp', ()),
    ('carte-des-vins-petillants', 'Carte des vins – pétillants', 'Prosecco, Moscato et bulles italiennes.', 'vins-petillants.webp', ()),
    ('aperitivo', 'Apéritivo', 'Les grands classiques de l’apéritif à l’italienne.', 'aperitivo.webp', ()),
    ('vins-deliveroo', 'Vins', 'Une sélection de bouteilles italiennes choisies par Pizza Vitti.', 'vins.webp', ()),
    ('analcolici', 'Boissons', 'Eaux, sodas, jus et bières servis bien frais.', 'boissons.webp', ('Peroni 33cl', 'Moretti 33cl')),
    ('digestifs', 'Digestifs', 'Limoncello, grappa et liqueurs pour terminer le repas.', 'digestifs.webp', ()),
]

TRANSLATED_NAMES = {
    'en': ['Coffee', 'Long coffee', 'Double espresso', 'Cappuccino', 'Hot chocolate', 'Teas & infusions', 'Wine list – reds', 'Wine list – whites', 'Wine list – rosés', 'Wine list – sparkling', 'Aperitivo', 'Wines', 'Drinks', 'Digestifs'],
    'es': ['Café', 'Café largo', 'Café doble', 'Capuchino', 'Chocolate caliente', 'Tés e infusiones', 'Carta de vinos – tintos', 'Carta de vinos – blancos', 'Carta de vinos – rosados', 'Carta de vinos – espumosos', 'Aperitivo', 'Vinos', 'Bebidas', 'Digestivos'],
    'it': ['Caffè', 'Caffè lungo', 'Caffè doppio', 'Cappuccino', 'Cioccolata calda', 'Tè e infusi', 'Carta dei vini – rossi', 'Carta dei vini – bianchi', 'Carta dei vini – rosati', 'Carta dei vini – spumanti', 'Aperitivo', 'Vini', 'Bevande', 'Digestivi'],
    'pt': ['Café', 'Café longo', 'Café duplo', 'Cappuccino', 'Chocolate quente', 'Chás e infusões', 'Carta de vinhos – tintos', 'Carta de vinhos – brancos', 'Carta de vinhos – rosés', 'Carta de vinhos – espumantes', 'Aperitivo', 'Vinhos', 'Bebidas', 'Digestivos'],
    'nl': ['Koffie', 'Lange koffie', 'Dubbele espresso', 'Cappuccino', 'Warme chocolademelk', 'Thee en infusies', 'Wijnkaart – rood', 'Wijnkaart – wit', 'Wijnkaart – rosé', 'Wijnkaart – mousserend', 'Aperitivo', 'Wijnen', 'Dranken', 'Digestieven'],
    'zh': ['咖啡', '长咖啡', '双份浓缩咖啡', '卡布奇诺', '热巧克力', '茶与花草茶', '葡萄酒单－红葡萄酒', '葡萄酒单－白葡萄酒', '葡萄酒单－桃红葡萄酒', '葡萄酒单－起泡酒', '开胃酒', '葡萄酒', '饮品', '餐后酒'],
    'ja': ['コーヒー', 'ロングコーヒー', 'ダブルエスプレッソ', 'カプチーノ', 'ホットチョコレート', '紅茶・ハーブティー', 'ワインリスト－赤', 'ワインリスト－白', 'ワインリスト－ロゼ', 'ワインリスト－スパークリング', 'アペリティーボ', 'ワイン', 'ドリンク', '食後酒'],
    'ar': ['قهوة', 'قهوة طويلة', 'إسبريسو مزدوج', 'كابتشينو', 'شوكولاتة ساخنة', 'شاي ومنقوعات', 'قائمة النبيذ – أحمر', 'قائمة النبيذ – أبيض', 'قائمة النبيذ – وردي', 'قائمة النبيذ – فوّار', 'مقبلات إيطالية', 'نبيذ', 'مشروبات', 'مشروبات هاضمة'],
}


class Command(BaseCommand):
    help = 'Prepare the editable premium drinks page and map existing products safely.'

    def handle(self, *args, **options):
        categories = []
        for index, (slug, name, description, filename, product_names) in enumerate(CATEGORY_DATA):
            if slug == 'caffe-the':
                category = Category.objects.filter(slug=slug).first()
                if category is None:
                    category = Category(slug=slug)
            else:
                category = Category.objects.filter(slug=slug).first() or Category(slug=slug)
            category.name = name
            category.description = description
            category.order = 100 + index
            category.is_active = True
            category.static_image_path = f'/static/shop/img/drinks/{filename}'
            category.save()
            categories.append(category)

            if product_names:
                Product.objects.filter(name__in=product_names).update(
                    category=category,
                    external_image=(
                        '/static/shop/img/products/deliveroo-beers.webp'
                        if slug == 'analcolici'
                        else category.static_image_path
                    ),
                )
            Product.objects.filter(category=category).filter(
                Q(external_image='') | Q(external_image__contains='images.unsplash.com')
            ).update(external_image=category.static_image_path)

        for language, names in TRANSLATED_NAMES.items():
            for category, translated_name in zip(categories, names):
                CategoryTranslation.objects.update_or_create(
                    category=category,
                    language=language,
                    defaults={
                        'name': translated_name,
                        'description': category.description,
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            f'Prepared {len(categories)} drinks categories with local images and translations.'
        ))
