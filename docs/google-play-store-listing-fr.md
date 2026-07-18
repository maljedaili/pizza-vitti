# Fiche Google Play - Pizza Vitti

Ce document contient les informations à saisir dans Google Play Console après la
validation du compte développeur Kayen.fr.

## Identité

- Nom de l'application : `Pizza Vitti`
- Langue par défaut : `Français (France) - fr-FR`
- Type : `Application`
- Prix : `Gratuite`
- Catégorie recommandée : `Cuisine et boissons`
- Package : `fr.kayen.pizzavitti`
- Site web : `https://pizza-vitti.kayen.fr/`
- Politique de confidentialité : `https://pizza-vitti.kayen.fr/politique-confidentialite/`
- Suppression de compte : `https://pizza-vitti.kayen.fr/suppression-compte/`
- E-mail d'assistance : à confirmer avec le propriétaire avant publication.

## Textes de la fiche

### Description courte

```text
Menu, commandes, fidélité et gestion du restaurant Pizza Vitti.
```

### Description complète

```text
Pizza Vitti réunit le menu du restaurant, les commandes et la fidélité dans une application simple et rapide.

Pour les clients :
- consulter les pizzas, pastas, boissons, menus bambino et desserts ;
- préparer une commande et suivre son statut ;
- commander à table avec le QR code du restaurant ;
- retrouver ses commandes, ses favoris et sa progression fidélité ;
- réserver et contacter Pizza Vitti.

Pour l'équipe du restaurant :
- recevoir les nouvelles commandes en cuisine ;
- suivre la préparation et signaler qu'une commande est prête ;
- gérer les tables et le pointage du personnel ;
- consulter les opérations depuis l'espace propriétaire sécurisé.

Les espaces Propriétaire, Cuisine et Staff utilisent des accès séparés. Les fonctions de gestion sont réservées aux personnes autorisées par Pizza Vitti.

Pizza Vitti
236 Rue d'Ornano
33000 Bordeaux, France
```

## Notes de version

Nom de la version :

```text
1.0.0 - Première version
```

Notes de version :

```text
Première version Android de Pizza Vitti : menu, commandes, fidélité client, préparation cuisine, gestion des tables et pointage staff.
```

## Éléments graphiques

- Icône 512 x 512 : `android/store_icon.png`
- Source de la feature graphic 1024 x 500 :
  `docs/play-store-assets/feature-graphic.html` (à exporter en PNG avant l'envoi).
- Captures téléphone :
  `docs/play-store-assets/phone-01-app-home.png` et
  `docs/play-store-assets/phone-02-role-login.png`.
- Vidéo : facultative pour la première version.

Texte alternatif de la feature graphic :

```text
Pizza italienne Pizza Vitti avec le slogan L'Italie à Bordeaux et les fonctions menu, commandes et fidélité.
```

Textes alternatifs des captures :

```text
Écran de choix entre les espaces Propriétaire, Cuisine, Staff et le site client.
Connexion sécurisée à l'espace Propriétaire de l'application Pizza Vitti.
```

## Accès pour l'équipe de validation Google

L'application contient des espaces restreints. Dans `App content > App access`,
indiquer que Google doit choisir un rôle sur la page de connexion :

- `Propriétaire (admin)` : accès au dashboard et à la cuisine ;
- `Cuisine (commandes)` : accès aux commandes uniquement, sans nom utilisateur ;
- `Staff (pointage)` : compte individuel créé par le propriétaire.

Saisir les identifiants de validation directement dans Play Console. Ne pas ajouter
les mots de passe dans Git, la description publique ou les captures d'écran.

Instructions proposées pour Google :

```text
Ouvrir l'application, sélectionner l'espace indiqué, puis utiliser les identifiants de test fournis dans ce formulaire. L'espace Cuisine demande uniquement un code. Le compte Cuisine ne peut pas ouvrir les pages Propriétaire.
```

## Déclarations App content

Réponses préparatoires à vérifier dans Play Console :

- Contient des publicités : `Non`.
- Accès à l'application : `Certaines fonctions sont restreintes`.
- Public cible recommandé : adultes ; l'application n'est pas conçue pour les enfants.
- Application d'actualité : `Non`.
- Application gouvernementale : `Non`.
- Fonction financière : paiement d'une commande de restaurant via Stripe, sans
  stockage des numéros de carte par Pizza Vitti.
- Permissions sensibles : le microphone peut être utilisé volontairement par le
  propriétaire pour parler via une caméra compatible ; Pizza Vitti ne stocke pas
  cet audio.

## Data safety - brouillon

Données susceptibles d'être collectées selon les fonctions utilisées :

- Informations personnelles : nom, e-mail, téléphone et adresse de commande.
- Activité dans l'application : commandes, favoris et progression fidélité.
- Informations de transaction : contenu, montant et statut de paiement ; aucune
  donnée complète de carte bancaire n'est stockée par Pizza Vitti.
- Messages : notes de commande, réservation et formulaire de contact.
- Données équipe : nom, rôle et heures de pointage pour les comptes staff.
- Audio : flux vocal temporaire uniquement lorsque le propriétaire active la
  fonction de parole d'une caméra compatible.

Finalités : fonctionnement de l'application, préparation des commandes, gestion de
compte, communication client, sécurité et opérations du restaurant.

Déclarations de sécurité :

- Données chiffrées pendant le transport : `Oui`, via HTTPS.
- Vente de données : `Non`.
- Publicité comportementale : `Non`.
- Suppression de compte disponible dans l'application : `Oui`.
- URL publique de suppression :
  `https://pizza-vitti.kayen.fr/suppression-compte/`.

Vérifier les réponses finales avec le propriétaire et les contrats des prestataires
Render, Stripe, e-mail et WhatsApp avant de soumettre le formulaire Data safety.

## Ordre de publication

1. Attendre la validation d'identité puis vérifier le téléphone du compte Kayen.fr.
2. Créer l'application `Pizza Vitti` avec la langue française et le type Application.
3. Activer Play App Signing et importer `android/app-release-bundle.aab`.
4. Compléter la fiche, App content, Data safety et l'accès des validateurs.
5. Publier d'abord sur le canal de test interne.
6. Créer ensuite un test fermé avec au moins 12 testeurs pendant 14 jours continus.
7. Demander l'accès à la production quand Google confirme que le test est éligible.
