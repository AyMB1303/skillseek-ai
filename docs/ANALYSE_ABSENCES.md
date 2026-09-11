# Ce que le document ne dit pas — principe d'analyse et correctifs

Note de travail rédigée après l'audit du 11/09/2026. Elle documente un
principe transversal de SkillSeek AI et les défauts qu'il a permis de lever.

## Le principe

Une rubrique **vide** et une rubrique **absente** portent deux informations
différentes, et les confondre est une faute d'analyse. Trois situations
doivent rester distinctes jusqu'à l'écran du recruteur :

| Situation | Ce que le système en sait | Ce qu'il affiche |
|---|---|---|
| Des éléments ont été extraits | une mesure | les éléments |
| La rubrique ne figure pas dans le CV | un fait sur le document | « Non mentionné dans le CV » |
| La rubrique y figure, rien n'en a été lu | un défaut d'analyse | un avertissement : ouvrir le document |

Le corollaire vaut pour toute grandeur : **une valeur qui n'a pas pu être
mesurée ne doit jamais s'écrire comme une mesure.** « 0 an d'expérience »
opposé à un candidat dont les dates n'ont pas été lues présente une lacune de
lecture comme un fait établi sur la personne — et c'est sur cette case que se
décide une élimination.

## Défauts levés

1. **Texte hors du cadre de la page.** Un CV trop long pour son format garde
   ses lignes en trop dans la couche texte, sous le bord de la page. Elles
   n'apparaissent ni à l'écran ni à l'impression, mais `pdfplumber` les
   restitue comme les autres : le profil se garnissait de compétences et de
   langues introuvables dans le document affiché à côté. C'est aussi la
   cachette classique des mots-clés ajoutés pour tromper un automate.
   → `extraction.py` découpe désormais chaque page à son cadre et compte ce
   qu'il écarte (`horsPage`), information remontée à l'interface.

2. **Langues inventées.** `extraire_langues` se rabattait sur le document
   entier faute de rubrique « Langues » : un nom d'employeur suffisait à
   déclarer une langue. Le repli exige maintenant que la ligne se présente
   elle-même comme une déclaration de langues.

3. **Niveaux nivelés.** Le niveau était pris une fois par ligne et appliqué à
   toutes les langues qui s'y trouvaient. Chaque langue reçoit le sien.

4. **Similarité sémantique indisponible renvoyée comme `0.0`.** Le contrat de
   `calculer_score` prévoyait `None` — une composante indisponible dont les
   25 points sont redistribués. Le zéro, lui, coûtait un quart de la note pour
   une comparaison qui n'avait jamais eu lieu.

5. **Expérience non déterminée valant zéro.** Séparée par
   `experienceDeterminee` ; une expérience non mesurée place la candidature en
   réserve au lieu de l'écarter, et n'ouvre plus l'équivalence de diplôme.

6. **Arrondi trompeur.** Deux mois de stage s'écrivaient « 0 an ». La durée
   est conservée en mois (`totalExperienceMonths`) et sert aussi bien à
   l'affichage qu'aux motifs de rejet.

7. **Caractères redoublés.** Un gras simulé par double tirage livrait
   « AAyymmeenn BBeennrrbbiibb » : le nom ne correspondait plus au compte et
   la candidature était signalée comme suspecte. Déduplication des glyphes
   superposés, puis redressement prudent au niveau du texte.

8. **Téléphone jamais relevé** lorsqu'il voisinait l'adresse électronique sans
   séparateur.

9. **CV non affichable.** `frame-src 'none'` et `object-src 'none'` dans la
   politique de sécurité de contenu bloquaient le cadre : le recruteur voyait
   « This content is blocked ». `frame-src` autorise désormais `blob:` — la
   page reste, elle, non incorporable ailleurs (`frame-ancestors 'none'`).

## Couverture

`tests/test_ats.py` (42), `tests/test_scoring.py` (34),
`tests/test_extraction.py` (12), dont des PDF construits à la main plaçant du
texte sous le bord de la page — aucune dépendance nouvelle.
