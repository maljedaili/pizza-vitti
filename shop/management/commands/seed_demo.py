from django.core.management.base import BaseCommand
from django.utils.text import slugify
from shop.models import Category, Product, BlogPost, Review, GalleryImage

# Menu taken from NEW menu VITTI.pdf (10 pages).
# Stable, real food/drink photos are used instead of source.unsplash.com random search URLs.

PHOTO_BANK = {
    'pizza': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=900&q=80',
    'margherita': 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=900&q=80',
    'calzone': 'https://images.unsplash.com/photo-1601924582970-9238bcb495d9?auto=format&fit=crop&w=900&q=80',
    'pasta': 'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?auto=format&fit=crop&w=900&q=80',
    'carbonara': 'https://images.unsplash.com/photo-1612874742237-6526221588e3?auto=format&fit=crop&w=900&q=80',
    'bolognaise': 'https://images.unsplash.com/photo-1551892374-ecf8754cf8b0?auto=format&fit=crop&w=900&q=80',
    'arrabiata': 'https://images.unsplash.com/photo-1563379926898-05f4575a45d8?auto=format&fit=crop&w=900&q=80',
    'gnocchi': 'https://images.unsplash.com/photo-1587740908075-9e245070dfaa?auto=format&fit=crop&w=900&q=80',
    'lasagnes': 'https://images.unsplash.com/photo-1574894709920-11b28e7367e3?auto=format&fit=crop&w=900&q=80',
    'ravioles': 'https://images.unsplash.com/photo-1587740908075-9e245070dfaa?auto=format&fit=crop&w=900&q=80',
    'bruschetta': 'https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?auto=format&fit=crop&w=900&q=80',
    'salade': 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80',
    'tartare': 'https://images.unsplash.com/photo-1604909052743-94e838986d24?auto=format&fit=crop&w=900&q=80',
    'antipasti': 'https://images.unsplash.com/photo-1546549032-9571cd6b27df?auto=format&fit=crop&w=900&q=80',
    'charcuterie': 'https://images.unsplash.com/photo-1625944230945-1b7dd3b949ab?auto=format&fit=crop&w=900&q=80',
    'burrata': 'https://images.unsplash.com/photo-1608897013039-887f21d8c804?auto=format&fit=crop&w=900&q=80',
    'caprese': 'https://images.unsplash.com/photo-1592417817038-d13fd7342605?auto=format&fit=crop&w=900&q=80',
    'aubergines': 'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=900&q=80',
    'houmous': 'https://images.unsplash.com/photo-1577805947697-89e18249d767?auto=format&fit=crop&w=900&q=80',
    'tiramisu': 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=900&q=80',
    'panna': 'https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=900&q=80',
    'mousse': 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=900&q=80',
    'glace': 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?auto=format&fit=crop&w=900&q=80',
    'dessert': 'https://images.unsplash.com/photo-1551024506-0bccd828d307?auto=format&fit=crop&w=900&q=80',
    'spritz': 'https://images.unsplash.com/photo-1551538827-9c037cb4f32a?auto=format&fit=crop&w=900&q=80',
    'cocktail': 'https://images.unsplash.com/photo-1536935338788-846bb9981813?auto=format&fit=crop&w=900&q=80',
    'beer': 'https://images.unsplash.com/photo-1608270586620-248524c67de9?auto=format&fit=crop&w=900&q=80',
    'bier': 'https://images.unsplash.com/photo-1608270586620-248524c67de9?auto=format&fit=crop&w=900&q=80',
    'cafe': 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=900&q=80',
    'the': 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=900&q=80',
    'soft': 'https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=900&q=80',
    'eau': 'https://images.unsplash.com/photo-1523362628745-0c100150b504?auto=format&fit=crop&w=900&q=80',
    'jus': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?auto=format&fit=crop&w=900&q=80',
    'vin': 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?auto=format&fit=crop&w=900&q=80',
    'wine': 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?auto=format&fit=crop&w=900&q=80',
    'prosecco': 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=900&q=80',
    'default': 'https://images.unsplash.com/photo-1546549032-9571cd6b27df?auto=format&fit=crop&w=900&q=80',
}

