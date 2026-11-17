import datetime as dt

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .attribution import generer_quadrimestre
from .creneaux import (
    postes_pour_date,
    semaines_du_mois,
    dates_quadrimestre,
)
from .jours_feries import est_ferie, jours_feries
from .models import (
    NIVEAU_ADMINISTRATEUR,
    NIVEAU_SUPERADMINISTRATEUR,
    NIVEAU_UTILISATEUR,
    Affectation,
    Disponibilite,
    Fermeture,
    Praticien,
)
from .services import (
    assigner,
    est_indisponible,
    stats_praticien,
    verifier_contraintes,
)


def _praticien(nom, **kwargs):
    defaults = dict(quote_part=100, type="P", dj=False, niveau=NIVEAU_UTILISATEUR)
    defaults.update(kwargs)
    return Praticien.objects.create(nom=nom, **defaults)


class JoursFeriesTests(TestCase):
    def test_paques_2026(self):
        # Paques 2026 = 5 avril 2026.
        feries = jours_feries(2026)
        self.assertIn(dt.date(2026, 4, 6), feries)    # lundi de Paques
        self.assertIn(dt.date(2026, 5, 14), feries)   # Ascension
        self.assertIn(dt.date(2026, 5, 25), feries)   # lundi de Pentecote
        self.assertIn(dt.date(2026, 1, 1), feries)
        self.assertIn(dt.date(2026, 12, 25), feries)
        self.assertNotIn(dt.date(2026, 4, 5), feries)  # dimanche de Paques non ferie

    def test_est_ferie(self):
        self.assertTrue(est_ferie(dt.date(2026, 7, 14)))
        self.assertFalse(est_ferie(dt.date(2026, 7, 15)))


class CreneauxTests(TestCase):
    def test_semaine_ouvrable(self):
        lundi = dt.date(2026, 1, 5)  # lundi
        codes = {(p.section, p.code, p.part) for p in postes_pour_date(lundi)}
        self.assertIn(("REANIMATION", "REA1", "journee"), codes)
        self.assertIn(("REANIMATION", "REA4", "demi"), codes)
        self.assertIn(("REANIMATION", "READJ", "journee"), codes)
        self.assertIn(("REANIMATION", "GARDE", "nuit"), codes)
        self.assertIn(("BLOC", "BLOC1", "matin"), codes)
        self.assertIn(("BLOC", "BLOC6", "aprem"), codes)
        self.assertIn(("CPA", "CPA", "matin"), codes)
        self.assertIn(("CONSULTATION", "PR", "matin"), codes)
        self.assertIn(("ASTREINTE", "AST", "journee"), codes)
        self.assertIn(("AI", "AI", "matin"), codes)
        self.assertIn(("CA", "CA", "aprem"), codes)
        # 6 vacations AI (3 matin + 3 aprem) et 6 CA
        ai = [p for p in postes_pour_date(lundi) if p.section == "AI"]
        ca = [p for p in postes_pour_date(lundi) if p.section == "CA"]
        self.assertEqual(len(ai), 6)
        self.assertEqual(len(ca), 6)

    def test_weekend(self):
        samedi = dt.date(2026, 1, 10)
        postes = postes_pour_date(samedi)
        codes = {(p.section, p.code, p.part) for p in postes}
        self.assertIn(("REANIMATION", "GARDE", "journee"), codes)
        self.assertIn(("ASTREINTE", "AST", "journee"), codes)
        self.assertNotIn(("BLOC", "BLOC1", "matin"), codes)
        garde = next(p for p in postes if p.code == "GARDE")
        ast = next(p for p in postes if p.section == "ASTREINTE")
        self.assertEqual(garde.heures, 24)
        self.assertEqual(ast.heures, 12)

    def test_jour_ferie_comme_weekend(self):
        fete = dt.date(2026, 5, 1)  # vendredi 1er mai
        codes = {(p.section, p.code) for p in postes_pour_date(fete)}
        self.assertIn(("REANIMATION", "GARDE"), codes)
        self.assertNotIn(("BLOC", "BLOC1"), codes)

    def test_bloc4(self):
        mercredi = dt.date(2026, 1, 7)
        lundi = dt.date(2026, 1, 5)
        b4_mercredi = [p for p in postes_pour_date(mercredi) if p.code == "BLOC4"]
        b4_lundi = [p for p in postes_pour_date(lundi) if p.code == "BLOC4"]
        self.assertTrue(all(p.assignable for p in b4_mercredi))
        self.assertTrue(all(not p.assignable for p in b4_lundi))

    def test_semaines_du_mois_lundi_dimanche(self):
        semaines = semaines_du_mois(2026, 2)  # fev 2026 commence un dimanche
        premier = semaines[0][0]
        dernier = semaines[-1][-1]
        self.assertEqual(premier.weekday(), 0)
        self.assertEqual(dernier.weekday(), 6)
        self.assertEqual(premier, dt.date(2026, 1, 26))
        self.assertEqual(dernier, dt.date(2026, 3, 1))
        for s in semaines:
            self.assertEqual(len(s), 7)

    def test_dates_quadrimestre(self):
        self.assertEqual(dates_quadrimestre(2026, 1)[0], dt.date(2026, 1, 1))
        self.assertEqual(dates_quadrimestre(2026, 1)[-1], dt.date(2026, 4, 30))
        self.assertEqual(dates_quadrimestre(2026, 3)[-1], dt.date(2026, 12, 31))


