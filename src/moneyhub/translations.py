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
octopus|pulpo|pieuvre|Oktopus
rocket|cohete|fusée|Rakete
car|auto|voiture|Auto
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
cupcake|cupcake|cupcake|Cupcake
mushroom|hongo|champignon|Pilz
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
Spring|primavera|printemps|Frühling
Summer|verano|été|Sommer
Autumn|otoño|automne|Herbst
Winter|invierno|hiver|Winter
happy|feliz|heureux|glücklich
sad|triste|triste|traurig
angry|enojado|en colère|wütend
surprised|sorprendido|surpris|überrascht
sleepy|soñoliento|fatigué|müde
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


# --------------------------------------------------------------------------- review guardrail
# A bilingual product can only be marked ready when the word list has been checked: by an AI helper (shows as a warning, because an AI is not a native
# speaker) or signed off by a person (passes). Any edit to the word list changes its fingerprint and cancels earlier reviews.
import hashlib  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402

from pydantic import BaseModel, Field  # noqa: E402


def fingerprint(lang: str) -> str:
    items = sorted(TR.get(lang, {}).items())
    return hashlib.sha1(json.dumps(items, ensure_ascii=False).encode()).hexdigest()[:12]


def _review_file():
    from .config import get_config
    return get_config().output_dir / "translations-review.json"


def load_reviews() -> dict:
    f = _review_file()
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    f = _review_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class WordVerdict(BaseModel):
    english: str
    given: str
    ok: bool
    suggestion: str = Field(default="", description="The better word, only when ok is false")
    note: str = Field(default="", description="One short reason, only when ok is false")


class LangVerdicts(BaseModel):
    verdicts: list[WordVerdict]


def ai_check(lang: str, providers: list[str] | None = None) -> dict:
    """Ask the configured AI helper to proofread one language's word list. Returns {'checked': bool, 'issues': [...], 'source': str}.
    Nothing is changed in the word list; fixes are for you to apply."""
    check_lang(lang)
    from .llm import get_router
    router = get_router()
    pairs = [{"english": en, "given": t} for en, t in TR[lang].items()]
    system = ("You are a careful native-level proofreader of children's early-learning vocabulary. Judge each translation for a picture-word card for ages 3-7: "
              "correct meaning, standard spelling and accents, natural everyday word, no article needed (German nouns capitalised). Use neutral international "
              f"{LANGS[lang]} (Latin American Spanish, France French, standard German). Be strict but do not invent problems: ok=true when a word is acceptable.")
    prompt = f"Language: {LANGS[lang]}\nWords (English -> given):\n{json.dumps(pairs, ensure_ascii=False)}\nReturn one verdict per word, in the same order."
    out = router.complete_json("research", system, prompt, LangVerdicts, providers=providers, max_tokens=12000)
    if out is None:
        return {"checked": False, "issues": [], "source": "", "reason": "no AI helper is available (log in to the claude CLI or add a key in Settings)"}
    issues = [v.model_dump() for v in out.verdicts if not v.ok]
    return {"checked": True, "issues": issues, "source": router.last_used or "ai", "words": len(out.verdicts)}


def record_ai(lang: str, result: dict) -> None:
    if not result.get("checked"):
        return
    data = load_reviews()
    data[lang] = {"fingerprint": fingerprint(lang), "by": f"AI helper ({result.get('source')})", "kind": "ai", "date": time.strftime("%Y-%m-%d"),
                  "words": result.get("words", 0), "issues": result.get("issues", [])}
    _save(data)


def approve(lang: str, by: str) -> None:
    """Record that a person reviewed this exact word list."""
    check_lang(lang)
    if not by.strip():
        raise ValueError("say who reviewed it (--by 'Name')")
    data = load_reviews()
    data[lang] = {"fingerprint": fingerprint(lang), "by": by.strip(), "kind": "human", "date": time.strftime("%Y-%m-%d"), "words": len(TR[lang]), "issues": []}
    _save(data)


def review_status(lang: str) -> tuple[str, str]:
    """(status, message): status is 'pass' (a person signed off the current list), 'warn' (AI-checked with no issues) or 'fail' (not checked, changed since, or issues found)."""
    if lang == "en":
        return "pass", "English: no translation to check"
    r = load_reviews().get(lang)
    if not r:
        return "fail", f"{LANGS[lang]} word list has not been checked. Run: moneyhub translations check --lang {lang}, then have a native speaker approve it"
    if r.get("fingerprint") != fingerprint(lang):
        return "fail", f"{LANGS[lang]} word list changed since it was reviewed ({r.get('by')}, {r.get('date')}). Check it again"
    if r.get("kind") == "human":
        return "pass", f"{LANGS[lang]} words signed off by {r.get('by')} on {r.get('date')}"
    if r.get("issues"):
        sample = "; ".join(f"{i['english']}: '{i['given']}' -> '{i.get('suggestion') or '?'}'" for i in r["issues"][:4])
        return "fail", f"AI proofreading flagged {len(r['issues'])} {LANGS[lang]} words ({sample}). Fix them in translations.py, or approve after a native speaker agrees"
    return "warn", f"{LANGS[lang]} words were AI-checked ({r.get('date')}), not by a native speaker. Ask one to approve: moneyhub translations approve --lang {lang} --by 'Name'"
