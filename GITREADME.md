# Aperture Studio

## Postavitev projekta (prvič)

1. Klonaj repozitorij:
   ```
   git clone git@github.com:MrLuka118/lnvision-.git
   cd lnvision-
   ```

2. Preveri, da imaš nastavljen SSH ključ za GitHub (Settings → SSH and GPG keys). Če ne:
   ```
   ssh-keygen -t ed25519 -C "tvoj@email.com"
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   pbcopy < ~/.ssh/id_ed25519.pub
   ```
   Nato ključ prilepi na GitHub in preveri z:
   ```
   ssh -T git@github.com
   ```

## Veje (branches)

- `production` – stabilna, "živa" verzija
- `dev` – testna veja za združevanje sprememb pred production
- `luka` – Lukova delovna veja
- `nikola` – Nikolova delovna veja

## Prehod na svojo vejo

```
git fetch
git checkout luka
```
oz.
```
git fetch
git checkout nikola
```

## Vsakodnevni potek dela

1. Pred začetkom dela vedno povleci najnovejše spremembe:
   ```
   git pull
   ```

2. Naredi spremembe, nato:
   ```
   git add .
   git commit -m "opis spremembe"
   git push
   ```

3. Ko je funkcionalnost pripravljena za testiranje, na GitHubu odpri **Pull Request** iz svoje veje (`luka` ali `nikola`) v `dev`.

4. Ko je vse na `dev` preverjeno in stabilno, se odpre Pull Request iz `dev` v `production`.

## Pomembno

- Nikoli ne delaj direktno na `production`.
- Pred vsakim začetkom dela naredi `git pull`, da se izogneš konfliktom.
- Po vsakem merge-u v `dev` ali `production` osveži svojo delovno vejo:
  ```
  git checkout luka
  git pull origin dev
  ```