class ContraintesTests(TestCase):
    def setUp(self):
        self.lundi = dt.date(2026, 1, 5)
        self.mardi = dt.date(2026, 1, 6)
        self.vendredi = dt.date(2026, 1, 9)
        self.dimanche = dt.date(2026, 1, 11)
        self.p1 = _praticien("A")
        self.p2 = _praticien("B")

    def test_ca_exclusif(self):
        ok, err = assigner(self.lundi, ("CA", "CA", "matin", 0), self.p1)
        self.assertTrue(ok, err)
        ok, err = assigner(self.lundi, ("REANIMATION", "REA2", "journee", 0), self.p1)
        self.assertFalse(ok)
        self.assertTrue(any("CA" in e for e in err))
        # l'inverse : poste de travail puis CA -> refuse
        ok, err = assigner(self.lundi, ("REANIMATION", "REA2", "journee", 0), self.p2)
        self.assertTrue(ok, err)
        ok, err = assigner(self.lundi, ("CA", "CA", "aprem", 0), self.p2)
        self.assertFalse(ok)

    def test_ai_créneau_equivalent(self):
        ok, err = assigner(self.lundi, ("AI", "AI", "matin", 0), self.p1)
        self.assertTrue(ok, err)
        # conflit avec un poste du matin
        ok, err = assigner(self.lundi, ("BLOC", "BLOC2", "matin", 0), self.p1)
        self.assertFalse(ok)
        # pas de conflit avec l'apres-midi
        ok, err = assigner(self.lundi, ("BLOC", "BLOC2", "aprem", 0), self.p2)
        self.assertTrue(ok, err)
        # AI aprem bloque un poste aprem
        assigner(self.lundi, ("AI", "AI", "aprem", 0), self.p2)
        ok, err = assigner(self.lundi, ("CPA", "CPA", "aprem", 0), self.p2)
        self.assertFalse(ok)

    def test_lendemain_garde_interdit(self):
        ok, err = assigner(self.lundi, ("REANIMATION", "GARDE", "nuit", 0), self.p1)
        self.assertTrue(ok, err)
        ok, err = assigner(self.mardi, ("REANIMATION", "REA2", "journee", 0), self.p1)
        self.assertFalse(ok)
        self.assertTrue(any("veille" in e for e in err))
        # CA reste possible le lendemain (ce n'est pas un poste de travail)
        ok, err = assigner(self.mardi, ("CA", "CA", "matin", 0), self.p1)
        self.assertTrue(ok, err)

    def test_lendemain_astreinte_interdit(self):
        ok, err = assigner(self.lundi, ("ASTREINTE", "AST", "journee", 0), self.p1)
        self.assertTrue(ok, err)
        ok, err = assigner(self.mardi, ("KT", "KT", "matin", 0), self.p1)
        self.assertFalse(ok)

    def test_vendredi_dimanche_garde(self):
        ok, err = assigner(self.vendredi, ("REANIMATION", "GARDE", "nuit", 0), self.p1)
        self.assertTrue(ok, err)
        # propagation au dimanche
        dimanche_garde = Affectation.objects.get(
            date=self.dimanche, section="REANIMATION", code="GARDE"
        )
        self.assertEqual(dimanche_garde.praticien, self.p1)
        # tentative de changer le dimanche seul -> refuse
        ok, err = assigner(self.dimanche, ("REANIMATION", "GARDE", "journee", 0), self.p2)
        self.assertFalse(ok)

    def test_vendredi_dimanche_astreinte(self):
        ok, err = assigner(self.vendredi, ("ASTREINTE", "AST", "journee", 0), self.p1)
        self.assertTrue(ok, err)
        self.assertTrue(Affectation.objects.filter(
            date=self.dimanche, section="ASTREINTE", praticien=self.p1).exists())
        ok, err = assigner(self.dimanche, ("ASTREINTE", "AST", "journee", 0), self.p2)
        self.assertFalse(ok)

    def test_liens_groupes(self):
        # REA1 et garde : meme personne
        ok, err = assigner(self.lundi, ("REANIMATION", "GARDE", "nuit", 0), self.p1)
        self.assertTrue(ok, err)
        rea1 = Affectation.objects.get(date=self.lundi, section="REANIMATION", code="REA1")
        self.assertEqual(rea1.praticien, self.p1)
        # BLOC1 et BLOC6 matin/aprem : meme personne
        ok, err = assigner(self.lundi, ("BLOC", "BLOC1", "matin", 0), self.p2)
        self.assertTrue(ok, err)
        for code in ("BLOC1", "BLOC6"):
            for part in ("matin", "aprem"):
                a = Affectation.objects.get(date=self.lundi, section="BLOC", code=code, part=part)
                self.assertEqual(a.praticien, self.p2)
        # BLOC3 matin et aprem : personnes differentes possibles
        p3 = _praticien("C")
        p4 = _praticien("D")
        p5 = _praticien("E")
        ok, err = assigner(self.lundi, ("BLOC", "BLOC3", "matin", 0), p3)
        self.assertTrue(ok, err)
        # astreinte = bloc 3 aprem
        ok, err = assigner(self.lundi, ("BLOC", "BLOC3", "aprem", 0), p4)
        self.assertTrue(ok, err)
        ast = Affectation.objects.get(date=self.lundi, section="ASTREINTE", code="AST")
        self.assertEqual(ast.praticien, p4)
        # consultation PR = CPA aprem
        ok, err = assigner(self.lundi, ("CPA", "CPA", "aprem", 0), p5)
        self.assertTrue(ok, err)
        pr = Affectation.objects.get(date=self.lundi, section="CONSULTATION", code="PR")
        self.assertEqual(pr.praticien, p5)

    def test_dj_reserve(self):
        p_dj = _praticien("DJ", dj=True)
        ok, err = assigner(self.lundi, ("REANIMATION", "READJ", "journee", 0), self.p1)
        self.assertFalse(ok)
        ok, err = assigner(self.lundi, ("REANIMATION", "READJ", "journee", 0), p_dj)
        self.assertTrue(ok, err)

    def test_une_seule_vacation_par_jour(self):
        ok, err = assigner(self.lundi, ("REANIMATION", "REA2", "journee", 0), self.p1)
        self.assertTrue(ok, err)
        ok, err = assigner(self.lundi, ("BLOC", "BLOC2", "matin", 0), self.p1)
        self.assertFalse(ok)

    def test_indisponibilite(self):
        Disponibilite.objects.create(praticien=self.p1, date=self.lundi, part="journee",
                                     disponible=False)
        self.assertTrue(est_indisponible(self.p1, self.lundi, "matin"))
        self.assertTrue(est_indisponible(self.p1, self.lundi, "nuit"))
        self.assertFalse(est_indisponible(self.p1, self.mardi, "matin"))

    def test_fermeture_section(self):
        Fermeture.objects.create(date=self.lundi, section="BLOC")
        codes = {(p.section, p.code) for p in postes_pour_date(
            self.lundi, sections_fermees={"BLOC"})}
        self.assertNotIn(("BLOC", "BLOC1"), codes)


