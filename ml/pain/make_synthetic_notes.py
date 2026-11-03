"""Write ml/pain/synthetic-notes.jsonl: labelled Egyptian-Arabic patient pain notes (synthetic).

Written by Claude (2026-11-03) to measure the red-flag check, NOT real patient text and
NOT reviewed by a physiotherapist yet. Notes were written to go beyond the lexicon on
purpose: paraphrases, spelling slips, Franco-Arabic (arabizi), formal Arabic (msa),
negated mentions and benign notes. Every second note of each group goes to the test split;
change the lexicon only by looking at dev.

  py -3.14 ml\\pain\\make_synthetic_notes.py
"""

import json
from pathlib import Path

OUT = Path(__file__).with_name("synthetic-notes.jsonl")

# (symptom, style, text); symptom None = no red flag
RED_FLAGS = [
    ("chest pain", "paraphrase", "حاسس بوجع في صدري من ساعة ما خلصت التمرين"),
    ("chest pain", "lexicon", "صدري واجعني أوي ومش عارف أنام"),
    ("chest pain", "paraphrase", "في تقل على صدري كده زي حاجة كابسة عليه"),
    ("chest pain", "lexicon", "عندي ألم في الصدر بيروح للدراع الشمال"),
    ("chest pain", "paraphrase", "قلبي بيوجعني وأنا بعمل السكوات"),
    ("chest pain", "paraphrase", "حاسة بضغط جامد في الضلوع من قدام"),
    ("chest pain", "arabizi", "sadry wag3ny awy ba3d el tamreen"),
    ("chest pain", "english", "my chest hurts after the exercise"),
    ("chest pain", "paraphrase", "وجع جامد في الصدر"),
    ("chest pain", "typo", "صدرى بيوجعنى"),
    ("difficulty breathing", "lexicon", "مش قادر أتنفس كويس من الصبح"),
    ("difficulty breathing", "lexicon", "نفسي مقطوع بعد كام تكرار بس"),
    ("difficulty breathing", "paraphrase", "بنهج جامد وأنا طالع السلم"),
    ("difficulty breathing", "paraphrase", "حاسس إني مخنوق ومش لاحق نفسي"),
    ("difficulty breathing", "lexicon", "عندي ضيق في النفس"),
    ("difficulty breathing", "paraphrase", "مش عارفة آخد نفسي"),
    ("difficulty breathing", "arabizi", "msh 2ader at2nafes"),
    ("difficulty breathing", "typo", "نفسى مقطوع"),
    ("difficulty breathing", "msa", "صعوبة في التنفس عند بذل أي مجهود"),
    ("difficulty breathing", "paraphrase", "نهجانة اوي النهارده"),
    ("calf pain or swelling", "lexicon", "سمانة رجلي الشمال وارمة وسخنة"),
    ("calf pain or swelling", "lexicon", "بطن رجلي بيوجعني ومشدود"),
    ("calf pain or swelling", "lexicon", "عندي شد في رجلي اليمين مش بيروح"),
    ("calf pain or swelling", "paraphrase", "السمانة حمرا ووارمة"),
    ("calf pain or swelling", "paraphrase", "رجلي اليمين كلها وارمة من تحت الركبة"),
    ("calf pain or swelling", "paraphrase", "بطة رجلي بتوجعني اوي"),
    ("calf pain or swelling", "arabizi", "fe wag3 gamed fe semanet regly"),
    ("calf pain or swelling", "typo", "سمانة رجلى بتوجعني"),
    ("calf pain or swelling", "msa", "ألم في ربلة الساق مع تورم"),
    ("calf pain or swelling", "paraphrase", "رجلي سخنة ولونها متغير"),
    ("fever or shivering", "lexicon", "عندي سخونية من امبارح"),
    ("fever or shivering", "lexicon", "حرارتي عالية ٣٨ ونص"),
    ("fever or shivering", "paraphrase", "جسمي بيترعش وبردان"),
    ("fever or shivering", "lexicon", "جالي رعشة بالليل"),
    ("fever or shivering", "paraphrase", "حاسس إني سخن وتعبان"),
    ("fever or shivering", "msa", "عندي حمى"),
    ("fever or shivering", "arabizi", "3andy sokhonya"),
    ("fever or shivering", "typo", "عندي سخونيه"),
    ("fever or shivering", "paraphrase", "قست الحرارة طلعت ٣٩"),
    ("fever or shivering", "msa", "ارتفاع في درجة الحرارة"),
    ("wound discharge", "lexicon", "الجرح فيه صديد"),
    ("wound discharge", "lexicon", "الجرح بينز مية صفرا"),
    ("wound discharge", "paraphrase", "مكان العملية بيطلع منه سايل"),
    ("wound discharge", "paraphrase", "الجرح ريحته وحشة ولونه احمر"),
    ("wound discharge", "msa", "توجد إفرازات من مكان الغرز"),
    ("wound discharge", "arabizi", "el gar7 beynez"),
    ("wound discharge", "typo", "الجرح بينذ"),
    ("wound discharge", "lexicon", "شايف صديد على الشاش"),
    ("knee swelling or redness", "lexicon", "ركبتي وارمة ومش بتخف"),
    ("knee swelling or redness", "lexicon", "ركبتي حمرا وسخنة"),
    ("knee swelling or redness", "lexicon", "الورم بيزيد كل يوم"),
    ("knee swelling or redness", "paraphrase", "الركبة منفوخة أكتر من الأول"),
    ("knee swelling or redness", "typo", "ركبتى ورمانه"),
    ("knee swelling or redness", "arabizi", "rokbety warma"),
    ("knee swelling or redness", "msa", "تورم الركبة يزداد"),
    ("knee swelling or redness", "paraphrase", "ركبتي محمرة ووارمة"),
    ("numbness", "lexicon", "عندي تنميل في صوابع رجلي"),
    ("numbness", "paraphrase", "إيدي منملة"),
    ("numbness", "typo", "رجلي منمله"),
    ("numbness", "paraphrase", "حاسس رجلي نايمة ومش حاسس بيها"),
    ("numbness", "lexicon", "فيه تنميل في دراعي الشمال"),
    ("numbness", "arabizi", "tanmeel fe regly"),
    ("numbness", "msa", "فقدت الإحساس في القدم"),
    ("numbness", "paraphrase", "صوابعي بتنمل"),
    ("dizziness or fainting", "lexicon", "جاتلي دوخة وأنا بقوم"),
    ("dizziness or fainting", "lexicon", "أنا دايخ شوية بعد التمرين"),
    ("dizziness or fainting", "paraphrase", "الدنيا بتلف بيا"),
    ("dizziness or fainting", "paraphrase", "حسيت إني هقع وعيني زغللت"),
    ("dizziness or fainting", "typo", "أنا دايخه"),
    ("dizziness or fainting", "arabizi", "dayekh awy"),
    ("dizziness or fainting", "msa", "شعرت بدوار"),
    ("dizziness or fainting", "typo", "عندي دوخه"),
    ("dizziness or fainting", "paraphrase", "أغمى عليا وأنا بتمرن"),
    ("sharp or sudden pain", "lexicon", "ألم حاد في الركبة لما بنزل"),
    ("sharp or sudden pain", "lexicon", "وجع زي السكينة في ضهري"),
    ("sharp or sudden pain", "paraphrase", "وجع حاد في الركبة"),
    ("sharp or sudden pain", "paraphrase", "وجع بيخزّق في الركبة"),
    ("sharp or sudden pain", "paraphrase", "حاجة بتشكني جامد في الركبة"),
    ("sharp or sudden pain", "arabizi", "alam 7ad fel rokba"),
    ("sharp or sudden pain", "paraphrase", "سمعت طقة في ركبتي ووجعتني جامد"),
    ("sharp or sudden pain", "msa", "ألم شديد ومفاجئ"),
]

