"""Deterministic local Contract Agent.

The production version can swap this module for an LLM call. For the course
artifact we keep a no-key deterministic parser so the whole project is
reproducible on any machine.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from scenetest.core.contract_schema import CameraSpec, ContractObject, Relation, SceneContract


@dataclass(frozen=True)
class ObjectLexeme:
    object_id: str
    object_type: str
    phrases: Tuple[str, ...]


OBJECT_LEXICON: Tuple[ObjectLexeme, ...] = (
    ObjectLexeme("low_table", "low_table", ("low table", "coffee table")),
    ObjectLexeme("desk", "desk", ("wooden desk", "desk")),
    ObjectLexeme("table", "table", ("side table", "small table", "table")),
    ObjectLexeme("bookshelf", "shelf", ("bookshelf", "book shelf", "shelf")),
    ObjectLexeme("laptop", "laptop", ("laptop", "computer")),
    ObjectLexeme("floor_lamp", "lamp", ("floor lamp",)),
    ObjectLexeme("lamp", "lamp", ("lamp",)),
    ObjectLexeme("coffee_cup", "cup", ("coffee cup",)),
    ObjectLexeme("cup", "cup", ("toothbrush cup", "ceramic cup", "cup", "mug")),
    ObjectLexeme("book", "book", ("book", "notebook")),
    ObjectLexeme("plant", "plant", ("small plant", "potted plant", "plant")),
    ObjectLexeme("chair", "chair", ("chair",)),
    ObjectLexeme("bench", "bench", ("bench",)),
    ObjectLexeme("sofa", "sofa", ("sofa", "couch")),
    ObjectLexeme("bed", "bed", ("bed",)),
    ObjectLexeme("cube", "cube", ("cube",)),
    ObjectLexeme("sphere", "sphere", ("sphere", "ball")),
    ObjectLexeme("cylinder", "cylinder", ("cylinder",)),
    ObjectLexeme("cone", "cone", ("cone",)),
    ObjectLexeme("monitor", "monitor", ("monitor", "screen")),
    ObjectLexeme("keyboard", "keyboard", ("keyboard",)),
    ObjectLexeme("mouse", "mouse", ("mouse",)),
    ObjectLexeme("phone", "phone", ("phone", "smartphone")),
    ObjectLexeme("vase", "vase", ("vase",)),
    ObjectLexeme("bottle", "bottle", ("bottle",)),
    ObjectLexeme("bowl", "bowl", ("bowl",)),
    ObjectLexeme("plate", "plate", ("plate",)),
    ObjectLexeme("clock", "clock", ("clock",)),
    ObjectLexeme("speaker", "speaker", ("speaker",)),
    ObjectLexeme("camera", "camera", ("camera",)),
    ObjectLexeme("microphone", "microphone", ("microphone",)),
    ObjectLexeme("telescope", "telescope", ("telescope",)),
    ObjectLexeme("robot_arm", "robot_arm", ("robot arm",)),
    ObjectLexeme("printer", "printer", ("printer",)),
    ObjectLexeme("toolbox", "toolbox", ("toolbox", "tool box")),
    ObjectLexeme("easel", "easel", ("easel",)),
    ObjectLexeme("canvas", "canvas", ("canvas", "painting")),
    ObjectLexeme("mirror", "mirror", ("mirror",)),
    ObjectLexeme("piano", "piano", ("piano",)),
    ObjectLexeme("rug", "rug", ("rug", "carpet")),
)

COLORS = ("red", "blue", "green", "yellow", "white", "black", "purple", "orange", "pink", "gray", "silver", "gold")
MATERIALS = (
    "wooden",
    "wood",
    "metal",
    "ceramic",
    "glass",
    "fabric",
    "plastic",
    "paper",
    "stone",
    "marble",
    "leather",
    "bronze",
    "clay",
)
STYLE_KEYWORDS = {
    "warm": ("warm", "cozy", "yellow lighting"),
    "cyberpunk": ("cyberpunk", "neon"),
    "minimal": ("minimal", "neutral", "soft neutral"),
    "medieval": ("medieval", "candle"),
    "futuristic": ("futuristic", "sci-fi", "science fiction"),
}

OPEN_TYPE_MAP = {
    "star_map": "map",
    "map": "map",
    "compass": "compass",
    "magnifying_glass": "magnifying_glass",
    "glass": "magnifying_glass",
    "globe": "globe",
    "passport": "passport",
    "ticket": "ticket",
    "clipboard": "clipboard",
    "plaque": "plaque",
    "menu_card": "menu_card",
    "card": "menu_card",
    "tablet": "clay_tablet",
    "clay_tablet": "clay_tablet",
    "board": "chess_board",
    "chess_board": "chess_board",
    "cutting_board": "cutting_board",
    "sensor_module": "sensor_module",
    "module": "sensor_module",
    "battery_pack": "battery_pack",
    "pack": "battery_pack",
    "monitor": "monitor",
    "screen": "monitor",
    "keyboard": "keyboard",
    "mouse": "mouse",
    "phone": "phone",
    "smartphone": "phone",
    "vase": "vase",
    "bottle": "bottle",
    "bowl": "bowl",
    "plate": "plate",
    "clock": "clock",
    "speaker": "speaker",
    "camera": "camera",
    "microphone": "microphone",
    "telescope": "telescope",
    "violin": "violin",
    "palette": "paint_palette",
    "paint_palette": "paint_palette",
    "sculpture": "clay_sculpture",
    "statue": "statue",
    "tripod": "tripod",
    "light_stand": "light_stand",
    "stand": "light_stand",
    "reflector": "reflector",
    "microscope": "microscope",
    "beaker": "beaker",
    "rack": "test_tube_rack",
    "test_tube_rack": "test_tube_rack",
    "wrench": "wrench",
    "drill": "drill",
    "helmet": "helmet",
    "spray_bottle": "spray_bottle",
    "seed_tray": "seed_tray",
    "watering_can": "watering_can",
    "roll": "fabric_roll",
    "fabric_roll": "fabric_roll",
    "needle_box": "needle_box",
    "scissors": "scissors",
    "scissor": "scissors",
    "sandwich": "sandwich",
    "basket": "basket",
    "king": "king",
    "queen": "queen",
    "cardboard_box": "cardboard_box",
    "box": "cardboard_box",
    "barcode_scanner": "barcode_scanner",
    "scanner": "barcode_scanner",
    "tape_roll": "tape_roll",
    "label_printer": "label_printer",
    "toy_car": "toy_car",
    "car": "toy_car",
    "robot_toy": "robot_toy",
    "block_tower": "block_tower",
    "teapot": "teapot",
    "tray": "bamboo_tray",
    "bamboo_tray": "bamboo_tray",
    "suitcase": "suitcase",
    "drone": "drone",
    "screwdriver": "screwdriver",
    "fish_statue": "fish_statue",
    "coral_model": "coral_model",
    "cake": "cake",
    "rolling_pin": "rolling_pin",
    "artifact": "stone_artifact",
    "stone_artifact": "stone_artifact",
    "radio": "radio",
    "soap_dispenser": "soap_dispenser",
    "dispenser": "soap_dispenser",
    "brush": "brush",
    "jewelry_box": "jewelry_box",
    "shoe_rack": "shoe_rack",
    "umbrella_stand": "umbrella_stand",
    "backpack": "backpack",
    "key_bowl": "key_bowl",
    "stethoscope": "stethoscope",
    "pill_bottle": "pill_bottle",
    "water_bottle": "bottle",
    "towel": "towel",
    "printer": "printer",
    "toolbox": "toolbox",
    "easel": "easel",
    "canvas": "canvas",
    "painting": "canvas",
    "mirror": "mirror",
    "piano": "piano",
    "rug": "rug",
    "carpet": "rug",
    "arm": "robot_arm",
}

OBJECT_STOPWORDS = {
    "scene",
    "setup",
    "display",
    "arrangement",
    "area",
    "corner",
    "lighting",
    "light",
    "side",
    "front",
    "back",
    "top",
    "center",
    "centre",
    "room",
    "gallery",
    "office",
    "workstation",
    "kitchen",
    "studio",
    "workshop",
    "lab",
    "laboratory",
    "classroom",
    "wall",
    "floor",
    "right",
    "left",
    "of",
    "with",
    "and",
    "a",
    "an",
    "the",
    "to",
    "from",
    "on",
    "in",
    "behind",
    "near",
    "next",
}

DESCRIPTOR_WORDS = {
    "small",
    "large",
    "tall",
    "short",
    "thin",
    "wide",
    "round",
    "square",
    "cozy",
    "minimal",
    "warm",
    "neutral",
    "futuristic",
    "cyberpunk",
    "medieval",
    "modern",
    "vintage",
    "bright",
    "dark",
    "soft",
    "wooden",
    *COLORS,
    *MATERIALS,
}

GENERIC_PHRASE_RE = re.compile(
    r"\b(?:a|an|the|one|small|large|tall|short|red|blue|green|yellow|white|black|purple|orange|pink|gray|silver|gold|wooden|metal|ceramic|glass|fabric|plastic|paper|stone|marble|leather|bronze|clay)\s+"
    r"([a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,2})"
)

RELATION_PATTERNS = (
    ("right_of", re.compile(r"\bto the right of\b|\bon the right side of\b|\bright of\b")),
    ("left_of", re.compile(r"\bto the left of\b|\bon the left side of\b|\bleft of\b")),
    ("in_front_of", re.compile(r"\bin front of\b")),
    ("behind", re.compile(r"\bbehind\b")),
    ("on", re.compile(r"\bon top of\b|\bon\b")),
    ("near", re.compile(r"\bnear\b|\bnext to\b")),
)


class ContractAgent:
    def parse(self, prompt: str, scene_id: str | None = None) -> SceneContract:
        text = prompt.lower()
        mentions = _find_mentions(text)
        objects = _extract_objects(text, mentions)
        relations = _extract_relations(text, mentions)
        objects = _filter_unreferenced_generic_objects(objects, relations)
        style = _extract_style(text)
        visible = [obj.id for obj in objects]
        contract_id = scene_id or "scene_" + hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:8]
        return SceneContract(
            id=contract_id,
            prompt=prompt,
            objects=objects,
            relations=relations,
            style=style,
            camera=CameraSpec(view="front_perspective", visible_objects=visible),
        )


def _find_mentions(text: str) -> List[Tuple[int, int, ObjectLexeme, str]]:
    mentions: List[Tuple[int, int, ObjectLexeme, str]] = []
    for lexeme in OBJECT_LEXICON:
        for phrase in sorted(lexeme.phrases, key=len, reverse=True):
            for match in re.finditer(rf"\b{re.escape(phrase)}\b", text):
                mentions.append((match.start(), match.end(), lexeme, phrase))
    mentions.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    filtered: List[Tuple[int, int, ObjectLexeme, str]] = []
    occupied: List[Tuple[int, int]] = []
    for start, end, lexeme, phrase in mentions:
        if any(start >= a and end <= b for a, b in occupied):
            continue
        filtered.append((start, end, lexeme, phrase))
        occupied.append((start, end))
    filtered.extend(_fallback_mentions(text, occupied, filtered))
    filtered.extend(_repeat_mentions(text, filtered, occupied))
    filtered.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    return filtered


def _fallback_mentions(
    text: str,
    occupied: List[Tuple[int, int]],
    known_mentions: List[Tuple[int, int, ObjectLexeme, str]],
) -> List[Tuple[int, int, ObjectLexeme, str]]:
    mentions: List[Tuple[int, int, ObjectLexeme, str]] = []
    for match in GENERIC_PHRASE_RE.finditer(text):
        raw_phrase = match.group(1)
        start, end = match.start(1), match.end(1)
        if _overlaps(start, end, occupied):
            continue
        phrase = _clean_object_phrase(raw_phrase)
        if not phrase:
            continue
        phrase_offset = raw_phrase.find(phrase)
        if phrase_offset >= 0:
            start = match.start(1) + phrase_offset
            end = start + len(phrase)
        object_id = _object_id_from_phrase(phrase)
        lexeme = _alias_lexeme(object_id, start, known_mentions + mentions) or ObjectLexeme(
            object_id,
            _type_from_phrase(phrase),
            (phrase,),
        )
        mentions.append((start, end, lexeme, phrase))
        occupied.append((start, end))
    return mentions


def _alias_lexeme(
    object_id: str,
    start: int,
    mentions: List[Tuple[int, int, ObjectLexeme, str]],
) -> ObjectLexeme | None:
    if "_" in object_id:
        return None
    prior = [
        item
        for item in mentions
        if item[1] <= start
        and item[2].object_id != object_id
        and item[2].object_id.split("_")[-1] == object_id
    ]
    if not prior:
        return None
    return prior[-1][2]


def _repeat_mentions(
    text: str,
    mentions: List[Tuple[int, int, ObjectLexeme, str]],
    occupied: List[Tuple[int, int]],
) -> List[Tuple[int, int, ObjectLexeme, str]]:
    repeats: List[Tuple[int, int, ObjectLexeme, str]] = []
    for _start, _end, lexeme, phrase in list(mentions):
        if not phrase or len(phrase) < 3:
            continue
        for match in re.finditer(rf"\b{re.escape(phrase)}\b", text):
            start, end = match.start(), match.end()
            if _overlaps(start, end, occupied):
                continue
            repeats.append((start, end, lexeme, phrase))
            occupied.append((start, end))
    return repeats


def _overlaps(start: int, end: int, spans: Iterable[Tuple[int, int]]) -> bool:
    return any(start < span_end and end > span_start for span_start, span_end in spans)


def _clean_object_phrase(phrase: str) -> str:
    tokens = re.findall(r"[a-z][a-z-]*", phrase.lower())
    while tokens and tokens[0] in DESCRIPTOR_WORDS:
        tokens.pop(0)
    clipped = []
    for token in tokens:
        if token in OBJECT_STOPWORDS:
            break
        clipped.append(token)
    tokens = clipped
    while tokens and tokens[-1] in OBJECT_STOPWORDS:
        tokens.pop()
    if not tokens or tokens[-1] in OBJECT_STOPWORDS:
        return ""
    if len(tokens) > 2:
        tokens = tokens[-2:]
    return " ".join(tokens)


def _object_id_from_phrase(phrase: str) -> str:
    object_id = re.sub(r"[^a-z0-9]+", "_", phrase.strip().lower()).strip("_")
    if object_id.endswith("ies") and len(object_id) > 4:
        object_id = object_id[:-3] + "y"
    elif object_id.endswith("es") and len(object_id) > 3:
        object_id = object_id[:-2]
    elif object_id.endswith("s") and not object_id.endswith("ss") and len(object_id) > 3:
        object_id = object_id[:-1]
    return object_id or "generic_object"


def _type_from_phrase(phrase: str) -> str:
    object_id = _object_id_from_phrase(phrase)
    if object_id in OPEN_TYPE_MAP:
        return OPEN_TYPE_MAP[object_id]
    final = object_id.split("_")[-1]
    return OPEN_TYPE_MAP.get(final, "generic")


def _extract_objects(text: str, mentions: Iterable[Tuple[int, int, ObjectLexeme, str]]) -> List[ContractObject]:
    seen: Dict[str, ContractObject] = {}
    for start, end, lexeme, _phrase in mentions:
        prefix = text[max(0, start - 32) : start]
        phrase = text[start:end]
        material = _material_from_context(prefix, phrase)
        color = _color_from_context(prefix, phrase)
        if lexeme.object_id in seen:
            existing = seen[lexeme.object_id]
            existing.material = existing.material or material
            existing.color = existing.color or color
            continue
        seen[lexeme.object_id] = ContractObject(
            id=lexeme.object_id,
            type=lexeme.object_type,
            required=True,
            material=material,
            color=color,
        )
    return list(seen.values())


def _filter_unreferenced_generic_objects(objects: List[ContractObject], relations: List[Relation]) -> List[ContractObject]:
    referenced = {rel.subject for rel in relations} | {rel.object for rel in relations}
    return [obj for obj in objects if obj.type != "generic" or obj.id in referenced]


def _extract_relations(text: str, mentions: List[Tuple[int, int, ObjectLexeme, str]]) -> List[Relation]:
    relations: List[Relation] = []
    relation_keys = set()
    for relation, pattern in RELATION_PATTERNS:
        for match in pattern.finditer(text):
            if relation == "on" and text[match.start() : match.end() + 18].startswith("on the right"):
                continue
            if relation == "on" and text[match.start() : match.end() + 17].startswith("on the left"):
                continue
            subject = _previous_object(mentions, match.start())
            target = _next_object(text, mentions, match.end())
            if not subject or not target or subject == target:
                continue
            key = (subject, relation, target)
            if key in relation_keys:
                continue
            relation_keys.add(key)
            margin = 0.25 if relation == "on" else 0.2
            relations.append(Relation(subject=subject, relation=relation, object=target, margin=margin))
    return relations


def _previous_object(mentions: List[Tuple[int, int, ObjectLexeme, str]], index: int) -> str | None:
    prev = [item for item in mentions if item[1] <= index]
    if not prev:
        return None
    return prev[-1][2].object_id


def _next_object(text: str, mentions: List[Tuple[int, int, ObjectLexeme, str]], index: int) -> str | None:
    alias = _definite_alias_after(text, mentions, index)
    if alias:
        return alias
    for start, _end, lexeme, _phrase in mentions:
        if start >= index:
            return lexeme.object_id
    return None


def _definite_alias_after(text: str, mentions: List[Tuple[int, int, ObjectLexeme, str]], index: int) -> str | None:
    match = re.match(r"\s+(?:the|a|an)\s+([a-z][a-z-]*)\b", text[index : index + 48])
    if not match:
        return None
    object_id = _object_id_from_phrase(match.group(1))
    alias = _alias_lexeme(object_id, index, [item for item in mentions if item[1] <= index])
    return alias.object_id if alias else None


def _extract_style(text: str) -> Dict[str, object]:
    if "neutral lighting" in text and "minimal" not in text:
        return {"lighting": "neutral", "palette": ["gray", "white"], "mood": "neutral"}
    for style, keywords in STYLE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            palette = {
                "warm": ["brown", "yellow", "amber"],
                "cyberpunk": ["magenta", "cyan", "black"],
                "minimal": ["white", "gray", "wood"],
                "medieval": ["brown", "gold", "candle"],
                "futuristic": ["white", "blue", "silver"],
            }[style]
            return {"lighting": style, "palette": palette, "mood": style}
    return {"lighting": "neutral", "palette": ["gray", "white"], "mood": "neutral"}


def _context_tokens(prefix: str, phrase: str) -> List[str]:
    tokens = re.findall(r"[a-z-]+", prefix)
    phrase_tokens = re.findall(r"[a-z-]+", phrase)
    immediate = list(tokens)
    while immediate and immediate[-1] in {"a", "an", "the", "and", "with"}:
        immediate.pop()
    prefix_token = immediate[-1:] if immediate else []
    return phrase_tokens[:2] + prefix_token


def _material_from_context(prefix: str, phrase: str) -> str | None:
    tokens = _context_tokens(prefix, phrase)
    if "wooden" in tokens or "wood" in tokens:
        return "wood"
    for material in MATERIALS:
        if material in tokens:
            return material
    return None


def _color_from_context(prefix: str, phrase: str) -> str | None:
    tokens = _context_tokens(prefix, phrase)
    for color in COLORS:
        if color in tokens:
            return color
    return None