class StatsTests(TestCase):
    def test_stats_jours_et_heures(self):
        lundi = dt.date(2026, 1, 5)
        p = _praticien("A")
        assigner(lundi, ("REANIMATION", "REA2", "journee", 0), p)   # 10h, 1.0
        assigner(lundi, ("BLOC", "BLOC2", "matin", 0), p) if False else None
        # bloc2 matin + aprem sont lies : une seule personne, 2 x 0.5
        assigner(lundi, ("BLOC", "BLOC2", "matin", 0), _praticien("B"))
        s = stats_praticien(p, lundi, lundi)
        self.assertEqual(s["heures"], 10)
        self.assertEqual(s["journees"], 1.0)
        p2 = Praticien.objects.get(nom="B")
        s2 = stats_praticien(p2, lundi, lundi)
        self.assertEqual(s2["heures"], 11)   # 5.5 + 5.5
        self.assertEqual(s2["journees"], 1.0)  # 0.5 + 0.5


class GenerationTests(TestCase):
    def setUp(self):
        self.praticiens = []
        for i in range(8):
            self.praticiens.append(_praticien(
                f"P{i}", quote_part=100, type="L" if i % 2 else "P", dj=(i < 2)))

    def _verifier_invariants(self, annee, trimestre):
        from .services import verifier_contraintes, postes_date
        dates = dates_quadrimestre(annee, trimestre)
        for date in dates:
            postes = {p.cle: p for p in postes_date(date)}
            for a in Affectation.objects.filter(date=date):
                cle = (a.section, a.code, a.part, a.index)
                err = verifier_contraintes(date, cle, a.praticien, ignorer_cle=cle)
                self.assertEqual(err, [], f"{date} {cle} {a.praticien}: {err}")
                poste = postes.get(cle)
                if poste and poste.exige_dj:
                    self.assertTrue(a.praticien.dj)
            # liens de groupe coherents
            for poste in postes.values():
                if not poste.groupe or poste.section in ("AI", "CA"):
                    continue
                groupes = {}
                for p in postes.values():
                    if p.groupe == poste.groupe:
                        a = Affectation.objects.filter(
                            date=date, section=p.section, code=p.code, part=p.part,
                            index=p.index).first()
                        groupes[p.cle] = a.praticien_id if a else None
                valeurs = set(v for v in groupes.values() if v is not None)
                if len(valeurs) > 1:
                    self.fail(f"{date} groupe {poste.groupe} incoherent: {groupes}")

    def test_generation_q1_sans_violation(self):
        journal = generer_quadrimestre(2026, 1, auteur=None)
        self._verifier_invariants(2026, 1)
        # au moins quelques affectations ont ete posees
        self.assertGreater(Affectation.objects.count(), 500)
        self.assertTrue(journal.avertissements is not None)

    def test_generation_respecte_ca_manuel(self):
        lundi = dt.date(2026, 1, 5)
        p = self.praticiens[0]
        assigner(lundi, ("CA", "CA", "matin", 0), p)
        generer_quadrimestre(2026, 1)
        # p reste en CA et n'a aucun autre poste ce jour
        autres = Affectation.objects.filter(date=lundi, praticien=p).exclude(section="CA")
        self.assertEqual(autres.count(), 0)

    def test_generation_prend_en_compte_indisponibilite(self):
        lundi = dt.date(2026, 1, 5)
        p = self.praticiens[0]
        Disponibilite.objects.create(praticien=p, date=lundi, part="journee", disponible=False)
        generer_quadrimestre(2026, 1)
        self.assertEqual(
            Affectation.objects.filter(date=lundi, praticien=p).exclude(
                section__in=("AI", "CA")).count(), 0)


