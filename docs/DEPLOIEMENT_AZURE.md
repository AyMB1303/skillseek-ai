# Déploiement sur Azure — session de validation

Mettre SkillSeek AI en ligne le temps d'une session, prouver que la chaîne va
du commit au service en fonctionnement, prendre les captures qui l'attestent,
puis libérer les ressources.

**Durée : 1 heure. Coût : environ 0,30 $** de crédit académique.

---

## Pourquoi des conteneurs et non une machine virtuelle

L'abonnement *Azure for Students* porte deux restrictions qui, combinées,
interdisent toute machine virtuelle :

**Une politique de régions.** Cinq régions sont autorisées — `polandcentral`,
`germanywestcentral`, `switzerlandnorth`, `swedencentral`, `austriaeast`.
Le portail propose pourtant toutes les autres, et ne signale le refus qu'à la
validation finale. La liste se lit ainsi :

```bash
az policy assignment list --query "[].{nom:displayName, params:parameters}" -o json
```

**Un quota de processeurs nul sur les familles proposées.** Dans
`germanywestcentral`, les familles offertes sont `Dsv7`, `Ddsv7`, `Dlsv7` —
toutes à une limite de zéro. À l'inverse, les familles disposant d'un quota
(`Bsv2`, `DSv3`, `Dv3`) n'y sont pas proposées. Vérification :

```bash
az vm list-usage --location germanywestcentral -o table
```

**Azure Container Instances relève d'un quota distinct**, lui disponible. Et le
projet étant déjà entièrement conteneurisé, c'est une transposition directe
plutôt qu'un contournement.

---

## Préalables

**Les images doivent être publiées et publiques.** Elles ne sont produites que
depuis `main` :

```bash
git checkout main
git merge dev
git push origin main
```

Puis, dans **github.com/AyMB1303?tab=packages**, pour `backend` **et**
`frontend` : *Package settings* → *Danger Zone* → **Change visibility** →
**Public**.

**Enregistrer le service**, une seule fois par abonnement :

```bash
az provider register --namespace Microsoft.ContainerInstance
az provider show --namespace Microsoft.ContainerInstance --query registrationState -o tsv
```

Attendre l'état `Registered`.

---

## Étape 1 — Déployer

Dans le **Cloud Shell** du portail Azure, en Bash :

```bash
az group create --name SkillSeek-demo --location germanywestcentral
git clone --depth 1 https://github.com/AyMB1303/skillseek-ai.git
cd skillseek-ai
bash deploiement/aci/deployer.sh
```

Le script génère trois secrets neufs, encode la configuration du proxy, compose
la description du groupe et lance la création. Cinq à dix minutes : Azure
télécharge 3,7 Go d'image applicative.

> 📸 **Capture 1** — la sortie du Cloud Shell à la fin du script, avec le cadre
> qui affiche l'adresse publique.

Note l'adresse, de la forme `skillseek-xxxxxx.germanywestcentral.azurecontainer.io`.

---

## Étape 2 — Suivre le démarrage

Quand la commande rend la main, **la plateforme ne répond pas encore**. Le
service applicatif attend la base, applique les onze migrations, installe rôles
et permissions, puis charge le jeu de démonstration.

```bash
az container logs -g SkillSeek-demo -n skillseek --container-name backend --follow
```

Attendre de voir défiler les migrations Alembic, puis `Jeu de démonstration en
place` et son décompte, puis la ligne de démarrage de Flask. Trois à cinq
minutes.

> 📸 **Capture 2** — ces journaux, montrant les migrations et
> `74 candidatures déposées`. C'est elle qui prouve que la chaîne complète
> s'exécute sur le serveur, et pas seulement que des conteneurs tournent.

Quitter le suivi avec `Ctrl+C`.

---

## Étape 3 — Vérifier

```bash
az container show -g SkillSeek-demo -n skillseek \
  --query "{etat:instanceView.state, adresse:ipAddress.fqdn, ip:ipAddress.ip}" -o table
```

```bash
az container show -g SkillSeek-demo -n skillseek \
  --query "containers[].{conteneur:name, etat:instanceView.currentState.state, cpu:resources.requests.cpu, memoire:resources.requests.memoryInGB}" -o table
```

La seconde commande liste les quatre conteneurs et leur état.

> 📸 **Capture 3** — cette sortie : quatre conteneurs `Running`, avec leurs
> ressources. L'équivalent d'un `docker compose ps` en production.

Puis, **depuis ton poste** et non depuis le Cloud Shell :

```
curl http://<adresse>/api/ready
```

> 📸 **Capture 4** — la réponse, dépendances à `true`, interrogée depuis
> l'extérieur.

Et dans le portail : **Resource groups** → `SkillSeek-demo` → le groupe de
conteneurs.

> 📸 **Capture 5** — la page Azure du groupe, état *Running*.

---

## Étape 4 — La plateforme en ligne

Ouvre `http://<adresse>` dans ton navigateur.

> 📸 **Capture 6 — la plus importante.** Connecté en recruteur
> (`s.lamrani@bcskills.ma` / `Demo@1234`), sur le **détail d'une candidature
> analysée** : le score, les cinq composantes, les compétences mises en
> correspondance. **L'adresse publique doit être lisible dans la barre du
> navigateur.** Une seule image qui montre l'URL et le produit qui fonctionne.

> 📸 **Captures 7 à 9** — à la même adresse : l'analyse décisionnelle, le
> journal d'audit, l'assistant. Elles montrent que ce n'est pas une page
> d'accueil isolée mais la plateforme entière.

Range le tout dans `docs/captures/`.

**Comptes :**

| Rôle | Identifiant | Mot de passe |
|---|---|---|
| Candidat | `y.tazi@example.ma` | `Demo@1234` |
| Recruteur | `s.lamrani@bcskills.ma` | `Demo@1234` |
| Administrateur | `admin@skillseek.local` | `Admin@1234` |

---

## Étape 5 — Libérer

**Une fois toutes les captures prises, et pas avant.**

```bash
az group delete --name SkillSeek-demo --yes
```

Supprimer le groupe emporte les conteneurs, l'adresse publique et le réseau
d'un seul coup. Vérifier ensuite dans **Cost Management** que la consommation
s'arrête.

---

## En cas de problème

**Le téléchargement de l'image échoue** — les paquets GHCR ne sont pas publics.
Reprendre les préalables.

**Le backend redémarre en boucle** — lire ses journaux. La cause la plus
probable est une base qui n'a pas eu le temps de démarrer ; le script attend
pourtant jusqu'à trois minutes.

**La page s'affiche mais reste vide** — le proxy joint le service applicatif
sur `127.0.0.1:5000`. Vérifier les journaux du conteneur `proxy`.

```bash
az container logs -g SkillSeek-demo -n skillseek --container-name proxy
az container logs -g SkillSeek-demo -n skillseek --container-name db
```

---

## La formulation pour le rapport

Ne jamais écrire que la plateforme est « en production » — elle ne le sera plus
quand le jury lira. Et ne pas revendiquer un déploiement continu : le
déploiement est ici **déclenché manuellement**, depuis un script versionné.

> Le déploiement a été réalisé et vérifié sur Azure Container Instances : les
> images produites par la chaîne d'intégration ont été récupérées depuis le
> registre, les migrations appliquées et la disponibilité du service contrôlée
> depuis l'extérieur. Le recours aux conteneurs plutôt qu'à une machine
> virtuelle découle d'une contrainte de l'abonnement académique, dont la
> politique de régions et les quotas de processeurs interdisaient toute
> instance. Les ressources ont été libérées après validation.

Exact, appuyé par les captures, et cohérent avec le reste du rapport.
