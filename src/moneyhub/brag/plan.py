"""Story plan: angle, hook, scenes, share copy. Written by an LLM when available, otherwise by a rule-based planner."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from ..llm import LLMRouter
from .tones import Tone

Visual = Literal["text", "page", "pages", "mockup", "stat", "checklist", "typing"]
Transition = Literal["cut", "fade", "dip", "slide", "zoom", "wipe", "flash"]
SceneKind = Literal["hook", "reveal", "feature", "show", "stat", "punchline", "outro"]

BANNED = ("excited to share", "streamline your workflow", "game-changer", "game changer", "revolutionize", "supercharge", "unlock your",
          "take it to the next level", "seamless", "cutting-edge", "in today's fast-paced")


class Scene(BaseModel):
    kind: SceneKind
    headline: str = Field(description="Main on-screen line, <= 9 words, specific to this product")
    subline: str = Field(default="", description="Optional smaller line, <= 14 words")
    bullets: list[str] = Field(default_factory=list, description="For checklist scenes: 3-4 items, <= 6 words each")
    visual: Visual = "text"
    page_index: int = Field(default=0, description="Which product page image to show (0 = first)")
    stat_value: int = Field(default=0, description="For stat scenes: the number to count up to (must come from the features)")
    stat_label: str = ""
    seconds: float = Field(default=3.0, ge=1.0, le=8.0)
    transition: Transition = "fade"
    vo: str = Field(default="", description="Optional voice-over line for this scene (spoken only with --voice)")


class ShareCopy(BaseModel):
    primary: str = Field(description="1-3 sentences, postable as-is, specific, in the tone; no 'excited to share'")
    pinterest_title: str = Field(description="<= 100 characters, keywords first")
    pinterest_description: str = Field(description="<= 500 characters, natural keywords, ends with a call to action")
    instagram: str = Field(description="Caption with keywords and at most 5 hashtags")
    tiktok: str = Field(description="Short caption, 3-5 niche hashtags, no #fyp")
    x: str = Field(description="<= 270 characters")
    reddit: str = Field(description="Value-first post body that discloses you made it; no hard sell; check each subreddit's rules")
    email_subject: str = Field(description="<= 60 characters")
    email_preview: str = Field(description="<= 110 characters")


class BragPlan(BaseModel):
    angle: str = Field(description="One sentence: the creative angle")
    hook: str = Field(description="What the first 2 seconds show or say")
    punchline: str = Field(description="The closing line")
    scenes: list[Scene] = Field(min_length=3, max_length=8)
    share: ShareCopy


def clean_share(sc: ShareCopy, url: str = "") -> ShareCopy:
    def tags(text: str, n: int) -> str:
        found = re.findall(r"#\w+", text)
        if len(found) <= n:
            return text
        keep = set(found[:n])
        return re.sub(r"#\w+", lambda m: m.group(0) if m.group(0) in keep else "", text).replace("  ", " ").strip()

    def clip(t: str, n: int) -> str:
        t = re.sub(r"\s+", " ", t).strip()
        return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0].rstrip(",;:- ") + "…"

    return sc.model_copy(update={
        "pinterest_title": clip(sc.pinterest_title, 100), "pinterest_description": clip(sc.pinterest_description, 500),
        "instagram": tags(sc.instagram, 5), "tiktok": tags(sc.tiktok.replace("#fyp", "").replace("#foryou", ""), 5),
        "x": clip(sc.x, 270), "email_subject": clip(sc.email_subject, 60), "email_preview": clip(sc.email_preview, 110),
    })


def has_banned(plan: BragPlan) -> list[str]:
    blob = " ".join([plan.angle, plan.hook, plan.punchline, plan.share.primary]
                    + [f"{s.headline} {s.subline} {' '.join(s.bullets)} {s.vo}" for s in plan.scenes]).lower()
    return [b for b in BANNED if b in blob]


def violations(plan: BragPlan) -> list[str]:
    """Hard limits that keep every line readable on screen and the video near its target length."""
    out: list[str] = []
    for i, sc in enumerate(plan.scenes, 1):
        if len(sc.headline.split()) > 9:
            out.append(f"scene {i} headline has {len(sc.headline.split())} words (max 9)")
        if len(sc.subline.split()) > 14:
            out.append(f"scene {i} subline has {len(sc.subline.split())} words (max 14)")
        for b in sc.bullets:
            if len(b.split()) > 6:
                out.append(f"scene {i} bullet '{b}' has more than 6 words")
        if len(sc.vo.split()) > 11:
            out.append(f"scene {i} voice-over has {len(sc.vo.split())} words (max 11)")
    total = sum(sc.seconds for sc in plan.scenes)
    if not 12 <= total <= 32:
        out.append(f"scene seconds add up to {total:.0f}; they must add up to about the target length")
    return out


# ----------------------------------------------------------------------------- source facts
class Facts(BaseModel):
    """What the planner may claim: everything on screen must come from here."""
    name: str
    kind: str                 # product | shop | website
    one_liner: str
    audience: str = ""
    features: list[str] = Field(default_factory=list)
    pains: list[str] = Field(default_factory=list)
    price: str = ""
    cta: str = "Instant download"
    shop: str = ""
    url: str = ""
    n_pages: int = 3          # how many page images are available for visuals


LAWS = """Creative laws (follow all):
- SHORT: 15-25 seconds total; 18-22 is the sweet spot.
- Clear to a stranger: after one viewing someone who never heard of it knows what it is, who it is for and how to get it.
- The hook is everything: the first 2 seconds decide whether anyone keeps watching. Plan it first.
- Show the thing: use the real product pages (visual page/pages/mockup) rather than abstract filler.
- Specific: it must feel made for exactly this product. Banned phrases: streamline your workflow, game-changer, revolutionize, supercharge, unlock your, seamless, cutting-edge, excited to share.
- Readable: every line the viewer must read stays settled long enough (about 0.3 s per word).
- Make it alive: things appear one by one; checklists tick; numbers count up.
- Never invent claims, numbers, prices or testimonials: use only the facts provided.
- Every frame postable. Funny only when it comes from the product's own absurdity."""