class PermissionsTests(TestCase):
    def setUp(self):
        self.user_visio = User.objects.create_user("visio", password="x")
        self.user_util = User.objects.create_user("util", password="x")
        self.user_admin = User.objects.create_user("admin2", password="x")
        self.user_super = User.objects.create_user("super", password="x")
        self.p_visio = _praticien("V", user=self.user_visio, niveau="VISIONNAGE")
        self.p_util = _praticien("U", user=self.user_util, niveau=NIVEAU_UTILISATEUR)
        self.p_admin = _praticien("A", user=self.user_admin, niveau=NIVEAU_ADMINISTRATEUR)
        self.p_super = _praticien("S", user=self.user_super, niveau=NIVEAU_SUPERADMINISTRATEUR)

    def test_planning_public_sans_connexion(self):
        r = self.client.get(reverse("planning_mois", args=[2026, 1]))
        self.assertEqual(r.status_code, 200)

    def test_stats_interdit_anonyme_et_visionnage(self):
        r = self.client.get(reverse("stats"))
        self.assertEqual(r.status_code, 302)  # redirection login
        self.client.login(username="visio", password="x")
        r = self.client.get(reverse("stats"))
        self.assertEqual(r.status_code, 403)
        self.client.login(username="util", password="x")
        r = self.client.get(reverse("stats"))
        self.assertEqual(r.status_code, 200)

    def test_praticiens_admin_seul(self):
        self.client.login(username="util", password="x")
        self.assertEqual(self.client.get(reverse("praticiens")).status_code, 403)
        self.client.login(username="admin2", password="x")
        self.assertEqual(self.client.get(reverse("praticiens")).status_code, 200)

    def test_accreditations_superadmin_seul(self):
        self.client.login(username="admin2", password="x")
        self.assertEqual(self.client.get(reverse("accreditations")).status_code, 403)
        self.client.login(username="super", password="x")
        r = self.client.get(reverse("accreditations"))
        self.assertEqual(r.status_code, 200)
        # monter "util" administrateur
        r = self.client.post(reverse("accreditations"),
                             {f"p{self.p_util.pk}-niveau": NIVEAU_ADMINISTRATEUR})
        self.assertEqual(r.status_code, 302)
        self.p_util.refresh_from_db()
        self.assertEqual(self.p_util.niveau, NIVEAU_ADMINISTRATEUR)

    def test_modification_poste_admin(self):
        lundi = dt.date(2026, 1, 5)
        self.client.login(username="util", password="x")
        r = self.client.post(reverse("modifier_poste", args=[2026, 1]), {
            "date": "2026-01-05", "section": "REANIMATION", "code": "REA2",
            "part": "journee", "index": 0, "praticien_id": self.p_util.pk,
        })
        self.assertEqual(r.status_code, 403)
        self.client.login(username="admin2", password="x")
        r = self.client.post(reverse("modifier_poste", args=[2026, 1]), {
            "date": "2026-01-05", "section": "REANIMATION", "code": "REA2",
            "part": "journee", "index": 0, "praticien_id": self.p_admin.pk,
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Affectation.objects.filter(
            date=lundi, section="REANIMATION", code="REA2",
            praticien=self.p_admin).exists())

    def test_generation_bouton_admin(self):
        self.client.login(username="admin2", password="x")
        r = self.client.post(reverse("generer_quadrimestre", args=[2026, 1]),
                             {"annee": 2026, "quadrimestre": 1})
        self.assertEqual(r.status_code, 302)
        self.assertGreater(Affectation.objects.count(), 0)

    def test_disponibilites_propre_compte(self):
        self.client.login(username="util", password="x")
        r = self.client.post(reverse("disponibilites"), {
            "annee": 2026, "mois": 1,
            "etat_2026-01-05": "indispo_journee",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Disponibilite.objects.filter(
            praticien=self.p_util, date=dt.date(2026, 1, 5),
            part="journee", disponible=False).exists())
