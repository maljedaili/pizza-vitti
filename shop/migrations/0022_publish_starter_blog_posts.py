from django.db import migrations


POSTS = [
    {
        'slug': 'pizza-italienne-artisanale-bordeaux',
        'title': 'La pizza italienne artisanale au cœur de Bordeaux',
        'excerpt': 'Découvrez notre façon de préparer une pizza généreuse, simple et inspirée de la tradition italienne rue d’Ornano.',
        'external_image': '/static/shop/img/hero/menu-pizza-vitti.jpg',
        'meta_title': 'Pizza italienne artisanale à Bordeaux | Pizza Vitti',
        'meta_description': 'Découvrez les pizzas italiennes artisanales de Pizza Vitti, préparées rue d’Ornano à Bordeaux.',
        'body': (
            "Chez Pizza Vitti, une bonne pizza commence par une pâte travaillée avec patience, "
            "une cuisson attentive et des ingrédients choisis pour leur goût. Notre carte met à "
            "l’honneur les grands classiques italiens ainsi que des recettes plus généreuses, "
            "pensées pour être partagées en famille, entre amis ou pendant une pause déjeuner.\n\n"
            "La sauce tomate, la mozzarella, les légumes, les fromages et les garnitures sont "
            "assemblés au dernier moment afin de préserver les textures et les saveurs. Chaque "
            "pizza est préparée à la commande dans notre restaurant du 236 rue d’Ornano à Bordeaux.\n\n"
            "Vous pouvez consulter les ingrédients et les prix directement sur notre menu en "
            "ligne, commander à emporter et nous signaler toute demande particulière. Pour une "
            "question concernant les allergènes, contactez toujours l’équipe avant de confirmer "
            "votre commande."
        ),
    },
    {
        'slug': 'que-choisir-menu-pizza-vitti',
        'title': 'Que choisir sur le menu Pizza Vitti ?',
        'excerpt': 'Pizza, pasta, antipasti ou douceur : quelques conseils simples pour composer votre prochain repas italien.',
        'external_image': '/static/shop/img/hero/menu-pasta.jpg',
        'meta_title': 'Que choisir sur le menu Pizza Vitti à Bordeaux ?',
        'meta_description': 'Nos conseils pour choisir pizzas, pâtes, entrées, boissons et desserts chez Pizza Vitti Bordeaux.',
        'body': (
            "Vous hésitez entre une pizza, un plat de pâtes ou plusieurs entrées à partager ? "
            "Commencez par choisir l’ambiance de votre repas. Une pizza convient parfaitement à "
            "un déjeuner rapide ou à une soirée conviviale. Les pastas et ravioles offrent une "
            "alternative chaleureuse, tandis que les antipasti permettent de goûter plusieurs "
            "saveurs autour de la table.\n\n"
            "Pour terminer, consultez les douceurs et les boissons proposées sur le menu. Les "
            "disponibilités et les prix affichés en ligne sont mis à jour par le restaurant. Les "
            "badges végétarien, épicé ou signature peuvent également vous aider à faire votre choix.\n\n"
            "Notre nouvel Assistant Vitti peut répondre aux questions courantes sur le menu. Pour "
            "les allergies ou les régimes spécifiques, demandez une confirmation directe à "
            "l’équipe, car la composition et les risques de traces doivent être vérifiés en cuisine."
        ),
    },
    {
        'slug': 'commander-pizza-en-ligne-bordeaux',
        'title': 'Commander votre pizza en ligne à Bordeaux',
        'excerpt': 'Voici comment choisir vos plats, préparer votre panier et récupérer votre commande chez Pizza Vitti.',
        'external_image': '/static/shop/img/hero/loyalty-pizza-vitti.jpg',
        'meta_title': 'Commander une pizza en ligne à Bordeaux | Pizza Vitti',
        'meta_description': 'Commandez votre pizza en ligne puis récupérez-la chez Pizza Vitti, 236 rue d’Ornano à Bordeaux.',
        'body': (
            "Le menu en ligne Pizza Vitti a été conçu pour rendre la commande plus simple. "
            "Parcourez les catégories, consultez les descriptions et ajoutez les produits désirés "
            "au panier. Vous pouvez ensuite ajuster les quantités avant de finaliser la commande.\n\n"
            "Si vous commandez depuis une table grâce au QR code, le numéro de table est mémorisé "
            "automatiquement. Pour une commande à emporter, vérifiez vos coordonnées et les "
            "informations de retrait avant de valider. Conservez ensuite votre numéro de commande "
            "pour suivre son état de préparation.\n\n"
            "Pizza Vitti se trouve au 236 rue d’Ornano, 33000 Bordeaux. En cas de doute sur une "
            "commande, un horaire exceptionnel ou un ingrédient, utilisez la page Contact ou "
            "appelez le restaurant avant de vous déplacer."
        ),
    },
]


def publish_posts(apps, schema_editor):
    BlogPost = apps.get_model('shop', 'BlogPost')
    for post in POSTS:
        BlogPost.objects.update_or_create(
            slug=post['slug'],
            defaults={**post, 'is_published': True},
        )


def remove_posts(apps, schema_editor):
    BlogPost = apps.get_model('shop', 'BlogPost')
    BlogPost.objects.filter(slug__in=[post['slug'] for post in POSTS]).delete()


class Migration(migrations.Migration):
    dependencies = [('shop', '0021_review_google_fields')]

    operations = [migrations.RunPython(publish_posts, remove_posts)]
