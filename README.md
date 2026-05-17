# Pizza Vitti Bordeaux — Django restaurant e-commerce

Site Django adapté pour **Pizza Vitti**, restaurant italien situé au 236 Rue d'Ornano, 33000 Bordeaux.

## Inclus

- Page d'accueil restaurant avec appels à l'action "Commander" et "Réserver / contacter"
- Menu en ligne avec catégories : Pizze Rosse, Pizze Bianche, Antipasti, Dolci, Boissons, Commandes groupe
- Panier, checkout et suivi de commande
- Paiement en avance prêt via Stripe : ajoutez les clés dans `.env`
- Blog pour actualités, promotions, événements et contenus liés à Instagram/Facebook
- Bloc avis clients / commentaires
- Formulaire contact et réservation
- Assistant client simple
- Admin Django pour gérer menu, articles, commandes, clients groupe et messages
- Crédit footer : `Site created with Kayan.fr`

## Lancer en local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Ouvrir : http://127.0.0.1:8000/

## Paiement Stripe

Dans `.env`, configurer :

```env
STRIPE_PUBLIC_KEY=pk_live_xxx
STRIPE_SECRET_KEY=sk_live_xxx
```

Sans clés Stripe, le site reste fonctionnel avec paiement au retrait.

## À personnaliser

- Remplacer les URL Instagram/Facebook dans `shop/templates/shop/base.html` et `home.html`
- Ajouter le vrai logo Pizza Vitti dans les templates/static si disponible
- Ajuster les prix du menu dans l'admin Django
- Mettre les vraies photos du restaurant dans `media/` ou en URL externe
- Configurer `SITE_URL` et `ALLOWED_HOSTS` pour le domaine final


## V5 updates
- Multilingual front pages: /fr/accueil, /en/home, /es/inicio, /it/home, /pt/inicio, /nl/home, /zh/, /ja/, /ar/.
- Google login is enabled with django-allauth. After `python manage.py migrate`, open `/admin/`, add a Social application for provider Google, then paste your Google Client ID and Secret.
- SEO improved with hreflang links, canonical URLs, JSON-LD Restaurant schema and robots.txt.
- Card payment wording now shows Visa / Mastercard / CB through Stripe. Each order automatically has an invoice at `/facture/<order_number>/`.
- “Clients professionnels” and public Services sections are removed from the admin/site interface.
