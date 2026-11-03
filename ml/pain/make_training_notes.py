"""Write ml/pain/training-notes.jsonl: synthetic notes for TRAINING the red-flag model.

Separate from synthetic-notes.jsonl (the dev/test set). Phrases were written by Claude
(2026-11-03) after the test set, avoiding its sentences; notes are phrase x frame
combinations, so they are less varied than real text. Notes whose normalised text
appears in the test set are dropped. Synthetic, not reviewed by a physiotherapist.

  py -3.14 ml\\pain\\make_training_notes.py
"""

import json
import random
from pathlib import Path

from pain_text import normalize

HERE = Path(__file__).parent
OUT = HERE / "training-notes.jsonl"
SEED = 7

# symptom -> phrases (Egyptian, formal, typos and Franco-Arabic mixed)
FLAG_PHRASES = {
    "chest pain": [
        "وجع في القلب", "شكة في القلب", "صدري مكتوم", "ألم في نص الصدر", "صدري واجعني",
        "ألم بالصدر", "وخز في صدري", "صدري مقبوض", "وجع ف صدرى", "ضغط على الصدر",
        "sadri byewga3ni", "wag3 fe sdry", "alam fel sadr", "chest pain",
    ],
    "difficulty breathing": [
        "نفسي بيتقطع", "مش لاقي نفسي", "النفس تقيل عليا", "بتنفس بالعافية",
        "الهوا مش داخل صدري", "نهجان من أقل مجهود", "نفسي قصير", "ضيق تنفس",
        "مش قادرة أتنفس", "صعوبة في التنفس", "بنهج من غير ما أعمل حاجة",
        "mesh 3aref atnaffes", "nafasy ma2too3", "short of breath",
    ],
    "calf pain or swelling": [
        "سمانتي بتوجعني", "ورم في السمانة", "وجع في بطن الرجل", "رجلي من تحت وارمة وسخنة",
        "سمانة رجلي حمرا", "شد جامد في السمانة", "الساق وارمة", "رجلي الشمال أتخن من اليمين",
        "ألم في الساق", "تورم في الساق", "بطة الرجل وارمة", "semanet regly wag3ani",
        "regly wermet", "calf pain",
    ],
    "fever or shivering": [
        "عندي حرارة", "سخنت بالليل", "جسمي سخن نار", "بترعش من البرد", "جالي برد ورعشة",
        "درجة حرارتي ٣٨", "حرارتي ٣٩ ونص", "عندي سخونة", "حمى", "جسمي مولع",
        "sokhna", "3andy 7arara", "fever",
    ],
    "wound discharge": [
        "الجرح بيطلع مية", "في إفرازات من الجرح", "الجرح ملتهب", "الجرح لونه أحمر وسخن",
        "الغرز فاتحة", "الجرح بيرشح", "صديد في الجرح", "التهاب الجرح",
        "الجرح ريحته مش حلوة", "el gar7 bytala3 mayya", "el gar7 multaheb", "wound is leaking",
    ],
    "knee swelling or redness": [
        "ركبتي منفوخة", "ركبتي ورمت", "الركبة بتورم أكتر", "ركبتي سخنة وحمرا",
        "ورم في الركبة بيزيد", "ركبتي لونها احمر", "انتفاخ الركبة", "ركبتي وارمه",
        "rokbety manfo5a", "rokbty warma w so5na", "knee is swollen",
    ],
    "numbness": [
        "رجلي بتنمل", "إيدي بتنمل", "مش حاسس بصوابعي", "تنميل في رجلي", "خدر في رجلي",
        "رجلي مخدرة", "فقدان الإحساس في الرجل", "منملة", "دراعي منمل",
        "regly betnamel", "tanmil fe edi", "numbness",
    ],
    "dizziness or fainting": [
        "دايخة", "الدنيا بتلف", "حسيت بدوخة", "راسي بتلف", "كنت هقع", "زغللة في عيني",
        "وقعت من طولي", "دوار", "فقدت الوعي", "اغمى عليا", "دوخة جامدة",
        "dayekha", "dokha", "dizzy",
    ],
    "sharp or sudden pain": [
        "وجع حاد", "ألم شديد مفاجئ", "شكة جامدة", "وجع بيخزق", "طرقعة في الركبة ووجع جامد",
        "وجع زي السكينة", "وجع مش طبيعي", "ألم مفاجئ", "وجع نار",
        "alam shedid", "wag3 gamed fag2a", "sharp pain",
    ],
}

# idioms and resolved mentions that use red-flag words but are not red flags
IDIOMS = [
    "صدري منشرح", "صدري واسع النهارده", "قلبي مبسوط", "قلبي حاسس إني هخف", "نفسي أرجع ألعب كورة",
    "نفسي مفتوحة للأكل", "خلاص الدوخة راحت من أسبوع", "السخونية راحت خالص",
    "الدكتور سألني عن التنميل وقلتله لا", "قريت إن الدوخة ممكن تحصل بس محصلتش", "مبقاش في ورم",
    "الجرح قفل ونشف",
]

# nouns that make sense after "مفيش" (no ...), per symptom
NEGATABLE = [
    "دوخة", "تنميل", "سخونية", "حرارة", "وجع في صدري", "ضيق في النفس", "صديد",
    "ورم", "وجع حاد", "رعشة", "إفرازات من الجرح", "خدر",
]