def llm_plan(router: LLMRouter, facts: Facts, tone: Tone, direction: str, duration: float, providers=None) -> BragPlan | None:
    prompt = (
        f"Plan a launch video ('/brag') for this {facts.kind}.\n\nFACTS (the only things you may claim):\n{facts.model_dump_json(indent=1)}\n\n"
        f"Tone preset: {tone.key} - {tone.brief}\n" + (f"Extra direction from the creator: {direction}\n" if direction else "")
        + f"Target length: about {duration:.0f} seconds across {tone.scenes[0]}-{tone.scenes[1]} scenes. "
        f"Scene visuals available: text, page, pages (several product pages), mockup (framed print on a wall; wall art only), "
        f"stat (a counting number taken from the features), checklist (3-4 bullets tick on), typing (typed line). "
        f"Transitions allowed for this tone: {', '.join(tone.transitions)}. page_index must be below {facts.n_pages}.\n"
        "Shape: Hook (2-3 s) -> Reveal (2-4 s) -> 2-3 sharp highlights -> Punchline/outro (2-4 s). A starting shape, not a template.\n"
        "Also write share copy for Pinterest, Instagram, TikTok, X, Reddit (value-first, disclose that you made it) and an email subject/preview. "
        "Add a short voice-over line (vo) per scene (<= 12 words) in case voice is enabled.\n\n" + LAWS
    )
    system = "You are a sharp launch-video director and copywriter. You write specific, truthful, tasteful scripts and never use marketing cliches."
    for _ in range(3):
        plan = router.complete_json("motion", system, prompt, BragPlan, providers=providers, max_tokens=6000)
        if plan is None:
            return None
        bad = has_banned(plan)
        long = violations(plan)
        if not bad and not long:
            return plan
        prompt += ("\n\nFix these problems and answer again: " + "; ".join(([f"banned phrases used: {', '.join(bad)}"] if bad else []) + long))
    return plan


# ----------------------------------------------------------------------------- rule-based planner
def _num(feature: str) -> tuple[int, str] | None:
    m = re.match(r"\s*(\d{1,3})\s+(.*)", feature)
    return (int(m.group(1)), m.group(2).strip()) if m else None


