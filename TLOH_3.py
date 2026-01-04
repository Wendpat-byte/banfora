# ============================================
# 1. PACKAGES ET IMPORTS
# ============================================
import streamlit as st
import pandas as pd
import pymysql
from pymysql import Error
from datetime import datetime
import hashlib
import time
from contextlib import contextmanager
from typing import Optional, List, Dict, Tuple, Any
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# 2. PAGE D'AUTHENTIFICATION
# ============================================
class GestionAuthentification:
    @staticmethod
    def authentifier(identifiant: str, mot_de_passe: str) -> Dict[str, Any]:
        """Authentifie l'utilisateur et retourne ses informations"""
        try:
            requete = """
                SELECT idUtilisateur, nom, prenom, identifiant, statut 
                FROM Utilisateur 
                WHERE identifiant = %s AND mot_de_passe = %s
            """
            parametres = (identifiant, mot_de_passe)
            
            resultat = executer_requete(requete, parametres, fetch=True)
            
            if resultat and len(resultat) > 0:
                return resultat[0]
            return None
        except Exception as e:
            logger.error(f"Erreur d'authentification: {e}")
            return None

def page_connexion():
    """Page de connexion à l'application"""
    st.markdown("<h1 class='titre-principal'>Plateforme de gestion TLOH</h1>", unsafe_allow_html=True)
    
    with st.form("formulaire_connexion"):
        st.subheader("Connexion")
        
        identifiant = st.text_input("Identifiant*", placeholder="Entrez votre identifiant")
        mot_de_passe = st.text_input("Mot de passe*", type="password", placeholder="Entrez votre mot de passe")
        
        bouton_connexion = st.form_submit_button("Se connecter", type="primary", use_container_width=True, 
                                                help="Cliquez pour vous connecter")
        
        if bouton_connexion:
            if not identifiant or not mot_de_passe:
                st.error("Veuillez remplir tous les champs obligatoires (*)")
            else:
                with st.spinner("Authentification en cours..."):
                    utilisateur = GestionAuthentification.authentifier(identifiant, mot_de_passe)
                    
                    if utilisateur:
                        st.session_state['authentifie'] = True
                        st.session_state['identifiant'] = utilisateur['identifiant']
                        st.session_state['nom_complet'] = f"{utilisateur['prenom']} {utilisateur['nom']}"
                        st.session_state['role_utilisateur'] = utilisateur['statut']
                        st.session_state['id_utilisateur'] = utilisateur['idUtilisateur']
                        st.session_state['page_actuelle'] = 'accueil'
                        st.success(f"Authentification réussie! Bienvenue {utilisateur['prenom']}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Identifiant ou mot de passe incorrect")

# ============================================
# 3. CONFIGURATION
# ============================================
class Configuration:
    TITRE_PAGE = "Plateforme de gestion des données du TLOH"
    
    # Configuration de la base de données
    CONFIG_DB = {
        "host": "localhost",
        "user": "root",
        "password": "1234",
        "database": "pato",
        "charset": "utf8mb4",
        "use_unicode": True,
        "autocommit": False,
        "raise_on_warnings": True
    }

    CONFIG_POOL = {
        "pool_name": "tloh_pool",
        "pool_size": 5,
        "pool_reset_session": True
    }
    
    # Services disponibles
    SERVICES = [
        "Pédiatrie", "Médecine Générale", "Urgences",
        "Gynéco-Obstétrique", "Maternité", "SPIH", "Administration"
    ]
    
    # Années disponibles
    ANNEES = list(range(2020, datetime.now().year + 2))
    
    # Types d'indicateurs
    TYPES_INDICATEUR = [
        "Maladie endemique",
        "maladies tropicales négligées",
        "décès"
    ]

# ============================================
# 4. CONNEXION À LA BASE DE DONNÉES MYSQL
# ============================================
@contextmanager
def obtenir_connexion_db():
    """Contexte pour gérer les connexions à la base de données"""
    connexion = None
    try:
        connexion = mysql.connector.connect(**Configuration.CONFIG_DB)
        yield connexion
    except Error as erreur:
        logger.error(f"Erreur de connexion à la base de données: {erreur}")
        st.error(f"Erreur de connexion à la base de données: {erreur}")
        raise
    finally:
        if connexion and connexion.is_connected():
            connexion.close()