# a red-flag word appears but the note says it is absent, hypothetical, or an idiom
NOT_FLAGS = [
    ("negated", "مفيش دوخة الحمد لله"),
    ("negated", "مش حاسس بأي تنميل"),
    ("negated", "مفيش سخونية ولا حاجة"),
    ("negated", "صدري كويس، بس رجلي تعبانة شوية"),
    ("negated", "الجرح ناشف ومفيش صديد"),
    ("negated", "ركبتي مش وارمة النهارده"),
    ("negated", "نفسي مش مقطوع زي الأول"),
    ("negated", "الدكتور قال لو حصل دوخة أكلمه"),
    ("negated", "مش دايخ خالص"),
    ("idiom", "صدري مفتوح النهارده وعندي طاقة"),
    ("idiom", "الجو حر ونفسي مش في التمرين النهارده"),
    ("idiom", "قلبي فرحان إني قدرت أكمل"),
    ("benign", "رجلي تعبانة شوية بعد التمرين"),
    ("benign", "عضلات فخدي مشدودة زي كل مرة"),
    ("benign", "الوجع خفيف ٣ من ١٠"),
    ("benign", "حاسس بشوية تيبس الصبح بيروح بعد ما أتحرك"),
    ("benign", "التمرين كان سهل النهارده"),
    ("benign", "ركبتي بتطقطق بس مش بتوجع"),
    ("benign", "تعبت شوية بس كملت"),
    ("benign", "مفيش وجع خالص"),
    ("benign", "الوجع زي امبارح، مش أكتر"),
    ("benign", "حاسس بشد خفيف في الفخد من ورا"),
    ("benign", "ضهري واجعني شوية من القعدة"),
    ("benign", "نمت كويس والوجع أقل"),
    ("benign", "عملت ٨ تكرارات من غير مشاكل"),
    ("benign", "الركبة أحسن من الأسبوع اللي فات"),
    ("benign", "حاسة بحرقان خفيف في العضلة"),
    ("benign", "kont ta3ban shwaya bas tamam"),
    ("benign", "pain 2/10 today"),
    ("benign", "مش قادر أعمل آخر تكرارتين من التعب"),
    ("benign", "عرقت كتير"),
    ("benign", "إيدي تعبانة من شيل الشنط"),
    ("benign", "الحمد لله ماشية كويس"),
    ("benign", "الوجع بيروح لما أرتاح"),
    ("benign", "مقدرتش أنزل لتحت أوي في السكوات"),
    ("benign", "ركبتي ناشفة الصبح شوية"),
    ("benign", "شوية ألم في الكتف لما برفع إيدي فوق أوي"),
    ("benign", "pain fel rokba 3 men 10"),
    ("benign", "أخدت المسكن وبقيت أحسن"),
    ("benign", "مفيش أي جديد"),
]


def rows():
    for symptom, style, text in RED_FLAGS:
        yield {"text": text, "red_flag": True, "symptom": symptom, "style": style}, symptom
    for style, text in NOT_FLAGS:
        yield {"text": text, "red_flag": False, "symptom": None, "style": style}, style


def main() -> None:
    count: dict[str, int] = {}
    with OUT.open("w", encoding="utf-8", newline="\n") as out:
        for i, (row, group) in enumerate(rows(), 1):
            count[group] = count.get(group, 0) + 1
            split = "test" if count[group] % 2 == 0 else "dev"
            out.write(json.dumps({"id": f"syn-{i:03d}", "split": split, **row}, ensure_ascii=False) + "\n")
    print(f"wrote {sum(count.values())} notes to {OUT}")


if __name__ == "__main__":
    main()
