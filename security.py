import re
import unicodedata

BLOCK_PATTERNS = [
    # 1. Override / ignore instructions
    r"ignore (all |any |the |your )?(previous|prior|above|earlier|system)",
    r"disregard (all |any |the |your )?(previous|prior|above|instructions|rules)",
    r"forget (all |any |the |your )?(previous|prior|above|instructions|rules)",
    r"override (the |your )?(instructions|rules|system|settings)",
    r"bypass (the |your )?(rules|filters?|restrictions?|safety)",
    r"(new|updated|real) (instructions|rules|system prompt)",
    r"from now on",
    r"do not follow (the |your )?(rules|instructions)",
    r"stop being (a |an )?(dental|clinic)",

    # 2. Prompt extraction / leaking
    r"(system|initial|hidden|original|developer) (prompt|message|instructions?)",
    r"(reveal|show|print|repeat|display|output|tell me|give me|leak|translate|summari[sz]e|rewrite) (me )?(your|the|these|all)? ?(instructions|rules|prompt|configuration|guidelines|context)",
    r"what (are|were) your (instructions|rules|guidelines)",
    r"(repeat|print) (everything|all|the text) (above|before)",
    r"(first|last) (message|line|words) (of|in) (the |your )?(prompt|conversation)",
    r"verbatim",

    # 3. Role / persona change
    r"you are now",
    r"act as",
    r"pretend (to be|you)",
    r"role ?play",
    r"imagine you (are|were)",
    r"simulate (a |an )?",
    r"behave (like|as)",
    r"switch (to|into) .* mode",

    # 4. Known jailbreak names / modes
    r"\bdan\b",
    r"do anything now",
    r"jailbreak",
    r"developer mode",
    r"god mode",
    r"admin mode",
    r"sudo",
    r"unrestricted",
    r"no (restrictions|filters|limits|rules|censorship)",
    r"without (any )?(restrictions|filters|limits|rules)",
    r"evil (mode|assistant)",
    r"opposite mode",

    # 5. Fake system / delimiter injection
    r"<\s*/?\s*(system|instructions?|assistant|user|prompt|im_start|im_end)\s*>",
    r"\[\s*/?\s*(system|inst|instructions?)\s*\]",
    r"###\s*(system|instruction)",
    r"^\s*(system|assistant)\s*:",
    r"begin (system|new) (prompt|instructions)",
    r"end of (instructions|prompt|context)",

    # 6. Encoding / obfuscation tricks
    r"base ?64",
    r"\brot ?13\b",
    r"hex(adecimal)? (encoded|decode)",
    r"decode (this|the following)",
    r"in (morse|binary|leetspeak|pig latin)",
    r"spell it backwards",
    r"(write|say) it in (code|cipher)",

    # 7. Authority / social engineering
    r"i am (the |your )?(developer|admin|owner|creator|programmer|engineer|dentist|doctor)",
    r"(developer|admin|owner) (here|speaking)",
    r"this is (a |an )?(test|debug|emergency|authorized)",
    r"authorized (by|to)",
    r"(openai|anthropic|google|meta) (told|said|says|authorized)",

    # 8. Forbidden-topic bait (matches your medical rules)
    r"(how (much|many)|what) (dose|dosage|mg)",
    r"(dose|dosage) (for|of)",
    r"(can|should) i (take|give) .* (ibuprofen|paracetamol|aspirin|antibiotic|painkiller|amoxicillin)",
    r"(my|the) child.*(medicine|medication|dose)",
    r"(diagnose|diagnosis)",
    r"what (disease|condition) (do i|is this)",

    # 9. Output manipulation (Removed "table" and "markdown" so users can ask for them!)
    r"(respond|reply|answer) (only )?(in|with) (json|code|html)",
    r"ignore (the )?(bullet|format|length|word) (limit|rule)",
    r"write (a )?(long|detailed|essay|story|poem|code|script)",
]

COMPILED = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in BLOCK_PATTERNS]

LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]", "", text)
    text = text.translate(LEET)
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    text = re.sub(r"[^\w\s<>/\[\]:#]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def is_blocked(user_input: str) -> bool:
    if len(user_input) > 500:
        return True
    for candidate in (user_input, normalize(user_input)):
        if any(p.search(candidate) for p in COMPILED):
            return True
    return False

SAFE_REPLY = "I can only help with questions about this clinic."