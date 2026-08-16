"""Assistant conversationnel fondé sur la récupération augmentée (RAG).

Le module est organisé en trois couches indépendantes :

  * `connaissance` : transforme le contenu de la plateforme en documents
    textuels indexables (offres, candidatures, profils, aide en ligne) ;
  * `index`        : encode ces documents en vecteurs et retrouve les plus
    proches d'une question posée ;
  * `generation`   : formule la réponse à partir des documents retrouvés,
    via le fournisseur disponible (gabarits, modèle local ou service distant).

Cette séparation permet de remplacer le générateur sans toucher au reste,
et de faire fonctionner l'assistant même sans modèle de langue installé.
"""
