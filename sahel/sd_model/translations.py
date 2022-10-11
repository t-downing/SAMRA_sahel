def l(word: str, language: str):
    print(locals())
    FR = "FR"
    dictionary = {
        "Evidence Bit": {FR: "Information Qualitative"},
        "Upstream Element": {FR: "Éléments en Amont"},
        "Layer": {FR: "Couche"},
        "Color": {FR: "Couleur"},
        "Storyline": {FR: "Histoires"},
        "Download": {FR: "Télécharger"},
        "Add an Object": {FR: "Ajouter un objet"},
        "Add an EB": {FR: "Ajouter un 'EB'"},
        "Group": {FR: "Groupe"},
        "Variable":  {FR: "Variable"},
        "Indicator": {FR: "Indicateur"},
        "Delete": {FR: "Supprimer"},
        "Element": {FR: "Élément"},
        "Add": {FR: "Ajouter"},
        "Submit": {FR: "Saisir"},
        "Sector": {FR: "Secteur"}
    }
    translations = dictionary.get(word)
    if translations is None:
        return word
    else:
        translated_word = translations.get(language)
        return translated_word if translated_word is not None else word
