"""Word lists for bilingual learning products: the figure names, colours, days, seasons, feelings and opposites in Spanish, French and German.
Short, common words only. English is the source; a missing word falls back to English rather than guessing."""
from __future__ import annotations

LANGS = {"en": "English", "es": "Spanish", "fr": "French", "de": "German"}

_NAMES = """cat|gato|chat|Katze
fish|pez|poisson|Fisch
butterfly|mariposa|papillon|Schmetterling
turtle|tortuga|tortue|Schildkröte
owl|búho|hibou|Eule
snail|caracol|escargot|Schnecke
ladybug|mariquita|coccinelle|Marienkäfer
whale|ballena|baleine|Wal
octopus|pulpo|pieuvre|Krake
rocket|cohete|fusée|Rakete
car|coche|voiture|Auto
robot|robot|robot|Roboter
dinosaur|dinosaurio|dinosaure|Dinosaurier
flower|flor|fleur|Blume
house|casa|maison|Haus
ice cream|helado|glace|Eis
frog|rana|grenouille|Frosch
bunny|conejo|lapin|Hase
bear|oso|ours|Bär
penguin|pingüino|pingouin|Pinguin
duck|pato|canard|Ente
elephant|elefante|éléphant|Elefant
giraffe|jirafa|girafe|Giraffe
lion|león|lion|Löwe
bee|abeja|abeille|Biene
crab|cangrejo|crabe|Krabbe
shark|tiburón|requin|Hai
airplane|avión|avion|Flugzeug
sailboat|velero|voilier|Segelboot
train|tren|train|Zug
cupcake|magdalena|cupcake|Cupcake
mushroom|seta|champignon|Pilz
unicorn|unicornio|licorne|Einhorn
pizza|pizza|pizza|Pizza
apple|manzana|pomme|Apfel
flying saucer|platillo volante|soucoupe volante|fliegende Untertasse
planet|planeta|planète|Planet
balloons|globos|ballons|Luftballons
pumpkin|calabaza|citrouille|Kürbis
ghost|fantasma|fantôme|Gespenst
bat|murciélago|chauve-souris|Fledermaus
witch hat|sombrero de bruja|chapeau de sorcière|Hexenhut
Christmas tree|árbol de Navidad|sapin de Noël|Weihnachtsbaum
snowman|muñeco de nieve|bonhomme de neige|Schneemann
present|regalo|cadeau|Geschenk
candy cane|bastón de caramelo|sucre d'orge|Zuckerstange
Easter egg|huevo de Pascua|œuf de Pâques|Osterei
chick|pollito|poussin|Küken
fox|zorro|renard|Fuchs
hedgehog|erizo|hérisson|Igel
cow|vaca|vache|Kuh
pig|cerdo|cochon|Schwein
sheep|oveja|mouton|Schaf
dog|perro|chien|Hund
mouse|ratón|souris|Maus
panda|panda|panda|Panda
monkey|mono|singe|Affe
koala|koala|koala|Koala
horse|caballo|cheval|Pferd
seahorse|caballito de mar|hippocampe|Seepferdchen
starfish|estrella de mar|étoile de mer|Seestern
jellyfish|medusa|méduse|Qualle
dragon|dragón|dragon|Drache
castle|castillo|château|Burg
fairy|hada|fée|Fee
mermaid|sirena|sirène|Meerjungfrau
bicycle|bicicleta|vélo|Fahrrad
bus|autobús|bus|Bus
fire truck|camión de bomberos|camion de pompiers|Feuerwehrauto
helicopter|helicóptero|hélicoptère|Hubschrauber
tractor|tractor|tracteur|Traktor
hot air balloon|globo aerostático|montgolfière|Heißluftballon
rainbow|arcoíris|arc-en-ciel|Regenbogen
umbrella|paraguas|parapluie|Regenschirm
snowflake|copo de nieve|flocon de neige|Schneeflocke
sun|sol|soleil|Sonne
moon|luna|lune|Mond
kite|cometa|cerf-volant|Drachen
tree|árbol|arbre|Baum
heart|corazón|cœur|Herz
red|rojo|rouge|rot
blue|azul|bleu|blau
yellow|amarillo|jaune|gelb
green|verde|vert|grün
orange|naranja|orange|orange
purple|morado|violet|lila
pink|rosa|rose|rosa
brown|marrón|marron|braun
Monday|lunes|lundi|Montag
Tuesday|martes|mardi|Dienstag
Wednesday|miércoles|mercredi|Mittwoch
Thursday|jueves|jeudi|Donnerstag
Friday|viernes|vendredi|Freitag
Saturday|sábado|samedi|Samstag
Sunday|domingo|dimanche|Sonntag
Spring|Primavera|Printemps|Frühling
Summer|Verano|Été|Sommer
Autumn|Otoño|Automne|Herbst
Winter|Invierno|Hiver|Winter
happy|feliz|heureux|glücklich
sad|triste|triste|traurig
angry|enojado|en colère|wütend
surprised|sorprendido|surpris|überrascht
sleepy|soñoliento|endormi|müde
scared|asustado|effrayé|ängstlich
big|grande|grand|groß
small|pequeño|petit|klein
tall|alto|grand|hoch
short|bajo|petit|niedrig
day|día|jour|Tag
night|noche|nuit|Nacht
hot|caliente|chaud|heiß
cold|frío|froid|kalt
full|lleno|plein|voll
empty|vacío|vide|leer
open|abierto|ouvert|offen
closed|cerrado|fermé|geschlossen
fast|rápido|rapide|schnell
slow|lento|lent|langsam"""

TR: dict[str, dict[str, str]] = {"es": {}, "fr": {}, "de": {}}
for _line in _NAMES.splitlines():
    _en, _es, _fr, _de = _line.split("|")
    TR["es"][_en], TR["fr"][_en], TR["de"][_en] = _es, _fr, _de


def tr(word: str, lang: str = "en") -> str:
    """`word` in the language (English returns it unchanged; a word with no entry stays English)."""
    return word if lang == "en" else TR.get(lang, {}).get(word, word)


def check_lang(lang: str) -> str:
    if lang not in LANGS:
        raise ValueError(f"unknown language '{lang}'. Choose one of: {', '.join(LANGS)}")
    return lang
