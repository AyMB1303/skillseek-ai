# Figures du rapport de stage

Huit figures, toutes engendrées par `generer.py`. Aucune n'a été dessinée à
la main : chacune sort d'une description textuelle versionnée à côté du code,
et se refait à l'identique par une commande.

```bash
python docs/figures/generer.py                  # les huit
python docs/figures/generer.py classes          # une seule
```

Dépendances : `graphviz` (commande `dot`) et `ImageMagick` (commande
`convert`). Les sources `.dot` et `.svg` restent dans ce dossier ; les `.svg`
s'ouvrent tels quels dans un navigateur.

## Les neuf figures

| Fichier | Contenu |
|---|---|
| `fig_organigramme.png` | Organigramme de BC SKILLS et rattachement du stagiaire |
| `fig_cas_utilisation.png` | Cas d'utilisation : trois acteurs, frontière du système |
| `fig_sequence_analyse.png` | Séquence : du dépôt du CV à la note justifiée |
| `fig_activite_rg01.png` | Activité : la règle de présélection RG-01 |
| `fig_classes.png` | Classes du noyau métier, **lues dans les modèles SQLAlchemy** |
| `fig_schema_relationnel.png` | Les douze tables, clés et liens, **lues dans les modèles** |
| `fig_architecture_composants.png` | Composants et protocoles |
| `fig_deploiement.png` | Déploiement : poste, forge, groupe de conteneurs |
| `fig_chaine_cicd.png` | Chaîne d'intégration et de livraison |

Les deux figures du modèle de données ne sont pas des transcriptions : le
script importe l'application et lit `db.metadata`. Elles ne peuvent donc pas
diverger du schéma que créent les migrations. Modifier un modèle, relancer la
commande, et la figure suit.

## Contraintes de forme, et ce qu'elles imposent

Le guide de l'ESI demande deux choses des figures : **pas de couleur**, et
**une lisibilité conservée sur une photocopie en noir et blanc**. Trois
décisions en découlent.

**L'information n'est jamais portée par la couleur seule.** Elle l'est par la
forme, le style du trait, le niveau de gris et l'étiquette — et une légende
accompagne chaque figure qui distingue des catégories.

**Les niveaux de gris sont espacés d'au moins trente et une valeurs** sur les
deux cent cinquante-six. Une première version employait des gris à 244, 228 et
207 : le plus clair se tenait à onze valeurs du blanc. À l'écran la
distinction se voyait ; une photocopieuse l'aurait effacée, et avec elle la
séparation entre les cas du candidat et ceux du recruteur.

**La taille du texte une fois imprimé a été mesurée, pas supposée.** Elle ne
dépend que du nombre de caractères qui tiennent dans la largeur de la figure :
agrandir la police n'y change rien, puisque la figure grandit d'autant. Les
mises en page ont donc été resserrées — le schéma relationnel est passé de
4 725 à 2 417 pixels de large, la chaîne d'intégration de 3 761 à 2 229.

## Où les poser dans le rapport

| Largeur d'impression | Taille du texte | Verdict |
|---|---|---|
| 16 cm — pleine largeur de page | 5,3 à 6,6 pt | trop petit |
| 24 cm — page entière, en paysage | **8,0 à 9,8 pt** | lisible, y compris photocopié |

Les neuf figures demandent donc une **page en paysage**. En LaTeX :

```latex
\usepackage{rotating}   % dans le préambule

\begin{sidewaysfigure}[p]
  \centering
  \includegraphics[width=0.95\textheight]{figures/fig_classes.png}
  \caption{Diagramme de classes du noyau métier.}
  \label{fig:classes}
\end{sidewaysfigure}
```

Neuf pages de figures dans un rapport plafonné à trente, c'est beaucoup. Deux
sorties possibles : n'en retenir que quatre ou cinq et renvoyer les autres en
annexe, ou demander des versions allégées — moins d'attributs par classe,
moins de messages par séquence — qui tiendraient alors dans la largeur du
texte.

## À confirmer avant remise

**L'organigramme.** Sa structure reprend celle d'un organigramme antérieur,
et n'a donc pas été vérifiée : une entreprise se réorganise. Le rattachement
du stagiaire, porté sous « Technique », est une hypothèse — c'est pourquoi il
figure en trait discontinu. Les deux sont à faire valider par le tuteur, et
se corrigent en une ligne dans `generer.py`.