def executer_requete(requete, parametres=None, fetch=False):
    """Exécute une requête SQL et retourne les résultats si nécessaire"""
    with obtenir_connexion_db() as connexion:
        curseur = connexion.cursor(dictionary=True)
        try:
            curseur.execute(requete, parametres or ())
            if fetch:
                resultat = curseur.fetchall()
            else:
                connexion.commit()
                resultat = curseur.rowcount
            return resultat
        except Error as erreur:
            logger.error(f"Erreur lors de l'exécution de la requête: {erreur}")
            st.error(f"Erreur lors de l'exécution de la requête: {erreur}")
            # Afficher la requête SQL pour débogage
            st.write(f"**Requête SQL:** {requete}")
            if parametres:
                st.write(f"**Paramètres:** {parametres}")
            return None
        finally:
            curseur.close()

# ============================================
# 5. PAGE D'ACCUEIL
# ============================================
def page_accueil():
    """Page d'accueil avec tableau de bord"""
    st.title("Tableau de bord")
    
    st.markdown("""
    <div class="boite-info">
        <h3>Bienvenue sur la plateforme de gestion des données TLOH</h3>
        <p>Cette application permet la collecte, la gestion et l'analyse des données épidémiologiques 
        du TLOH (Télégramme Lettre Officielle Hebdomadaire).</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Afficher les statistiques globales
    st.markdown("### Statistiques Globales")
    
    try:
        # Vérifier d'abord si la table Enregistrement existe
        check_table = executer_requete("SHOW TABLES LIKE 'Enregistrement'", fetch=True)
        
        if check_table:
            # Requête pour les statistiques globales
            requete_statistiques = """
            SELECT 
                IFNULL(SUM(cas), 0) AS total_cas,
                IFNULL(SUM(décès), 0) AS total_décès,
                IFNULL(SUM(isolé), 0) AS total_isolé,
                IFNULL(SUM(notifié), 0) AS total_notifié
            FROM Enregistrement
            """
            
            statistiques = executer_requete(requete_statistiques, fetch=True)
            
            if statistiques and len(statistiques) > 0:
                stats = statistiques[0]
                
                # Afficher les métriques
                colonne1, colonne2, colonne3, colonne4 = st.columns(4)
                
                with colonne1:
                    total_cas = stats['total_cas']
                    st.metric("Total Cas", total_cas)
                
                with colonne2:
                    total_décès = stats['total_décès']
                    st.metric("Total Décès", total_décès)
                
                with colonne3:
                    total_isolé = stats['total_isolé']
                    st.metric("Total Isolé", total_isolé)
                
                with colonne4:
                    total_notifié = stats['total_notifié']
                    st.metric("Total Notifié", total_notifié)
            else:
                st.info("Aucune donnée disponible dans la base")
        else:
            st.warning("La table 'Enregistrement' n'existe pas encore dans la base de données")
            
    except Exception as erreur:
        st.error(f"Erreur lors de la récupération des statistiques: {erreur}")

# ============================================
# 6. PAGE DE NOUVEL ENREGISTREMENT
# ============================================
def page_nouvel_enregistrement():
    """Page pour créer un nouvel enregistrement TLOH"""
    st.title("Nouvel enregistrement TLOH")
    
    # Section 1: Informations générales
    st.markdown('<h3 class="sous-titre">Informations générales</h3>', unsafe_allow_html=True)
    
    colonne1, colonne2 = st.columns(2)
    
    with colonne1:
        numéro_TLOH = st.text_input("Numéro TLOH*", help="Numéro unique d'identification du TLOH")
        service = st.selectbox("Service*", Configuration.SERVICES)
    
    with colonne2:
        date_début = st.date_input("Date de début*", value=datetime.now())
        date_fin = st.date_input("Date de fin*", value=datetime.now())
    
    # Initialiser les dictionnaires pour stocker les données
    donnees_maladies = {}
    donnees_tropicales = {}
    donnees_décès = {}
    
    # Variables pour suivre les erreurs de validation
    validation_erreurs = []
    
    # Section 2: Maladies endémiques
    st.markdown('<h3 class="sous-titre">Maladies endémiques</h3>', unsafe_allow_html=True)
    
    try:
        # Récupérer les maladies endémiques
        requete_endemiques = """
            SELECT idIndicateur, nom 
            FROM Indicateur 
            WHERE type = 'Maladie endemique'
            ORDER BY nom
        """
        maladies_endemiques = executer_requete(requete_endemiques, fetch=True)
        
        if maladies_endemiques:
            # Créer un tableau pour les maladies endémiques dans le même format que la page surveillance
            st.write("Renseignez le nombre de cas et de décès pour chaque maladie:")
            
            # Créer les en-têtes du tableau
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write("**indicateur**")
            with col2:
                st.write("**cas**")
            with col3:
                st.write("**décès**")
            
            for maladie in maladies_endemiques:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(maladie['nom'])
                
                with col2:
                    cas = st.number_input(
                        "",
                        min_value=0,
                        value=0,
                        key=f"cas_end_{maladie['idIndicateur']}",
                        label_visibility="collapsed"
                    )
                
                with col3:
                    # Ne pas compter les décès pour paludisme simple
                    if 'paludisme simple' in maladie['nom'].lower():
                        st.write("N/A")
                        décès = 0
                    else:
                        décès = st.number_input(
                            "",
                            min_value=0,
                            value=0,
                            key=f"décès_end_{maladie['idIndicateur']}",
                            label_visibility="collapsed"
                        )
                        
                        # Vérifier que le nombre de décès ne dépasse pas le nombre de cas
                        if décès > cas:
                            st.error(f"⚠️ Décès > Cas pour {maladie['nom']}")
                            validation_erreurs.append(f"Pour {maladie['nom']}: le nombre de décès ({décès}) ne peut pas dépasser le nombre de cas ({cas})")
                
                donnees_maladies[maladie['idIndicateur']] = {
                    'nom': maladie['nom'],
                    'cas': cas,
                    'décès': décès
                }
        else:
            st.info("Aucune maladie endémique définie")
            
    except Exception as erreur:
        st.error(f"Erreur lors du chargement des maladies endémiques: {erreur}")
    
    # Section 3: Maladies tropicales négligées
    st.markdown('<h3 class="sous-titre">Maladies tropicales négligées</h3>', unsafe_allow_html=True)
    
    try:
        # Récupérer les maladies tropicales négligées
        requete_tropicales = """
            SELECT idIndicateur, nom 
            FROM Indicateur 
            WHERE type = 'maladies tropicales négligées'
            ORDER BY nom
        """
        maladies_tropicales = executer_requete(requete_tropicales, fetch=True)
        
        if maladies_tropicales:
            # Créer un tableau pour les maladies tropicales négligées
            st.write("Renseignez le nombre de cas notifiés et isolés:")
            
            # Créer les en-têtes du tableau
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write("**indicateur**")
            with col2:
                st.write("**notifié**")
            with col3:
                st.write("**isolé**")
            
            for maladie in maladies_tropicales:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(maladie['nom'])
                
                with col2:
                    notifié = st.number_input(
                        "",
                        min_value=0,
                        value=0,
                        key=f"notifié_trop_{maladie['idIndicateur']}",
                        label_visibility="collapsed"
                    )
                
                with col3:
                    isolé = st.number_input(
                        "",
                        min_value=0,
                        value=0,
                        key=f"isolé_trop_{maladie['idIndicateur']}",
                        label_visibility="collapsed"
                    )
                    
                    # Vérifier que le nombre de cas isolés ne dépasse pas le nombre de cas notifiés
                    if isolé > notifié:
                        st.error(f" Isolé > Notifié pour {maladie['nom']}")
                        validation_erreurs.append(f"Pour {maladie['nom']}: le nombre de cas isolés ({isolé}) ne peut pas dépasser le nombre de cas notifiés ({notifié})")
                
                donnees_tropicales[maladie['idIndicateur']] = {
                    'nom': maladie['nom'],
                    'notifié': notifié,
                    'isolé': isolé
                }
        else:
            st.info("Aucune maladie tropicale négligée définie")
            
    except Exception as erreur:
        st.error(f"Erreur lors du chargement des maladies tropicales: {erreur}")
    
    # Section 4: Décès
    st.markdown('<h3 class="sous-titre">Décès</h3>', unsafe_allow_html=True)
    
    try:
        # Récupérer les types de décès
        requete_décès = """
            SELECT idIndicateur, nom 
            FROM Indicateur 
            WHERE type = 'décès'
            ORDER BY nom
        """
        types_décès = executer_requete(requete_décès, fetch=True)
        
        if types_décès:
            # Créer un tableau pour les décès
            st.write("Renseignez le nombre de décès en institution et en communauté:")
            
            # Créer les en-têtes du tableau
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write("**indicateur**")
            with col2:
                st.write("**institution**")
            with col3:
                st.write("**communauté**")
            
            for type_décès in types_décès:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(type_décès['nom'])
                
                with col2:
                    institution = st.number_input(
                        "",
                        min_value=0,
                        value=0,
                        key=f"inst_décès_{type_décès['idIndicateur']}",
                        label_visibility="collapsed"
                    )
                
                with col3:
                    communauté = st.number_input(
                        "",
                        min_value=0,
                        value=0,
                        key=f"comm_décès_{type_décès['idIndicateur']}",
                        label_visibility="collapsed"
                    )
                
                donnees_décès[type_décès['idIndicateur']] = {
                    'nom': type_décès['nom'],
                    'institution': institution,
                    'communauté': communauté,
                    'total_décès': institution + communauté
                }
        else:
            st.info("Aucun type de décès défini")
            
    except Exception as erreur:
        st.error(f"Erreur lors du chargement des types de décès: {erreur}")
    
    # Bouton final pour enregistrer toutes les données
    st.divider()
    
    # Afficher les erreurs de validation si elles existent
    if validation_erreurs:
        for erreur in validation_erreurs:
            st.error(erreur)
    
    if st.button("Enregistrer le TLOH", type="primary", use_container_width=True, 
                help="Cliquez pour enregistrer le TLOH", disabled=bool(validation_erreurs)):
        if not numéro_TLOH or not service:
            st.error("Veuillez remplir tous les champs obligatoires (*) dans la section Informations générales")
        elif validation_erreurs:
            st.error("Veuillez corriger les erreurs de validation avant d'enregistrer")
        else:
            try:
                enregistrements_crees = 0
                erreurs = []
                
                # Enregistrer les maladies endémiques
                for id_indicateur, maladie in donnees_maladies.items():
                    if maladie['cas'] > 0 or maladie['décès'] > 0:
                        try:
                            executer_requete(
                                """
                                INSERT INTO Enregistrement 
                                (numéro_TLOH, date_début, date_fin, institution, 
                                    communauté, notifié, décès, 
                                    cas, isolé, service)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)                                """,
                                (
                                    numéro_TLOH, date_début, date_fin, 0,
                                    0, 0, maladie['décès'],
                                    maladie['cas'], 0,
                                    service                            
                                )
                            )
                            enregistrements_crees += 1
                        except Exception as e:
                            erreurs.append(f"Maladie {maladie['nom']}: {e}")
                
                # Enregistrer les maladies tropicales négligées
                for id_indicateur, maladie in donnees_tropicales.items():
                    if maladie['notifié'] > 0 or maladie['isolé'] > 0:
                        try:
                            executer_requete(
                                """
                                INSERT INTO Enregistrement 
                                (numéro_TLOH, date_début, date_fin, institution, 
                                    communauté, notifié, décès, 
                                    cas, isolé, service)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    numéro_TLOH, date_début, date_fin, 0,
                                    0, maladie['notifié'], 0,
                                    0, maladie['isolé'],
                                    service
                                )
                            )
                            enregistrements_crees += 1
                        except Exception as e:
                            erreurs.append(f"Maladie tropicale {maladie['nom']}: {e}")
                
                # Enregistrer les décès
                for id_indicateur, décès in donnees_décès.items():
                    if décès['institution'] > 0 or décès['communauté'] > 0:
                        try:
                            executer_requete(
                                """
                                INSERT INTO Enregistrement 
                                (numéro_TLOH, date_début, date_fin, institution, 
                                    communauté, notifié, décès, 
                                    cas, isolé, service)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    numéro_TLOH, date_début, date_fin, décès['institution'],
                                    décès['communauté'], 0, décès['total_décès'],
                                    0, 0,
                                    service
                                )
                            )
                            enregistrements_crees += 1
                        except Exception as e:
                            erreurs.append(f"Décès {décès['nom']}: {e}")
                
                if enregistrements_crees > 0:
                    st.success(f"TLOH {numéro_TLOH} enregistré avec succès! ({enregistrements_crees} indicateurs)")
                    
                    if erreurs:
                        st.warning(f"Certains enregistrements ont échoué: {', '.join(erreurs)}")
                    
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("Aucune donnée à enregistrer (tous les champs sont à 0)")
                    if erreurs:
                        st.error(f"Erreurs d'enregistrement: {', '.join(erreurs)}")
                    
            except Exception as e:
                st.error(f"Erreur générale lors de l'enregistrement: {e}")

# ============================================
# 7. PAGE DE SURVEILLANCE ÉPIDÉMIOLOGIQUE AVEC FILTRES
# ============================================
def page_surveillance_epidemiologique():
    """Page de surveillance épidémiologique avec système de filtres"""
    st.title("Surveillance Épidémiologique")
    
    # Section de filtres
    st.markdown('<div class="section-filtres">', unsafe_allow_html=True)
    st.subheader("Filtres de recherche")
    
    colonne1, colonne2, colonne3 = st.columns(3)
    
    with colonne1:
        # Filtre par numéro TLOH
        numéro_tloh = st.text_input("Numéro TLOH", placeholder="Tous les numéros")
    
    with colonne2:
        # Filtre par année
        annee = st.selectbox("Année", ["Toutes les années"] + Configuration.ANNEES)
    
    with colonne3:
        # Filtre par service
        service = st.selectbox("Service", ["Tous les services"] + Configuration.SERVICES)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Construire les conditions WHERE
    conditions = []
    parametres = []
    
    if numéro_tloh:
        conditions.append("numéro_TLOH LIKE %s")
        parametres.append(f"%{numéro_tloh}%")
    
    if annee != "Toutes les années":
        conditions.append("YEAR(date_début) = %s")
        parametres.append(annee)
    
    if service != "Tous les services":
        conditions.append("service = %s")
        parametres.append(service)
    
    clause_where = " AND ".join(conditions) if conditions else "1=1"
    
    # Section 1: Maladies endémiques
    st.markdown('<h3 class="sous-titre">Maladies Endémiques</h3>', unsafe_allow_html=True)
    
    try:
        # Récupérer les maladies endémiques pour afficher la liste
        requete_endemiques_liste = """
            SELECT idIndicateur, nom 
            FROM Indicateur 
            WHERE type = 'Maladie endemique'
            ORDER BY nom
        """
        maladies_endemiques_liste = executer_requete(requete_endemiques_liste, fetch=True)
        
        if maladies_endemiques_liste:
            # Pour chaque maladie endémique, afficher les statistiques
            donnees_endemiques = []
            
            for maladie in maladies_endemiques_liste:
                # Requête pour les statistiques de cette maladie spécifique
                requete_maladie = f"""
                SELECT 
                    %s AS indicateur,
                    IFNULL(SUM(cas), 0) AS cas,
                    IFNULL(SUM(décès), 0) AS décès
                FROM Enregistrement
                WHERE {clause_where}
                """
                # Note: Comme il n'y a plus de lien avec la table Indicateur, 
                # on ne peut pas filtrer par maladie spécifique
                resultat_maladie = executer_requete(requete_maladie, tuple(parametres + [maladie['nom']]), fetch=True)
                
                if resultat_maladie and len(resultat_maladie) > 0:
                    donnees_endemiques.append(resultat_maladie[0])
            
            if donnees_endemiques:
                df_endemiques = pd.DataFrame(donnees_endemiques)
                st.dataframe(df_endemiques, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour les maladies endémiques")
        else:
            st.info("Aucune maladie endémique définie dans la base")
            
    except Exception as erreur:
        st.error(f"Erreur lors de la récupération des données: {erreur}")
    
    st.divider()
    
    # Section 2: Maladies tropicales négligées
    st.markdown('<h3 class="sous-titre">Maladies tropicales négligées</h3>', unsafe_allow_html=True)
    
    try:
        # Récupérer les maladies tropicales pour afficher la liste
        requete_tropicales_liste = """
            SELECT idIndicateur, nom 
            FROM Indicateur 
            WHERE type = 'maladies tropicales négligées'
            ORDER BY nom
        """
        maladies_tropicales_liste = executer_requete(requete_tropicales_liste, fetch=True)
        
        if maladies_tropicales_liste:
            # Pour chaque maladie tropicale, afficher les statistiques
            donnees_tropicales = []
            
            for maladie in maladies_tropicales_liste:
                # Requête pour les statistiques de cette maladie spécifique
                requete_maladie = f"""
                SELECT 
                    %s AS indicateur,
                    IFNULL(SUM(notifié), 0) AS notifié,
                    IFNULL(SUM(isolé), 0) AS isolé
                FROM Enregistrement
                WHERE {clause_where}
                """
                resultat_maladie = executer_requete(requete_maladie, tuple(parametres + [maladie['nom']]), fetch=True)
                
                if resultat_maladie and len(resultat_maladie) > 0:
                    donnees_tropicales.append(resultat_maladie[0])
            
            if donnees_tropicales:
                df_tropicales = pd.DataFrame(donnees_tropicales)
                st.dataframe(df_tropicales, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour les maladies tropicales négligées")
        else:
            st.info("Aucune maladie tropicale négligée définie dans la base")
            
    except Exception as erreur:
        st.error(f"Erreur lors de la récupération des données: {erreur}")
    
    st.divider()
    
    # Section 3: Décès
    st.markdown('<h3 class="sous-titre">Décès</h3>', unsafe_allow_html=True)
    
    try:
        # Récupérer les types de décès pour afficher la liste
        requete_deces_liste = """
            SELECT idIndicateur, nom 
            FROM Indicateur 
            WHERE type = 'décès'
            ORDER BY nom
        """
        types_deces_liste = executer_requete(requete_deces_liste, fetch=True)
        
        if types_deces_liste:
            # Pour chaque type de décès, afficher les statistiques
            donnees_deces = []
            
            for type_deces in types_deces_liste:
                # Requête pour les statistiques de ce type de décès spécifique
                requete_deces = f"""
                SELECT 
                    %s AS indicateur,
                    IFNULL(SUM(institution), 0) AS institution,
                    IFNULL(SUM(communauté), 0) AS communauté,
                    IFNULL(SUM(décès), 0) AS décès
                FROM Enregistrement
                WHERE {clause_where}
                """
                resultat_deces = executer_requete(requete_deces, tuple(parametres + [type_deces['nom']]), fetch=True)
                
                if resultat_deces and len(resultat_deces) > 0:
                    donnees_deces.append(resultat_deces[0])
            
            if donnees_deces:
                df_décès = pd.DataFrame(donnees_deces)
                st.dataframe(df_décès, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour les décès")
        else:
            st.info("Aucun type de décès défini dans la base")
            
    except Exception as erreur:
        st.error(f"Erreur lors de la récupération des données: {erreur}")

# ============================================
# 8. PAGE D'AJOUT D'INDICATEUR (CORRIGÉE)
# ============================================
def page_ajout_indicateur():
    """Page pour ajouter un nouvel indicateur"""
    st.title("Ajout d'indicateur")
    
    with st.form("formulaire_ajout_indicateur"):
        st.subheader("Nouvel indicateur")
        
        colonne1, colonne2 = st.columns(2)
        
        with colonne1:
            nom_indicateur = st.text_input("Nom de l'indicateur*", 
                                         help="Nom complet de l'indicateur")
        
        with colonne2:
            type_indicateur = st.selectbox("Type d'indicateur*", 
                                         Configuration.TYPES_INDICATEUR,
                                         help="Sélectionnez le type d'indicateur")
        
        bouton_valider = st.form_submit_button("Ajouter l'indicateur", type="primary", use_container_width=True,
                                              help="Cliquez pour ajouter le nouvel indicateur")
        
        if bouton_valider:
            if not nom_indicateur:
                st.error("Le nom de l'indicateur est obligatoire")
            else:
                try:
                    # Vérifier si l'indicateur existe déjà
                    requete_verification = """
                        SELECT COUNT(*) as count 
                        FROM Indicateur 
                        WHERE nom = %s AND type = %s
                    """
                    resultat = executer_requete(requete_verification, (nom_indicateur, type_indicateur), fetch=True)
                    
                    if resultat and resultat[0]['count'] > 0:
                        st.error(f"Cet indicateur existe déjà dans la base de données")
                    else:
                        # Insérer le nouvel indicateur - ne pas spécifier idIndicateur (AUTO_INCREMENT)
                        requete_insertion = """
                            INSERT INTO Indicateur (nom, type)
                            VALUES (%s, %s)
                        """
                        parametres = (nom_indicateur, type_indicateur)
                        
                        rows_affected = executer_requete(requete_insertion, parametres)
                        if rows_affected is not None and rows_affected > 0:
                            st.success(f"Indicateur '{nom_indicateur}' ajouté avec succès!")
                        else:
                            st.error("Erreur lors de l'ajout de l'indicateur")
                        
                except Exception as erreur:
                    st.error(f"Erreur lors de l'ajout de l'indicateur: {erreur}")

# ============================================
# 9. PAGE DE GESTION DES UTILISATEURS (CORRIGÉE)
# ============================================
def page_gestion_utilisateurs():
    """Page de gestion des utilisateurs"""
    st.title("Gestion des utilisateurs")
    
    # Formulaire d'ajout d'utilisateur
    with st.form("formulaire_ajout_utilisateur"):
        st.subheader("Ajouter un nouvel utilisateur")
        
        colonne1, colonne2 = st.columns(2)
        with colonne1:
            nom = st.text_input("Nom*")
        with colonne2:
            prenom = st.text_input("Prénom*")
        
        colonne1, colonne2 = st.columns(2)
        with colonne1:
            identifiant = st.text_input("Identifiant*")
            statut = st.selectbox("Statut*", ["Administrateur", "Utilisateur"])
        with colonne2:
            mot_de_passe = st.text_input("Mot de passe*", type="password")
            confirmer_mot_de_passe = st.text_input("Confirmer mot de passe*", type="password")
        
        bouton_valider = st.form_submit_button("Ajouter utilisateur", type="primary", use_container_width=True,
                                              help="Cliquez pour ajouter le nouvel utilisateur")
        
        if bouton_valider:
            if not all([nom, prenom, identifiant, mot_de_passe, confirmer_mot_de_passe]):
                st.error("Veuillez remplir tous les champs obligatoires (*)")
            elif mot_de_passe != confirmer_mot_de_passe:
                st.error("Les mots de passe ne correspondent pas")
            else:
                try:
                    # Vérifier si l'utilisateur existe déjà
                    requete_verification = """
                        SELECT COUNT(*) as count 
                        FROM Utilisateur 
                        WHERE identifiant = %s
                    """
                    resultat = executer_requete(requete_verification, (identifiant,), fetch=True)
                    
                    if resultat and resultat[0]['count'] > 0:
                        st.error(f"Cet identifiant existe déjà")
                    else:
                        # Insérer le nouvel utilisateur - ne pas spécifier idUtilisateur (AUTO_INCREMENT)
                        requete_insertion = """
                            INSERT INTO Utilisateur (nom, prenom, identifiant, mot_de_passe, statut)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        parametres = (nom, prenom, identifiant, mot_de_passe, statut)
                        
                        rows_affected = executer_requete(requete_insertion, parametres)
                        if rows_affected is not None and rows_affected > 0:
                            st.success(f"Utilisateur {identifiant} ajouté avec succès!")
                        else:
                            st.error("Erreur lors de l'ajout de l'utilisateur")
                        
                except Exception as erreur:
                    st.error(f"Erreur lors de l'ajout de l'utilisateur: {erreur}")
    
    st.divider()
    
    # Liste des utilisateurs
    st.subheader("Liste des utilisateurs")
    try:
        requete_utilisateurs = """
            SELECT idUtilisateur, nom, prenom, identifiant, statut
            FROM Utilisateur
            ORDER BY nom, prenom
        """
        utilisateurs = executer_requete(requete_utilisateurs, fetch=True)
        
        if utilisateurs:
            dataframe_utilisateurs = pd.DataFrame(utilisateurs)
            st.dataframe(dataframe_utilisateurs, use_container_width=True)
        else:
            st.info("Aucun utilisateur trouvé")
            
    except Exception as erreur:
        st.error(f"Erreur lors de la récupération des utilisateurs: {erreur}")

# ============================================
# 10. CSS PERSONNALISÉ
# ============================================
st.markdown("""
    <style>
    .titre-principal {
        font-size: 2.8rem;
        font-weight: 800;
        color: #006400;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .titre-epidemio {
        font-size: 2.5rem;
        color: #006400;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 700;
    }
    
    .sous-titre {
        font-size: 1.5rem;
        color: #228B22;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #228B22;
        padding-bottom: 0.5rem;
    }
    
    /* Boutons verts personnalisés */
    .stButton > button:first-child {
        background-color: #228B22 !important;
        color: white !important;
        border: 1px solid #1C6B1C !important;
    }
    
    .stButton > button:first-child:hover {
        background-color: #1C6B1C !important;
        border-color: #155015 !important;
    }
    
    /* Désactiver le bouton quand il y a des erreurs */
    .stButton > button:disabled {
        background-color: #cccccc !important;
        color: #666666 !important;
        border-color: #999999 !important;
    }
    
    .btn-primaire {
        background-color: #006400 !important;
        color: white !important;
        border: none !important;
    }
    
    .btn-success {
        background-color: #228B22 !important;
        color: white !important;
        border: none !important;
    }
    
    .boite-info {
        background-color: #e6f7e6;
        border-left: 4px solid #228B22;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }
    
    .section-filtres {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        border: 1px solid #ddd;
    }
    
    .conteneur-tableau {
        margin: 1rem 0;
        overflow-x: auto;
    }
    
    .dataframe th {
        background-color: #228B22;
        color: white;
        padding: 10px;
        text-align: left;
        font-weight: bold;
    }
    
    .dataframe td {
        padding: 10px;
        border-bottom: 1px solid #ddd;
    }
    
    .dataframe tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    
    .dataframe tr:hover {
        background-color: #e6ffe6;
    }
    
    /* Message d'erreur pour validation */
    .stAlert {
        border-left: 4px solid #ff4b4b;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# 11. MENU LATERAL
# ============================================
def menu_lateral():
    """Menu de navigation latéral"""
    with st.sidebar:
        st.title("Navigation")
        
        # Navigation principale
        st.subheader("Gestion TLOH")
        
        if st.button("Tableau de bord", use_container_width=True):
            st.session_state['page_actuelle'] = 'accueil'
            st.rerun()
        
        if st.button("Nouvel enregistrement", use_container_width=True):
            st.session_state['page_actuelle'] = 'enregistrement'
            st.rerun()
        
        st.divider()
        
        # Gestion (admin seulement)
        if st.session_state.get('role_utilisateur') == 'Administrateur':
            st.subheader("Administration")
            
            if st.button("Surveillance épidémiologique", use_container_width=True):
                st.session_state['page_actuelle'] = 'surveillance'
                st.rerun()
            
            if st.button("Ajouter un indicateur", use_container_width=True):
                st.session_state['page_actuelle'] = 'ajout_indicateur'
                st.rerun()
            
            if st.button("Gérer utilisateurs", use_container_width=True):
                st.session_state['page_actuelle'] = 'gestion_utilisateurs'
                st.rerun()
        
        st.divider()
        
        # Déconnexion
        if st.button("Déconnexion", use_container_width=True):
            for cle in list(st.session_state.keys()):
                del st.session_state[cle]
            st.rerun()

# ============================================
# 12. FONCTION PRINCIPALE
# ============================================
def main():
    """Fonction principale de l'application"""
    
    # Initialiser la session
    if 'authentifie' not in st.session_state:
        st.session_state['authentifie'] = False
    if 'page_actuelle' not in st.session_state:
        st.session_state['page_actuelle'] = 'accueil'
    if 'identifiant' not in st.session_state:
        st.session_state['identifiant'] = ''
    if 'role_utilisateur' not in st.session_state:
        st.session_state['role_utilisateur'] = 'Utilisateur'
    if 'id_utilisateur' not in st.session_state:
        st.session_state['id_utilisateur'] = None
    if 'nom_complet' not in st.session_state:
        st.session_state['nom_complet'] = ''
    
    # Configuration de la page
    st.set_page_config(
        page_title=Configuration.TITRE_PAGE,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Gestion de l'authentification
    if not st.session_state['authentifie']:
        page_connexion()
    else:
        # Afficher le menu
        menu_lateral()
        
        # Gestion des pages
        pages = {
            'accueil': page_accueil,
            'enregistrement': page_nouvel_enregistrement,
            'surveillance': page_surveillance_epidemiologique,
            'ajout_indicateur': page_ajout_indicateur,
            'gestion_utilisateurs': page_gestion_utilisateurs,
        }
        
        # Afficher la page actuelle
        page_actuelle = st.session_state.get('page_actuelle', 'accueil')
        fonction_page = pages.get(page_actuelle, page_accueil)
        fonction_page()

# ============================================
# 13. POINT D'ENTRÉE
# ============================================
if __name__ == "__main__":

    main()