FLAG_FRAMES = [
    "{x}", "عندي {x}", "{x} من امبارح", "بعد التمرين {x}", "{x} وأنا بتمرن",
    "النهارده {x}", "من الصبح {x}", "{x} ومش عارف أعمل ايه", "{x} جامد", "حاسس إن {x}",
    "{x} من ساعة ما صحيت", "يا دكتور {x}",
]
LATIN_FRAMES = ["{x}", "{x} ba3d el tamreen", "el naharda {x}", "{x} awy", "3andy {x}"]
NEG_FRAMES = [
    "مفيش {x}", "مفيش {x} الحمد لله", "مش حاسس ب{x}", "مكانش عندي {x} النهارده",
    "لو حصل {x} هكلم الدكتور", "{x}؟ لا خالص", "ولا {x} ولا حاجة",
]

BENIGN = [
    "شوية تعب بعد التمرين", "وجع خفيف في الفخد", "شد عضلي خفيف", "تيبس الصبح وبيروح",
    "رجلي تعبانة", "الوجع ٢ من ١٠", "الوجع ٤ من ١٠ زي كل مرة", "كملت التمرين عادي",
    "التمرين كان صعب شوية", "ركبتي كويسة", "مفيش مشاكل", "حاسس بتحسن",
    "عملت التكرارات كلها", "الوجع قل عن الأسبوع اللي فات", "عضلاتي مشدودة شوية",
    "نمت كويس", "أخدت المسكن زي ما الدكتور قال", "العضلة بتحرقني شوية وده طبيعي",
    "ضهري تعبان من الشغل", "كتفي متيبس شوية", "زهقت من التمرين بصراحة",
    "معرفتش أكمل آخر تكرار", "الحمد لله تمام", "مفيش جديد", "صدري مفتوح ومبسوط",
    "نفسي أخلص العلاج بسرعة", "نفسي في أكلة حلوة", "قلبي معاكم", "قلبي مرتاح النهارده",
    "رجلي على رجلك يا دكتور", "عرقان شوية", "الجو حر", "اتأخرت على التمرين",
    "عملت المشي نص ساعة", "الركبة بتطقطق من غير وجع", "حاسس بشد بسيط بعد السكوات",
    "tamam el hamdulellah", "kolo tamam", "ta3ban shwaya", "pain 3/10",
    "el wag3 a2al", "no pain today", "feeling better", "شوية وجع عادي في العضلة",
    "تعبت من السلم بس ارتحت", "ركبتي أحسن", "الوجع بيروح مع الحركة", "مش قادر أنزل أوي في السكوات",
    # added after the first dev run: mild, familiar pain is not a red flag
    "رقبتي واجعاني شوية من النوم", "ألم خفيف في الركبة زي العادة", "وجع بسيط في الفخد بعد التمرين",
    "ركبتي بتوجعني شوية لما بطلع السلم زي كل مرة", "الوجع نفس بتاع امبارح", "كتفي بيوجعني شوية لما أرفعه",
    "وجع ٣ من ١٠", "ألم ٢ من ١٠ بيروح بالراحة", "pain 1/10", "pain 4/10 like usual", "mild pain in my knee",
    "slight soreness", "shwayet wag3 3ady", "wag3 khafeef", "ضهري بيوجعني من الشغل",
    "الوجع مش أكتر من الأول", "إيدي واجعاني من الشيل", "ألم العضلات بعد التمرين عادي",
]
BENIGN_FRAMES = ["{x}", "النهارده {x}", "{x} الحمد لله", "{x} بس كده", "بعد التمرين {x}"]


def is_latin(text: str) -> bool:
    return any("a" <= c.lower() <= "z" for c in text)


def build(rng: random.Random) -> list[dict]:
    notes = []
    for symptom, phrases in FLAG_PHRASES.items():
        for phrase in phrases:
            frames = LATIN_FRAMES if is_latin(phrase) else FLAG_FRAMES
            for frame in rng.sample(frames, min(len(frames), 5)):
                notes.append({"text": frame.format(x=phrase), "red_flag": True, "symptom": symptom})
    for noun in NEGATABLE:
        for frame in NEG_FRAMES:
            notes.append({"text": frame.format(x=noun), "red_flag": False, "symptom": None})
    for phrase in IDIOMS:
        notes.append({"text": phrase, "red_flag": False, "symptom": None})
    for phrase in BENIGN:
        frames = ["{x}"] if is_latin(phrase) else BENIGN_FRAMES
        for frame in rng.sample(frames, min(len(frames), 3)):
            notes.append({"text": frame.format(x=phrase), "red_flag": False, "symptom": None})
    return notes


def main() -> None:
    test_texts = {
        normalize(json.loads(line)["text"])
        for line in (HERE / "synthetic-notes.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    seen, kept, dropped = set(), [], 0
    for note in build(random.Random(SEED)):
        key = normalize(note["text"])
        if key in test_texts:
            dropped += 1
        elif key not in seen:
            seen.add(key)
            kept.append(note)
    with OUT.open("w", encoding="utf-8", newline="\n") as out:
        for i, note in enumerate(kept, 1):
            out.write(json.dumps({"id": f"train-{i:04d}", **note}, ensure_ascii=False) + "\n")
    flags = sum(n["red_flag"] for n in kept)
    print(f"wrote {len(kept)} notes ({flags} red flags) to {OUT}; dropped {dropped} that equal a test note")


if __name__ == "__main__":
    main()
