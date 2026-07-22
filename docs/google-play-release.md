# Publication Google Play - Pizza Vitti

L'application Android est une Trusted Web Activity qui ouvre la PWA Pizza Vitti.

## Identité de l'application

- Nom : `Pizza Vitti`
- Package Android : `kayen.fr`
- URL de démarrage : `https://pizza-vitti.kayen.fr/app/`
- Projet Android : `android/`
- API Android ciblée par cette release : `35`
- API de compilation : `36`

Le package Android devient définitif dès la création de l'application dans Google
Play Console. Ne pas le modifier après cette étape.

## 1. Construire sans signature

Cette commande vérifie que le projet Android compile sans demander de secret :

```bash
cd android
npx --yes @bubblewrap/cli build --skipSigning
```

Les fichiers générés dans `android/app/build/` ne sont pas enregistrés dans Git.

## 2. Créer la clé d'importation

Créer la clé une seule fois depuis le dossier `android/` :

```bash
npx --yes @bubblewrap/cli build
```

Bubblewrap propose de créer `android.keystore`. Choisir un mot de passe long et
unique, puis le conserver dans un gestionnaire de mots de passe. Ne jamais ajouter
la clé ou son mot de passe dans Git. Une perte de cette clé peut bloquer les futures
mises à jour de l'application.

La clé d'importation Pizza Vitti a été créée localement dans :

```text
android/android.keystore
android/.env.play-signing
```

Ces deux fichiers sont privés, ignorés par Git et doivent être sauvegardés ensemble
dans un gestionnaire de mots de passe ou un coffre chiffré. Ne pas les envoyer par
e-mail ou messagerie.

Pour reconstruire une version signée sans saisir les mots de passe dans le terminal :

```bash
cd android
set -a
. ./.env.play-signing
set +a
npx --yes @bubblewrap/cli build
```

Le build signé produit notamment :

```text
android/app-release-bundle.aab
android/app-release-signed.apk
```

Empreinte SHA-256 de la clé d'importation :

```text
2E:AF:ED:BC:64:E1:4A:51:0A:D1:93:43:EB:50:69:FF:14:30:E2:16:7E:24:C6:6F:AB:EE:86:9E:9B:E0:85:6D
```

Cette empreinte permet de tester l'APK signé directement. Après l'envoi sur Google
Play, il faut également ajouter l'empreinte distincte fournie par Play App Signing.

## 3. Créer l'application dans Play Console

1. Attendre la validation complète du compte développeur Google Play.
2. Créer une application nommée `Pizza Vitti`.
3. Utiliser le package `kayen.fr`.
4. Activer Play App Signing.
5. Envoyer le fichier `.aab` dans le canal de test interne.
6. Compléter la fiche Play Store, la politique de confidentialité, la sécurité des
   données, la classification du contenu et la section d'accès à l'application.

Pour la section d'accès, expliquer que certaines pages nécessitent un rôle
Propriétaire, Cuisine ou Staff et fournir à Google un compte de test limité.

## 4. Relier l'application au site

Après l'envoi du bundle, ouvrir :

`Play Console > Configuration > Intégrité de l'application > Signature de l'application`

Copier l'empreinte SHA-256 du certificat de signature de l'application, puis ajouter
sur Render :

```env
ANDROID_APP_PACKAGE=kayen.fr
ANDROID_CERT_SHA256_FINGERPRINTS=AA:BB:CC:...
```

Plusieurs empreintes peuvent être séparées par des virgules. Redéployer ensuite le
site et vérifier :

```text
https://pizza-vitti.kayen.fr/.well-known/assetlinks.json
```

Le fichier doit contenir le package `kayen.fr` et l'empreinte Play.
Sans cette association, l'application peut afficher une barre de navigateur.

## 5. Tester avant production

- Installer la version du canal de test interne sur un téléphone Android.
- Vérifier la connexion Propriétaire, Cuisine et Staff.
- Vérifier qu'un compte Cuisine ou Staff ne peut pas ouvrir le dashboard
  Propriétaire.
- Tester les commandes, le son cuisine, le pointage, la caméra et les notifications.
- Tester l'application avec une connexion lente et après une mise à jour.

Les nouveaux comptes personnels Google Play peuvent devoir effectuer un test fermé
avec le nombre de testeurs et la durée indiqués dans leur Play Console avant de
demander l'accès à la production.

## 6. Activer le badge du site

Quand la fiche Play Store est visible, ajouter l'URL de l'application dans les
variables Render :

```env
GOOGLE_PLAY_URL=https://play.google.com/store/apps/details?id=kayen.fr
```

Redéployer ensuite le service. Le badge officiel Google Play présent dans le footer
ouvrira alors la fiche publique au lieu du programme d'installation web.

## Nouvelle version

Avant chaque nouvel envoi, augmenter `appVersionCode` dans
`android/twa-manifest.json`, mettre à jour `appVersionName`, puis exécuter :

```bash
cd android
npx --yes @bubblewrap/cli update
npx --yes @bubblewrap/cli build
```

Bubblewrap peut régénérer `android/app/build.gradle`. Cette première release cible
l'API 35, acceptée jusqu'au 30 août 2026. Avant tout envoi à partir du 31 août 2026,
passer `targetSdkVersion` à `36` ou à une version plus récente exigée par Google Play.
