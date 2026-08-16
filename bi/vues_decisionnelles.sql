-- =====================================================================
-- Vues décisionnelles SkillSeek AI (S4-03)
--
--   docker compose exec -T db psql -U skillseek -d skillseek < bi/vues_decisionnelles.sql
--
-- Ces vues constituent la couche sémantique exposée à Power BI. Les tables
-- applicatives ne sont jamais interrogées directement par le rapport, pour
-- trois raisons :
--
--   * le vocabulaire métier est fixé ici, en français, une fois pour toutes.
--     « received » devient « Reçue » à un seul endroit, et non dans chaque
--     visuel ;
--   * les règles de gestion — seuil de présélection, exclusion des éléments
--     mis à la corbeille — sont appliquées en base. Une même définition sert
--     donc l'application et le décisionnel, et les deux ne peuvent pas
--     diverger ;
--   * la structure interne peut évoluer sans casser les rapports, tant que
--     les vues conservent leurs colonnes.
--
-- Les données personnelles sont réduites au nécessaire : le décisionnel
-- travaille sur des volumes et des délais, pas sur des individus. Aucune
-- adresse électronique ni aucun numéro de téléphone n'y figure.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Référentiel des offres
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS bi_candidatures CASCADE;
DROP VIEW IF EXISTS bi_offres CASCADE;
DROP VIEW IF EXISTS bi_entonnoir CASCADE;
DROP VIEW IF EXISTS bi_activite CASCADE;
DROP VIEW IF EXISTS bi_competences CASCADE;
DROP VIEW IF EXISTS bi_indicateurs CASCADE;

CREATE VIEW bi_offres AS
SELECT
    o.id                                    AS offre_id,
    o.title                                 AS intitule,
    COALESCE(o.location, 'Non précisée')    AS localisation,
    COALESCE(o.contract_type, 'Non précisé') AS type_contrat,
    COALESCE(o.remote_policy, 'Non précisé') AS mode_travail,
    CASE o.status WHEN 'open' THEN 'Ouverte' ELSE 'Fermée' END AS statut,
    o.min_experience_years                  AS experience_requise,
    COALESCE(o.min_degree, 'Non exigé')     AS diplome_requis,
    o.salary_min                            AS salaire_min,
    o.salary_max                            AS salaire_max,
    COALESCE(jsonb_array_length(o.required_skills::jsonb), 0)  AS nb_competences_requises,
    COALESCE(jsonb_array_length(o.preferred_skills::jsonb), 0) AS nb_competences_souhaitees,
    o.created_at                            AS date_publication,
    o.created_at::date                      AS jour_publication,
    r.id                                    AS recruteur_id,
    r.full_name                             AS recruteur,
    COALESCE(r.company, 'Non renseignée')   AS entreprise
FROM job_offers o
JOIN users r ON r.id = o.recruiter_id
WHERE o.deleted_at IS NULL;

COMMENT ON VIEW bi_offres IS
    'Offres publiées, hors corbeille. Une ligne par offre.';