def img(*words):
    text = ' '.join(str(w).lower() for w in words if w)
    text = text.replace('é','e').replace('è','e').replace('ê','e').replace('à','a').replace('ù','u').replace('ç','c').replace('ô','o').replace('î','i')
    checks = [
        ('margherita','margherita'), ('calzone','calzone'), ('carbonara','carbonara'), ('bolognaise','bolognaise'), ('bologn','bolognaise'),
        ('arrabiata','arrabiata'), ('gnocchi','gnocchi'), ('lasagne','lasagnes'), ('raviol','ravioles'), ('fiore','ravioles'),
        ('bruschetta','bruschetta'), ('salade','salade'), ('tartare','tartare'), ('charcuterie','charcuterie'), ('antipast','antipasti'),
        ('burrata','burrata'), ('caprese','caprese'), ('aubergine','aubergines'), ('houmous','houmous'), ('tiramisu','tiramisu'),
        ('panna','panna'), ('mousse','mousse'), ('glace','glace'), ('dame blanche','glace'), ('dessert','dessert'), ('douceur','dessert'),
        ('spritz','spritz'), ('gin','cocktail'), ('cuba','cocktail'), ('whisky','cocktail'), ('vodka','cocktail'), ('martini','cocktail'), ('ricard','cocktail'), ('aperitivo','cocktail'),
        ('birre','beer'), ('peroni','beer'), ('moretti','beer'), ('leffe','beer'), ('desperados','beer'),
        ('cafe','cafe'), ('cappuccino','cafe'), ('chocolat chaud','cafe'), ('the','the'),
        ('coca','soft'), ('limonade','soft'), ('iced tea','soft'), ('orangina','soft'), ('sirop','soft'), ('diabolo','soft'), ('canette','soft'),
        ('eau','eau'), ('pellegrino','eau'), ('abatilles','eau'), ('jus','jus'),
        ('prosecco','prosecco'), ('moscato','prosecco'), ('lambrusco','prosecco'), ('vin','vin'), ('wine','wine'), ('chateau','vin'), ('chianti','vin'), ('valpolicella','vin'), ('nero','vin'),
        ('pizza','pizza'),
    ]
    for needle, key in checks:
        if needle in text:
            return PHOTO_BANK[key]
    return PHOTO_BANK['default']

