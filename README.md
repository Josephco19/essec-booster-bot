# Essec Masters – booster automatique

GitHub lance `open_booster.py` toutes les 5 minutes (avec un peu de retard
parfois). Si le booster est prêt, il est ouvert ; sinon le script s'arrête
tranquillement et réessaie au tour suivant. Ton ordi peut être éteint.

## Installation (5 minutes)

1. **Crée un repo public** sur GitHub (public = minutes GitHub Actions
   illimitées et gratuites ; ton cookie reste secret, voir étape 3).
2. **Envoie ces fichiers** dans le repo (bouton *Add file → Upload files*,
   en gardant le dossier `.github/workflows/`).
3. **Récupère ton cookie** dans Chrome :
   - va sur https://www.essecmasters.com/home (connecté) ;
   - `F12` → onglet **Network** → recharge la page (`F5`) ;
   - clique sur la ligne **home** → **Headers** → **Request Headers** ;
   - copie toute la valeur de la ligne **cookie**.
4. **Ajoute-le en secret** : dans le repo, *Settings → Secrets and variables →
   Actions → New repository secret*, nom `ESSEC_COOKIE`, colle la valeur.
5. **Teste** : onglet *Actions* → « Ouvrir le booster » → *Run workflow*.
   Dans le log tu dois voir « Booster ouvert ! » ou « Pas de booster pour
   l'instant ».

## Si ça s'arrête

- **Mail de GitHub « Run failed » avec « pas connecté »** : ton cookie a
  expiré (ou tu t'es déconnecté du site). Refais les étapes 3 et 4.
  Astuce : ne clique pas sur *Log out* sur le site, ça invalide le cookie.
- **« réponse inattendue »** : le site a changé, il faut adapter le script.

## Repo privé ?

Un repo privé n'a que 2 000 minutes gratuites par mois, et chaque passage en
compte une. Dans ce cas, remplace `*/5 * * * *` par `*/30 * * * *` dans
`.github/workflows/booster.yml`.