def _title(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _short(f: str, max_words: int = 6) -> str | None:
    f = re.sub(r"\(.*?\)", "", f)
    f = re.split(r"\s+-\s+|:", f)[0].strip(" ,.")
    return f if 1 <= len(f.split()) <= max_words and not f.lower().startswith(("sizes", "made for", "designed for")) else None


def builtin_plan(facts: Facts, tone: Tone, duration: float) -> BragPlan:
    pain = (facts.pains[0] if facts.pains else "").rstrip(".")
    feats = [x for x in (_short(f) for f in facts.features) if x]
    stat = next((_num(f) for f in feats if _num(f)), None)
    hook = {
        "yc-parody": f"We are disrupting {facts.audience.split(' who ')[0] or 'planning'}.",
        "chaotic": f"{pain or facts.name}?? NOT ANYMORE.",
        "deadpan": f"{pain or 'A planner'}. Here is one more option.",
        "cinematic": f"In a world of {pain.lower() or 'clutter'}...",
    }.get(tone.key, f"{pain}?" if pain else f"Meet {facts.name}")
    if tone.key in ("default", "app-store", "polished") and pain:
        hook = f"{pain}."
    scenes: list[Scene] = [Scene(kind="hook", headline=hook[:80], visual="typing" if tone.anim == "type" else "text", seconds=2.6,
                                 transition="cut", vo=hook)]
    scenes.append(Scene(kind="reveal", headline=facts.name, subline=facts.one_liner[:100], visual="page", page_index=0, seconds=3.4,
                        transition=tone.transitions[0], vo=f"Meet {facts.name}."))
    if stat and tone.scenes[1] > 5:
        scenes.append(Scene(kind="stat", headline=_title(stat[1])[:50], visual="stat", stat_value=stat[0], stat_label=_title(stat[1])[:40],
                            seconds=3.0, transition=tone.transitions[-1], vo=f"{stat[0]} {stat[1]}."))
    if tone.key == "chaotic":   # one fast scene per benefit
        for i, f in enumerate(feats[:3]):
            scenes.append(Scene(kind="feature", headline=_title(f)[:48], visual="text", seconds=1.7, transition=tone.transitions[i % len(tone.transitions)], vo=f))
    else:
        scenes.append(Scene(kind="feature", headline="What you get", bullets=[_title(f)[:48] for f in feats[:4]], visual="checklist", seconds=4.2,
                            transition=tone.transitions[-1], vo="; ".join(feats[:3])))
    if facts.n_pages > 1:
        scenes.append(Scene(kind="show", headline="Made to be used", subline="Print it or use it on your device", visual="pages",
                            page_index=1, seconds=3.2, transition=tone.transitions[0], vo="Print it or use it on your device."))
    scenes.append(Scene(kind="outro", headline=facts.cta, subline=(facts.shop or facts.url or facts.name)[:60], visual="text", seconds=3.0,
                        transition=tone.transitions[0], vo=f"{facts.cta}."))
    scenes = scenes[: tone.scenes[1] + 1]
    total = sum(s.seconds for s in scenes)
    k = duration / total
    for s in scenes:
        s.seconds = round(max(1.4, s.seconds * k), 2)
    tag = "#" + re.sub(r"[^a-z0-9]", "", facts.name.lower())[:24]
    desc = f"{facts.name}: {facts.one_liner}"
    share = ShareCopy(
        primary=f"{facts.name} is here. {facts.one_liner} {facts.cta}.",
        pinterest_title=f"{facts.name} - {facts.cta.lower()}", pinterest_description=f"{desc} {facts.cta}. Save this pin for later.",
        instagram=f"{desc}\n\n{tag} #printable #digitaldownload", tiktok=f"{facts.name} {tag} #printable #digitalproduct",
        x=f"{facts.name}: {facts.one_liner} {facts.url}".strip(),
        reddit=f"I made {facts.name}. {facts.one_liner} Happy to answer questions or share how I built it (check the sub's self-promo rules first).",
        email_subject=f"New: {facts.name}", email_preview=facts.one_liner[:110])
    return BragPlan(angle=f"{tone.feel}: show {facts.name} doing its job", hook=hook, punchline=facts.cta, scenes=scenes, share=clean_share(share))


def make_plan(router: LLMRouter | None, facts: Facts, tone: Tone, direction: str, duration: float, providers=None) -> tuple[BragPlan, str]:
    plan = llm_plan(router, facts, tone, direction, duration, providers) if router is not None else None
    source = (router.last_used if router is not None and plan is not None else None) or "builtin"
    if plan is None:
        plan, source = builtin_plan(facts, tone, duration), "builtin"
    plan = plan.model_copy(update={"share": clean_share(plan.share, facts.url)})
    # keep scene count and total length sane
    scenes = [s.model_copy(update={"page_index": min(s.page_index, max(0, facts.n_pages - 1)),
                                   "transition": s.transition if s.transition in tone.transitions or s.transition == "cut" else tone.transitions[0]})
              for s in plan.scenes]
    total = sum(s.seconds for s in scenes)
    if abs(total - duration) > 2.5:
        k = duration / total
        scenes = [s.model_copy(update={"seconds": round(min(8.0, max(1.2, s.seconds * k)), 2)}) for s in scenes]
    return plan.model_copy(update={"scenes": scenes}), source