MENU = [
    ('Apéritivo', [
        ('Spritz', 'Cocktail italien pétillant.', '7.50', 'verre', 'Aperitivo'),
        ('Gin tonic', 'Gin tonic classique.', '8.50', 'verre', 'Aperitivo'),
        ('Cuba libre', 'Rhum, cola et citron vert.', '8.00', 'verre', 'Aperitivo'),
        ('Whisky coca', 'Whisky et cola.', '7.50', 'verre', 'Aperitivo'),
        ('Vodka 4cl', 'Orange, pomme ou Red Bull.', '8.50', '4cl', 'Aperitivo'),
        ('Marsala 7cl', 'Marsala italien.', '5.50', '7cl', 'Aperitivo'),
        ('Martini 7cl', 'Martini italien.', '5.50', '7cl', 'Aperitivo'),
        ('Ricard 2cl', 'Pastis Ricard.', '3.50', '2cl', 'Aperitivo'),
        ("Coupe Moscato d'Asti", "Moscato d'Asti servi à la coupe.", '6.50', 'coupe', 'Aperitivo'),
        ('Coupe de Prosecco', 'Prosecco servi à la coupe.', '6.50', 'coupe', 'Aperitivo'),
        ('Verre de Lambrusco', 'Lambrusco au verre.', '6.50', 'verre', 'Aperitivo'),
    ]),
    ('Digestifs', [
        ('Limoncello', 'Liqueur italienne au citron.', '3.90', 'verre', 'Digestif'),
        ('Grappa 3cl', 'Eau-de-vie italienne.', '4.50', '3cl', 'Digestif'),
        ('Amaretto 4cl', "Liqueur d'amande italienne.", '6.00', '4cl', 'Digestif'),
        ('Get 27 4cl', 'Liqueur de menthe.', '6.00', '4cl', 'Digestif'),
    ]),
    ('Birre', [
        ('Peroni 33cl', 'Bière italienne.', '4.50', '33cl', 'Bière'),
        ('Moretti 33cl', 'Bière italienne.', '4.50', '33cl', 'Bière'),
        ('Leffe', 'Bière belge.', '4.50', 'bouteille', 'Bière'),
        ('Desperados', 'Bière aromatisée tequila.', '5.50', 'bouteille', 'Bière'),
        ('Bières artisanales Italiennes', 'Pils, IPA, Blanche ou Strong ALE.', '6.00', 'bouteille', 'Artisanal'),
    ]),
    ('Analcolici', [
        ('Coca 33cl', 'Coca, zéro ou cherry.', '3.50', '33cl', 'Frais'),
        ('Limonade 33cl', 'Limonade fraîche.', '4.00', '33cl', 'Frais'),
        ('Iced tea 33cl', 'Thé glacé.', '4.00', '33cl', 'Frais'),
        ('Orangina 33cl', 'Orangina.', '4.00', '33cl', 'Frais'),
        ('Sirops', 'Grenadine, menthe, citron, pêche ou violette.', '2.80', 'verre', 'Frais'),
        ('Diabolo', 'Grenadine, menthe, citron, pêche ou violette.', '4.50', 'verre', 'Frais'),
        ('San Pellegrino 1l', 'Eau pétillante San Pellegrino.', '3.80', '1l', 'Eau'),
        ('San Pellegrino 50cl', 'Eau pétillante San Pellegrino.', '3.50', '50cl', 'Eau'),
        ('Eau minérale Abatilles 1l', 'Eau minérale Abatilles.', '4.00', '1l', 'Eau'),
        ('Eau minérale Abatilles 50cl', 'Eau minérale Abatilles.', '3.50', '50cl', 'Eau'),
        ('Jus 25cl', 'Orange, pomme, ananas ou abricot.', '4.00', '25cl', 'Jus'),
        ('Canette à emporter', 'Coca, Coca zéro, Sprite, Orangina ou Iced tea.', '2.50', 'canette', 'À emporter'),
    ]),
    ('Caffè - Thé', [
        ('Café', 'Espresso italien.', '1.80', 'tasse', 'Café'),
        ('Café allongé', 'Café allongé.', '2.20', 'tasse', 'Café'),
        ('Café double', 'Double espresso.', '3.00', 'tasse', 'Café'),
        ('Thés et Infusions', 'Sélection de thés et infusions.', '3.50', 'tasse', 'Thé'),
        ('Cappuccino', 'Café italien au lait mousseux.', '4.50', 'tasse', 'Café'),
        ('Chocolat chaud', 'Chocolat chaud gourmand.', '4.50', 'tasse', 'Chaud'),
    ]),
    ('Nos entrées', [
        ('Caponata sicilienne & burrata', 'Légumes méditerranéens poêlés et déglacés au vinaigre balsamique, burrata, pignons de pin.', '10.90', 'portion', 'Entrée'),
        ('Mozzarella Caprese', "Mozzarella di bufala, tomates, basilic, pesto verde.", '8.50', 'portion', 'Entrée'),
        ("Gratin d'aubergines au parmesan", "Aubergines gratinées au parmesan.", '9.90', 'portion', 'Entrée'),
        ('Le houmous Vitti', "Purée de pois chiches, crème de sésame, citron, huile d'olive, ail, cumin.", '9.00', 'portion', 'Entrée'),
    ]),
    ('Antipasti à partager', [
        ('Planche de charcuterie', 'Jambon de Parme 20 mois, bresaola, speck, spianata calabra piquante, mortadelle, coppa, pancetta.', '22.50', 'planche', 'À partager'),
        ('Carpaccio di coppa', 'Fines tranches de coppa, roquette, champignons et courgettes grillées.', '16.50', 'portion', 'À partager'),
        ('Antipasto vegetariano', 'Mozzarella de bufflonne, roquette, artichaut alla romana, aubergines, courgettes et poivrons grillés.', '17.90', 'portion', 'Végétarien'),
        ('Delizia di parma et burrata', 'Fines tranches de jambon de Parme, burrata au pesto verde, roquette, tomates cerise, crème balsamique.', '22.50', 'portion', 'Signature'),
        ('Carpaccio di Bresaola', 'Bresaola, roquette, câpres, copeaux de parmesan, artichaut alla romana.', '20.90', 'portion', 'À partager'),
    ]),
    ('Nos bruschetta', [
        ('Bruschetta saumon fumé', 'Guacamole, zestes de citron.', '11.80', 'pièce', 'Bruschetta'),
        ('Bruschetta burrata pesto', 'Tomate confites, pignons de pin, basilic.', '10.90', 'pièce', 'Bruschetta'),
        ('Bruschetta figues', 'Jambon de Parme, gorgonzola.', '11.90', 'pièce', 'Bruschetta'),
        ('Bruschetta chèvre miel', 'Noix, tomates cerise, roquette.', '10.50', 'pièce', 'Bruschetta'),
    ]),
    ('Nos salades', [
        ('Salade Méditerranéenne', 'Feta, salade, tomates cerise, oignons rouges, olives Kalamata, concombre, huile d’olive al pesto genovese.', '15.50', 'salade', 'Salade'),
        ('Salade italienne', "Salade, jambon aux herbes, oignons rouges, olives Kalamata, tomates cerise, copeaux de parmesan, œuf, huile d'olive extra vierge à la truffe blanche.", '16.50', 'salade', 'Salade'),
        ('Tartare de saumon', 'Saumon frais, concombre, avocat, perles de grenades.', '15.90', 'portion', 'Frais'),
    ]),
    ('Nos Pizza', [
        ('La Margherita', 'Sauce tomate, mozzarella fior di latte, tomates cerise, olives, basilic.', '11.50', 'pizza', 'Pizza'),
        ('La Regina', 'Sauce tomate, mozzarella fior di latte, jambon blanc cuit aux herbes, champignons, olives, origan.', '13.50', 'pizza', 'Pizza'),
        ('La Quattro stagioni', 'Sauce tomate, mozzarella fior di latte, jambon blanc cuit aux herbes, artichauts, champignons, olives, origan.', '14.90', 'pizza', 'Pizza'),
        ('La Quattro fromaggi', 'Mozzarella fior di latte, gorgonzola, scamorza, copeaux de parmesan, basilic, tomates cerises.', '15.90', 'pizza', 'Fromage'),
        ("L’Adriana", 'Crème fraîche, mozzarella fior di latte, pancetta, tomates cerises, champignons, oignons.', '13.50', 'pizza', 'Pizza'),
        ('La Calabrese', 'Sauce tomate, mozzarella fior di latte, oignons rouges, spianata calabraise, piments doux, olives noires.', '15.90', 'pizza', 'Épicée'),
        ('La Calzone', 'Sauce tomate, mozzarella fior di latte, œuf, jambon cuit aux herbes, champignons, parmesan.', '15.50', 'pizza', 'Pizza'),
        ('La Tartuffo', 'Jambon cuit aux herbes, crème de truffe, scamorza, roquette, tomates cerises, copeaux de parmesan.', '17.80', 'pizza', 'Signature'),
        ('La Napoletana', 'Sauce tomate, mozzarella fior di latte, anchois marinés, câpres, olives noires.', '14.90', 'pizza', 'Pizza'),
        ('La Salmone', 'Crème fraîche, mozzarella fior di latte, saumon fumé, zestes de citron, tomates cerises, olives, pesto verde.', '16.50', 'pizza', 'Pizza'),
        ('La Parma et Burrata', 'Sauce tomate, mozzarella fior di latte, jambon de Parme 20 mois, tomates cerises, roquette, burrata fraîche, copeaux de parmesan.', '18.50', 'pizza', 'Signature'),
        ('La Vegetariana', 'Sauce tomate, mozzarella fior di latte, artichaut alla romana, aubergines, courgettes et poivrons grillés, roquette, pesto verde.', '15.90', 'pizza', 'Végétarien'),
        ('La Vesuvio', 'Sauce tomates, mozzarella di bufala, tomates cerises, origan, basilic, copeaux de parmesan, pesto verde.', '15.50', 'pizza', 'Pizza'),
        ('La Pescatora', 'Sauce tomates, mozzarella fior di latte, thon, olives, oignons rouges, tomates cerises, câpres, roquette.', '15.90', 'pizza', 'Pizza'),
        ('La fumée', 'Sauce tomates, mozzarella fior di latte, speck, scamorza fumée, éclats de noix.', '16.80', 'pizza', 'Fumée'),
        ('La Cabri', 'Crème fraîche, jambon cuit aux herbes, fromage de chèvre, miel, olives, roquette, tomates cerises.', '15.50', 'pizza', 'Pizza'),
    ]),
    ('Suppléments pizza', [
        ('Supplément légumes', 'Champignons, oignons, olives, tomates cerises, courgettes, aubergines, poivrons ou artichaut.', '1.00', 'supplément', 'Supplément'),
        ('Supplément œuf', 'Œuf supplémentaire.', '1.50', 'supplément', 'Supplément'),
        ('Supplément fromage', 'Gorgonzola, scamorza ou parmesan.', '2.50', 'supplément', 'Supplément'),
        ('Supplément buffala', 'Mozzarella di bufala.', '4.50', 'supplément', 'Supplément'),
        ('Supplément charcuterie', 'Jambon blanc, pancetta ou spianata calabra.', '3.50', 'supplément', 'Supplément'),
        ('Supplément premium', 'Jambon de Parme, bresaola ou jambon speck.', '4.50', 'supplément', 'Supplément'),
    ]),
    ('Nos Pastas', [
        ('Spaghetti à la Carbonara', 'Pancetta, œuf, parmesan.', '14.50', 'plat', 'Pasta'),
        ('Spaghetti à la Bolognaise', 'Viande de bœuf, sauce tomate, oignons, carottes, céleri.', '15.50', 'plat', 'Pasta'),
        ("Spaghetti à l'arrabiata", 'Sauce tomate, piment, oignons.', '14.50', 'plat', 'Pasta'),
        ('Gnocchi al Pesto Verde', 'Burrata, pignons grillés.', '16.50', 'plat', 'Pasta'),
        ('Lasagnes du chef', 'Lasagnes maison du chef.', '16.50', 'plat', 'Pasta'),
    ]),
    ('Nos Ravioles', [
        ('Ravioles chèvre', 'Fromage de chèvre, épinards.', '15.50', 'plat', 'Raviole'),
        ('Fiore aux aubergines', 'Aubergines grillées, sauce tomate, parmesan.', '16.00', 'plat', 'Raviole'),
        ('Ravioles à la burrata', 'Crème de truffes, noisettes.', '17.50', 'plat', 'Raviole'),
    ]),
    ('Menu Bambino', [
        ('Menu Bambino', 'Plat au choix: pâtes à la carbonara, pâte à la bolognaise ou pizza bambino jambon/fromage. Dessert: glace 1 boule. Boisson: sirop à l’eau.', '12.50', 'menu', 'Enfant'),
    ]),
    ('Nos douceurs', [
        ('Tiramisu', 'Dessert italien au mascarpone et café.', '6.90', 'dessert', 'Dessert'),
        ('Panna cotta aux fruits rouges', 'Panna cotta et fruits rouges.', '6.20', 'dessert', 'Dessert'),
        ('Panna cotta vanille et mangue', 'Panna cotta vanille et mangue.', '6.00', 'dessert', 'Dessert'),
        ('Panna cotta au caramel beurre salé', 'Panna cotta au caramel beurre salé.', '5.80', 'dessert', 'Dessert'),
        ('Mousse au chocolat', 'Mousse au chocolat.', '5.50', 'dessert', 'Dessert'),
        ('Baba au limoncello', 'Baba parfumé au limoncello.', '5.20', 'dessert', 'Dessert'),
        ('Dame blanche', 'Glace vanille, chocolat noir fondu, crème chantilly, noisettes.', '7.50', 'dessert', 'Dessert'),
        ('Affogato', 'Glace vanille noyée dans un café espresso.', '6.00', 'dessert', 'Dessert'),
        ('Glace 1 boule', 'Vanille, chocolat, fraise, citron ou pistache.', '3.00', 'glace', 'Glace'),
        ('Glace 2 boules', 'Vanille, chocolat, fraise, citron ou pistache.', '4.90', 'glace', 'Glace'),
    ]),
    ('Carte des vins - rouges', [
        ('Sélection Pizza Vitti rouge - verre', 'Vin rouge sélection Pizza Vitti.', '5.00', 'verre', 'Vin rouge'),
        ('Sélection Pizza Vitti rouge - bouteille', 'Vin rouge sélection Pizza Vitti.', '22.00', 'bouteille', 'Vin rouge'),
        ('Chateau Canet rouge - verre', 'Bordeaux BIO.', '5.00', 'verre', 'Vin rouge'),
        ('Chateau Canet rouge - bouteille', 'Bordeaux BIO.', '22.00', 'bouteille', 'Vin rouge'),
        ('Chateau Tour Castillon - verre', 'Médoc, cru bourgeois.', '6.00', 'verre', 'Vin rouge'),
        ('Chateau Tour Castillon - bouteille', 'Médoc, cru bourgeois.', '24.00', 'bouteille', 'Vin rouge'),
        ('Chianti - verre', 'Toscane.', '6.00', 'verre', 'Vin rouge'),
        ('Chianti - bouteille', 'Toscane.', '28.00', 'bouteille', 'Vin rouge'),
        ('Primitivo Salento - bouteille', 'Pouilles.', '32.00', 'bouteille', 'Vin rouge'),
        ('Valpolicella Ripasso - bouteille', 'Vénétie.', '38.00', 'bouteille', 'Vin rouge'),
        ("Nero d’Avola - bouteille", 'Sicilien.', '36.00', 'bouteille', 'Vin rouge'),
        ("Montepulciano d’Abruzzo - bouteille", 'Abruzzes.', '34.00', 'bouteille', 'Vin rouge'),
        ('Lacryma Christi - bouteille', 'Campanie / Napoli.', '32.00', 'bouteille', 'Vin rouge'),
    ]),
    ('Carte des vins - blancs', [
        ('Sélection Pizza Vitti blanc - verre', 'Vin blanc sélection Pizza Vitti.', '6.00', 'verre', 'Vin blanc'),
        ('Sélection Pizza Vitti blanc - bouteille', 'Vin blanc sélection Pizza Vitti.', '24.00', 'bouteille', 'Vin blanc'),
        ('Chateau Canet blanc - verre', 'Entre-deux-mers BIO.', '6.00', 'verre', 'Vin blanc'),
        ('Chateau Canet blanc - bouteille', 'Entre-deux-mers BIO.', '24.00', 'bouteille', 'Vin blanc'),
        ('Tentula Rapitala - bouteille', 'Sicile.', '28.00', 'bouteille', 'Vin blanc'),
    ]),
    ('Carte des vins - rosés', [
        ('Rosato delle Venizie - verre', 'Vin rosé italien.', '6.00', 'verre', 'Vin rosé'),
        ('Rosato delle Venizie - bouteille', 'Vin rosé italien.', '24.00', 'bouteille', 'Vin rosé'),
    ]),
    ('Carte des vins - pétillants', [
        ('Lambrusco - verre', 'Rouge, blanc ou rosé.', '7.00', 'verre', 'Vin pétillant'),
        ('Lambrusco - bouteille', 'Rouge, blanc ou rosé.', '22.50', 'bouteille', 'Vin pétillant'),
        ('Prosecco - verre', 'Vin pétillant italien.', '7.00', 'verre', 'Vin pétillant'),
        ('Prosecco - bouteille', 'Vin pétillant italien.', '32.00', 'bouteille', 'Vin pétillant'),
        ("Moscato d’Asti - verre", 'Vin doux pétillant italien.', '7.00', 'verre', 'Vin pétillant'),
        ("Moscato d’Asti - bouteille", 'Vin doux pétillant italien.', '32.00', 'bouteille', 'Vin pétillant'),
    ]),
]