-- ---------------------------------------------------------------------
-- Candidatures : table de faits principale
-- ---------------------------------------------------------------------
CREATE VIEW bi_candidatures AS
SELECT
    a.id                                    AS candidature_id,
    a.offer_id                              AS offre_id,
    o.title                                 AS intitule_offre,
    r.full_name                             AS recruteur,
    COALESCE(r.company, 'Non renseignée')   AS entreprise,
    COALESCE(o.location, 'Non précisée')    AS localisation,
    COALESCE(o.contract_type, 'Non précisé') AS type_contrat,

    a.created_at                            AS date_candidature,
    a.created_at::date                      AS jour,
    date_trunc('week', a.created_at)::date  AS semaine,
    date_trunc('month', a.created_at)::date AS mois,

    a.score                                 AS note,
    -- Le seuil de 50 est la regle RG-01 : il est applique ici, et non dans
    -- chaque visuel, pour qu'application et decisionnel restent d'accord.
    CASE
        WHEN a.score IS NULL          THEN 'Non analysée'
        WHEN a.score >= 50            THEN 'Retenue'
        ELSE                               'Écartée'
    END                                     AS qualification,
    CASE
        WHEN a.score IS NULL   THEN 'Sans note'
        WHEN a.score >= 85     THEN '85 et plus'
        WHEN a.score >= 70     THEN '70 à 84'
        WHEN a.score >= 50     THEN '50 à 69'
        WHEN a.score >= 30     THEN '30 à 49'
        ELSE                        'Moins de 30'
    END                                     AS tranche_de_note,

    CASE a.status
        WHEN 'received'    THEN 'Reçue'
        WHEN 'under_review' THEN 'En étude'
        WHEN 'shortlisted' THEN 'Présélectionnée'
        WHEN 'interview'   THEN 'Entretien'
        WHEN 'hired'       THEN 'Recrutée'
        WHEN 'rejected'    THEN 'Non retenue'
        ELSE a.status
    END                                     AS statut,
    -- Rang de l'etape dans le parcours : sert a ordonner l'entonnoir sans
    -- que le rapport ait a coder l'ordre lui-meme.
    CASE a.status
        WHEN 'received'     THEN 1
        WHEN 'under_review' THEN 2
        WHEN 'shortlisted'  THEN 3
        WHEN 'interview'    THEN 4
        WHEN 'hired'        THEN 5
        WHEN 'rejected'     THEN 0
        ELSE 0
    END                                     AS rang_statut,

    -- Traçabilité de l'analyse, extraite du détail conservé avec la note.
    -- Le détail est stocké en `json` : la conversion en `jsonb` est requise
    -- pour disposer des fonctions de longueur de tableau.
    COALESCE(a.score_details::jsonb -> 'extraction' ->> 'methode', 'inconnue')
                                            AS methode_extraction,
    COALESCE(a.score_details::jsonb -> 'similarite' ->> 'methode', 'inconnue')
                                            AS methode_similarite,
    jsonb_array_length(
        COALESCE(a.score_details::jsonb -> 'eliminatoires', '[]'::jsonb))
                                            AS nb_criteres_eliminatoires,
    jsonb_array_length(
        COALESCE(a.score_details::jsonb -> 'reserves', '[]'::jsonb))
                                            AS nb_reserves,
    jsonb_array_length(
        COALESCE(a.score_details::jsonb -> 'competences_manquantes', '[]'::jsonb))
                                            AS nb_competences_manquantes,
    (a.score_details::jsonb -> 'modele' ->> 'probabilite')::numeric
                                            AS probabilite_modele,

    -- Delai de traitement : nombre de jours entre le depot et aujourd'hui
    -- pour les candidatures encore en attente de decision.
    CASE
        WHEN a.status IN ('received', 'under_review')
        THEN EXTRACT(DAY FROM (now()::timestamp - a.created_at))::int
    END                                     AS jours_en_attente
FROM applications a
JOIN job_offers o ON o.id = a.offer_id
JOIN users r      ON r.id = o.recruiter_id
WHERE o.deleted_at IS NULL;

COMMENT ON VIEW bi_candidatures IS
    'Table de faits : une ligne par candidature, enrichie de son offre.';


-- ---------------------------------------------------------------------
-- Entonnoir de conversion
-- ---------------------------------------------------------------------
CREATE VIEW bi_entonnoir AS
WITH etapes AS (
    SELECT 1 AS rang, 'Candidatures reçues' AS etape,
           COUNT(*)::int AS volume
    FROM bi_candidatures
    UNION ALL
    SELECT 2, 'Analysées',
           COUNT(*) FILTER (WHERE note IS NOT NULL)::int
    FROM bi_candidatures
    UNION ALL
    SELECT 3, 'Au-dessus du seuil',
           COUNT(*) FILTER (WHERE qualification = 'Retenue')::int
    FROM bi_candidatures
    UNION ALL
    SELECT 4, 'Entretiens',
           COUNT(*) FILTER (WHERE statut = 'Entretien')::int
    FROM bi_candidatures
    UNION ALL
    SELECT 5, 'Recrutements',
           COUNT(*) FILTER (WHERE statut = 'Recrutée')::int
    FROM bi_candidatures
)
SELECT
    rang, etape, volume,
    ROUND(100.0 * volume / NULLIF(MAX(volume) OVER (), 0), 1) AS part_du_total,
    ROUND(100.0 * volume / NULLIF(LAG(volume) OVER (ORDER BY rang), 0), 1)
                                                              AS conversion_etape
