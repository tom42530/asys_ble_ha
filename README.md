#  intégration de gestion de piscine connectée Blueswim EO, Precise'o, Filtreo BLE pour Home Assistant 

![hassfest_workflow](https://github.com/tom42530/asys_ble_ha/actions/workflows/hassfest.yml/badge.svg)
![release_workflow](https://github.com/tom42530/asys_ble_ha/actions/workflows/release.yml/badge.svg)
![hacs_validate_workflow](https://github.com/tom42530/asys_ble_ha/actions/workflows/validate.yml/badge.svg)
[![Dernière release](https://img.shields.io/github/v/release/tom42530/asys_ble_ha)](https://github.com/tom42530/asys_ble_ha/releases)

Cette intégration permet de surveiller et de contrôler des systèmes Bluetooth Low Energy (BLE), comme le Precise'o+ d’Asys, directement depuis [Home Assistant](https://www.home-assistant.io/).

Après l'installation, aucune configuration n'est requise.
Vous pouvez utiliser un [proxy Bluetooth ESPHome](https://esphome.io/components/bluetooth_proxy.html) pour étendre la portée de la couverture Bluetooth.

![dashboard](https://github.com/user-attachments/assets/76d722d7-45da-44a7-927a-eff7f493be9d)



* [Fonctionnalités](#Fonctionnalités)
  * [Controles](#Controles)
  * [Capteurs](#Capteurs)
  * [Diagnostiques](#Diagnostiques)
  * [Configuration](#Configuration)
* [Appareils compatibles](#Appareils-compatibles)
* [Installation](#installation)
* [Surrimer l'intégration](#Supprimer-lintégration)
* [Dépannage](#Dépannage)
    * [Problèmes connus](#Problèmes-connus)
    * [Obtenir de l'aide](#Si-vous-rencontrez-des-problèmes-pour-lesquels-vous-souhaitez-obtenir-de-laide)
* [FAQ](FAQ)
* [Thanks to](#thanks-to)

## Fonctionnalités

### Controles
* On/off/auto de la filtration.
* Selection du mode de filtration (loi d'eau, mode personnalisé été/hiver, horloge 72h et horloge usine 1,2 et 3).
* On/off Lumière.
* Changement de couleur (mode standard).

### Capteurs
* Consommation de la pompe en WH, inexistant dans le system intial il a été ajouté afin que vous puissiez l'intégrer facilement dans votre dashboard Energy de home assistant.
* Intensité de la pompe en A (ampère)
* Nombre de cycle total effectué.
* Filtration (en cours d'exécution/ A l'arret)
* Runtime (temps total de fonctionnement en heure de la pompe)
* Température de l'air en °C
* Température de l'eau en °C

### Diagnostiques
* Protection de surcharge (en cours d'éxécution/ a l'arret)
* Filtration hors gel (en cours d'éxécution/ a l'arret)
* Statut pairage.
* Force du signal bleutooth en dB.
* Qualité de la liaison en %.

### Configuration
* Personnalisation de l'intervalle de rafraîchissement.

## Appareils compatibles
- Precise'o+
- Precise'o
- Blueswim EO


## Installation
Blueswim EO & precise'o est un dépôt par défaut dans HACS.
Veuillez suivre les [instructions d’utilisation de HACS](https://hacs.xyz/docs/use/) si vous ne l’avez pas encore installé.
Pour ajouter l’intégration à votre instance Home Assistant, utilisez ce bouton My :

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tom52530&repository=asys_ble_ha&category=Integration)

<details><summary>Étapes d'installation manuelle</summary>

1. À l’aide de l’outil de votre choix, ouvrez le dossier de configuration de Home Assistant (celui contenant le fichier `configuration.yaml`).
2. Si vous n’avez pas de dossier `custom_components`, vous devez le créer.
3. Dans ce dossier `custom_components`, créez un nouveau dossier nommé `asys_ble`.
4. Téléchargez **tous** les fichiers du répertoire `custom_components/asys_ble/` de ce dépôt.
5. Placez les fichiers téléchargés dans le nouveau dossier `bms_ble` que vous venez de créer.
6. Redémarrez Home Assistant.
7. Dans l’interface utilisateur de Home Assistant, allez dans <a href="https://my.home-assistant.io/redirect/integrations">Configuration > Intégrations</a>, cliquez sur <a href="https://my.home-assistant.io/redirect/config_flow_start?domain=asys_ble">+ Ajouter une intégration</a> et [recherchez](https://my.home-assistant.io/redirect/config_flow_start/?domain=asys_ble) «Blueswim EO».
</details>

## Supprimer l'intégration
Cette intégration suit la procédure standard de suppression. Aucune étape supplémentaire n’est requise.  
<details><summary>Pour supprimer une instance de l’intégration dans Home Assistant</summary>

1. Allez dans <a href="https://my.home-assistant.io/redirect/integrations">Paramètres > Appareils et services</a> et sélectionnez la carte de l’intégration.  
2. Dans la liste des appareils, sélectionnez l’instance de l’intégration que vous souhaitez supprimer.  
3. À côté de l’entrée, cliquez sur le menu à trois points, puis sélectionnez **Supprimer**.

</details>

## Dépannage

> [!NOTE]
> De nombreux problèmes temporaires sont liés aux adaptateurs Bluetooth.
L’exemple le plus courant est la limitation de performances de l’[adaptateur Bluetooth interne du Raspberry Pi](https://www.home-assistant.io/integrations/bluetooth/#cypress-based-adapters), qui peut entraîner, par exemple, des données incorrectes lorsque plusieurs appareils sont utilisés.
Nous vous recommandons de consulter la page de l’intégration Bluetooth de Home Assistant pour connaître les problèmes connus, et d’envisager l’utilisation d’un [adaptateur hautes performances recommandé](https://www.home-assistant.io/integrations/bluetooth/#known-working-high-performance-adapters).

### Problèmes connus



### Si vous rencontrez des problèmes pour lesquels vous souhaitez obtenir de l’aide

- Activer [le protocole de debug](https://www.home-assistant.io/docs/configuration/troubleshooting/#debug-logs-and-diagnostics),
- Redémarrez Home Assistant, puis attendez qu’il soit complètement démarré,
- Reproduire le problème,
- Désactivez le journal (Home Assistant vous invitera à télécharger le journal), puis enfin
- [Ouvrir une issue](https://github.com/tom42530/asys_ble_ha/issues/new?assignees=&labels=question&projects=&template=support.yml) avec une bonne description de votre question/problème, et en joignant le journal, ou
- [Ouvrir un bug](https://github.com/tom42530/asys_ble_ha/issues/new?assignees=&labels=Bug&projects=&template=bug.yml) si vous pensez que le comportement observé est causé par l’intégration, incluez une bonne description de ce qui s’est passé, vos attentes, et joignez le journal.


## FAQ
### les contrôles sont grisés
Cela signifie que le périphérique BLE n’est pas correctement appairé. Certaines caractéristiques ne peuvent pas être lues si l’authentification n’est pas effectuée. Veuillez appuyer sur le bouton d’appairage sur l’appareil.
Vous pouvez aussi vérifier dans la partie diagnotic que le statut pairing est à ok.


## Thanks to

[Daelle84](https://github.com/Daelle84)

[tom42530](https://github.com/tom42530)