class Command(BaseCommand):
    help = 'Create the complete Pizza Vitti menu from the new PDF, with categories and photos.'

    def handle(self, *args, **kwargs):
        Product.objects.all().delete()
        Category.objects.all().delete()
        cats = {}
        for order, (cat_name, items) in enumerate(MENU):
            cats[cat_name], _ = Category.objects.update_or_create(
                name=cat_name,
                defaults={'order': order, 'description': f'Carte Pizza Vitti — {cat_name}', 'is_active': True},
            )
            for item_order, (name, desc, price, unit, badge) in enumerate(items):
                search_words = [name, cat_name, 'italian food']
                Product.objects.update_or_create(
                    name=name,
                    defaults={
                        'category': cats[cat_name],
                        'description': desc,
                        'price': price,
                        'unit': unit,
                        'badge': badge,
                        'stock': 100,
                        'is_featured': cat_name in ['Nos Pizza', 'Nos entrées', 'Antipasti à partager', 'Nos Pastas', 'Nos douceurs'] and item_order < 4,
                        'professional_only': False,
                        'external_image': img(*search_words),
                        'is_available': True,
                        'meta_title': f'{name} | Pizza Vitti Bordeaux',
                        'meta_description': desc[:160],
                    },
                )

        posts = [
            ('Commander sa pizza en ligne à Bordeaux', 'Le menu digital simplifie le choix, le paiement et le retrait.', 'Avec un menu en ligne, les clients choisissent leurs pizzas, valident leur panier et peuvent payer en avance. C’est plus rapide pour eux et plus fluide pour le restaurant.', img('pizza restaurant')), 
            ('Les coulisses de Pizza Vitti', 'Actualités, nouveautés et événements du restaurant.', 'Le blog permet de publier les nouveautés, les offres spéciales et les événements. Il peut aussi relayer Instagram et Facebook pour garder le site vivant.', img('italian kitchen')), 
            ('Pizzas italiennes et pause repas rue d’Ornano', 'Une adresse pratique pour déjeuner ou dîner à Bordeaux.', 'Pizza Vitti accueille les clients au 236 Rue d’Ornano à Bordeaux avec une sélection de pizzas italiennes et une cuisine fraîche et variée.', img('pizza table')), 
        ]
        for title, excerpt, body, image_url in posts:
            BlogPost.objects.update_or_create(title=title, defaults={'excerpt': excerpt, 'body': body, 'external_image': image_url, 'meta_description': excerpt, 'is_published': True})

        reviews = [
            ('Martine B.',5,'Cette pizzeria offre depuis plusieurs années des produits de qualité dans un lieu accueillant.','Uniiti'),
            ('Dominique K.',5,'Pizzas très bonnes et copieuses, très bon accueil.','Uniiti'),
            ('Cyril B.',5,'Pizzas excellentes et service rapide!','Uniiti'),
            ('Sophie V.',5,'Rapide efficace pas cher et bon.','Uniiti'),
        ]
        for name, rating, comment, source in reviews:
            Review.objects.update_or_create(name=name, defaults={'rating':rating, 'comment':comment, 'source':source, 'is_published':True})

        gallery = [
            ('Pizza Vitti', img('pizza oven'), 0),
            ('Antipasti italiens', img('antipasti charcuterie burrata'), 1),
            ('Pâtes fraîches', img('italian pasta'), 2),
            ('Desserts maison', img('tiramisu panna cotta'), 3),
            ('Vins italiens', img('italian wine'), 4),
            ('Cocktails', img('spritz cocktail'), 5),
        ]
        for title, image_url, order in gallery:
            GalleryImage.objects.update_or_create(title=title, defaults={'external_image': image_url, 'order':order, 'is_active':True})

        self.stdout.write(self.style.SUCCESS(f'Pizza Vitti complete menu created: {len(MENU)} categories.'))