FROM etapes
ORDER BY rang;

COMMENT ON VIEW bi_entonnoir IS
    'Entonnoir de recrutement, avec conversion d''une étape à la suivante.';


-- ---------------------------------------------------------------------
-- Activité dans le temps
-- ---------------------------------------------------------------------
CREATE VIEW bi_activite AS
SELECT
    jour,
    COUNT(*)::int                                              AS candidatures,
    COUNT(*) FILTER (WHERE qualification = 'Retenue')::int      AS retenues,
    COUNT(*) FILTER (WHERE qualification = 'Écartée')::int      AS ecartees,
    COUNT(*) FILTER (WHERE qualification = 'Non analysée')::int AS non_analysees,
    ROUND(AVG(note)::numeric, 1)                               AS note_moyenne
FROM bi_candidatures
GROUP BY jour
ORDER BY jour;

COMMENT ON VIEW bi_activite IS 'Volumes et note moyenne par jour.';


-- ---------------------------------------------------------------------
-- Compétences les plus demandées
-- ---------------------------------------------------------------------
CREATE VIEW bi_competences AS
SELECT
    competence,
    COUNT(DISTINCT o.offre_id)::int AS nb_offres,
    'Obligatoire'                   AS nature
FROM bi_offres o
JOIN job_offers j ON j.id = o.offre_id
CROSS JOIN LATERAL jsonb_array_elements_text(
    COALESCE(j.required_skills::jsonb, '[]'::jsonb)) AS competence
GROUP BY competence
UNION ALL
SELECT
    competence,
    COUNT(DISTINCT o.offre_id)::int,
    'Souhaitée'
FROM bi_offres o
JOIN job_offers j ON j.id = o.offre_id
CROSS JOIN LATERAL jsonb_array_elements_text(
    COALESCE(j.preferred_skills::jsonb, '[]'::jsonb)) AS competence
GROUP BY competence;

COMMENT ON VIEW bi_competences IS
    'Compétences exigées ou appréciées, et nombre d''offres concernées.';


-- ---------------------------------------------------------------------
-- Indicateurs de synthèse (une seule ligne : cartes du tableau de bord)
-- ---------------------------------------------------------------------
CREATE VIEW bi_indicateurs AS
SELECT
    (SELECT COUNT(*) FROM bi_offres)::int                       AS offres,
    (SELECT COUNT(*) FROM bi_offres WHERE statut = 'Ouverte')::int AS offres_ouvertes,
    (SELECT COUNT(*) FROM bi_candidatures)::int                 AS candidatures,
    (SELECT COUNT(*) FROM bi_candidatures
      WHERE qualification = 'Retenue')::int                     AS retenues,
    (SELECT COUNT(*) FROM bi_candidatures
      WHERE statut = 'Entretien')::int                          AS entretiens,
    (SELECT COUNT(*) FROM bi_candidatures
      WHERE statut = 'Recrutée')::int                           AS recrutements,
    (SELECT COUNT(*) FROM bi_candidatures
      WHERE statut IN ('Reçue', 'En étude'))::int               AS en_attente,
    (SELECT ROUND(AVG(note)::numeric, 1) FROM bi_candidatures)  AS note_moyenne,
    (SELECT ROUND(AVG(jours_en_attente)::numeric, 1)
       FROM bi_candidatures)                                    AS delai_moyen_traitement,
    (SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE qualification = 'Retenue')
                  / NULLIF(COUNT(*), 0), 1) FROM bi_candidatures) AS taux_preselection;

COMMENT ON VIEW bi_indicateurs IS
    'Indicateurs de synthèse, une seule ligne, destinés aux cartes.';
