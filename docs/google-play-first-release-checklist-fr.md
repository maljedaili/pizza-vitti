# Première publication Google Play - Pizza Vitti

Ce document est la checklist d'import de la version Android `1.0.0`.

## 1. Créer l'application

- Nom : `Pizza Vitti`
- Langue par défaut : `Français (France) - fr-FR`
- Type : `Application`
- Tarif : `Gratuite`
- Catégorie : `Cuisine et boissons`
- Package créé par le bundle : `kayen.fr`
- E-mail d'assistance : utiliser une adresse consultée régulièrement par le propriétaire.

## 2. Importer les éléments de la fiche

- Textes : `docs/google-play-store-listing-fr.md`
- Icône 512 x 512 : `android/store_icon.png`
- Feature graphic 1024 x 500 : `docs/play-store-assets/feature-graphic.png`
- Capture 1 : `docs/play-store-assets/phone-01-app-home.png`
- Capture 2 : `docs/play-store-assets/phone-02-role-login.png`
- Site : `https://pizza-vitti.kayen.fr/`
- Confidentialité : `https://pizza-vitti.kayen.fr/politique-confidentialite/`
- Suppression de compte : `https://pizza-vitti.kayen.fr/suppression-compte/`

## 3. Compléter App content

- Publicités : `Non`
- Accès à l'application : `Certaines fonctionnalités sont restreintes`
- Fournir les accès Propriétaire et Cuisine uniquement dans le formulaire privé
  destiné à l'équipe de validation Google.
- Public cible : adultes ; l'application n'est pas conçue pour les enfants.
- Application d'actualité : `Non`
- Application gouvernementale : `Non`
- Fonctionnalités financières : `Aucune`
- Data safety : reprendre et vérifier le brouillon dans
  `docs/google-play-store-listing-fr.md`.
- Classification du contenu : remplir le questionnaire selon les fonctions réelles
  de l'application de restaurant.

## 4. Créer la première release

1. Ouvrir `Test et publication > Tests > Test fermé`.
2. Créer une piste nommée `Test Pizza Vitti`.
3. Accepter Play App Signing.
4. Importer `android/app-release-bundle.aab`.
5. Nom de la release : `1.0.0`.
6. Coller les notes de version préparées dans la fiche.
7. Vérifier les avertissements, puis lancer le déploiement en test fermé.

## 5. Test fermé et production

- Ajouter au moins 12 testeurs avec leurs comptes Google.
- Envoyer le lien d'inscription généré par Play Console.
- Chaque testeur doit accepter le test et rester inscrit pendant 14 jours continus.
- Recueillir les retours et corriger tout blocage important.
- Après 14 jours, demander l'accès à la production depuis le Dashboard.
- Une fois l'accès accordé, promouvoir la release validée vers Production.

## Contrôle avant envoi

- [ ] L'e-mail d'assistance est confirmé.
- [ ] Les URL publiques répondent sans connexion.
- [ ] Les identifiants de validation sont à jour et non publiés dans la fiche.
- [ ] Les textes, l'icône, la feature graphic et les deux captures sont importés.
- [ ] Data safety correspond aux données réellement collectées.
- [ ] Le bundle importé affiche le package `kayen.fr` et la version `1.0.0`.
- [ ] Les 12 testeurs ont accepté le test fermé.
