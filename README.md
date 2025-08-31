# 🚗 Solution Factory – RoboticA
## 📌 Objectif général

Ces challenges visent à développer pas à pas un robot autonome basé sur une **Raspberry Pi**, des **capteurs infrarouges**, un **capteur ultrason**, et une **caméra**.
Chaque étape introduit une difficulté supplémentaire afin de renforcer la maîtrise du **suivi de ligne**, de la **détection** et de l’**évitement d’obstacles**.

---

## 🔹 Challenge 1 – Suivi de ligne simple

* **Objectif** : Faire suivre une piste au robot de manière fluide.
* **Moyens** :

  * Utilisation des **capteurs infrarouges (IR)**.
  * Élaboration d’un **tableau des états** des capteurs IR.
  * Détermination de la direction du **servomoteur** et de la vitesse du **moteur DC** en fonction des capteurs.

---

## 🔹 Challenge 2 – Suivi de ligne avec boucle et intersection

* **Objectif** : Suivre une piste en **boucle** avec des intersections.
* **Moyens** :

  * Reprise et adaptation du **tableau des états des capteurs IR** (cas de 0 et 1).
  * Ajustement des vitesses moteurs et de l’orientation pour gérer les intersections.

---

## 🔹 Challenge 3 – Suivi de ligne avec discontinuités

* **Objectif** : Suivre une piste en boucle même lorsque la **ligne est interrompue**.
* **Moyens** :

  * Mise en œuvre d’une logique de **prédiction de trajectoire** lorsque les capteurs IR ne détectent plus la ligne.
  * Maintenir la direction jusqu’à retrouver la ligne.

---

## 🔹 Challenge 4 – Suivi de ligne et arrêt devant obstacle

* **Objectif** : Suivre la ligne et **s’arrêter automatiquement** devant un obstacle situé à **10 cm**.
* **Moyens** :

  * Utilisation du **capteur ultrason** pour mesurer la distance.
  * Arrêt des moteurs dès qu’un obstacle est détecté à moins de 10 cm.

---

## 🔹 Challenge 5 – Suivi de ligne et évitement d’obstacles

* **Objectif** :

  * Suivre la ligne (IR).
  * Détecter un obstacle (ultrason).
  * **Contourner l’obstacle** puis reprendre la ligne.
* **Moyens** :

  * Combinaison capteurs IR + ultrason.
  * Mise en place d’une séquence d’évitement puis retour sur la piste.

---

## 🔹 Challenge 6 – Détection de couleur des obstacles

* **Objectif** :

  * Suivi de ligne (IR).
  * Arrêt devant un obstacle (ultrason).
  * **Identifier la couleur** de l’obstacle avec la caméra.
* **Moyens** :

  * Capteurs IR + ultrason + **traitement d’image** (détection de couleur via caméra Raspberry Pi).

---

## 🔹 Challenge avancé - labyrinthe

* Mise en situation dans un **labyrinthe**.
* Maintien d’une distance avec les murs (20–30 cm, ultrason).
* Détection de **flèches directionnelles** (caméra).
* Commande du robot pour trouver la sortie.
