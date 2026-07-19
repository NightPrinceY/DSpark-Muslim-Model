# -*- coding: utf-8 -*-
"""Generate ~1600 diverse Arabic religious questions covering the full MCP
tool taxonomy, especially the new tools added this session (IslamQA fatwa,
hadith cross-references, mcp.tafsir.net's under-used tools).

Approach: real parameter data (surah names/ayah-counts, hadith topics, fatwa
topics, Quranic roots, reciters) combined with multiple phrasing templates per
category, sampled with a fixed seed for reproducibility and non-repetition.
This mirrors Muslim-mode-finetuning's own build_lora_dataset.py approach
(seeded, deterministic, template+data-driven) -- the established quality bar
for this project, not organic hand-written prose for every line.

Run from the repo root: `python scripts/generate_questions.py`.
"""
import json
import random

random.seed(1435)

# All 114 surahs: (number, Arabic name, ayah count) -- real Quran structure.
SURAHS = [
    (1, "الفاتحة", 7), (2, "البقرة", 286), (3, "آل عمران", 200), (4, "النساء", 176),
    (5, "المائدة", 120), (6, "الأنعام", 165), (7, "الأعراف", 206), (8, "الأنفال", 75),
    (9, "التوبة", 129), (10, "يونس", 109), (11, "هود", 123), (12, "يوسف", 111),
    (13, "الرعد", 43), (14, "إبراهيم", 52), (15, "الحجر", 99), (16, "النحل", 128),
    (17, "الإسراء", 111), (18, "الكهف", 110), (19, "مريم", 98), (20, "طه", 135),
    (21, "الأنبياء", 112), (22, "الحج", 78), (23, "المؤمنون", 118), (24, "النور", 64),
    (25, "الفرقان", 77), (26, "الشعراء", 227), (27, "النمل", 93), (28, "القصص", 88),
    (29, "العنكبوت", 69), (30, "الروم", 60), (31, "لقمان", 34), (32, "السجدة", 30),
    (33, "الأحزاب", 73), (34, "سبأ", 54), (35, "فاطر", 45), (36, "يس", 83),
    (37, "الصافات", 182), (38, "ص", 88), (39, "الزمر", 75), (40, "غافر", 85),
    (41, "فصلت", 54), (42, "الشورى", 53), (43, "الزخرف", 89), (44, "الدخان", 59),
    (45, "الجاثية", 37), (46, "الأحقاف", 35), (47, "محمد", 38), (48, "الفتح", 29),
    (49, "الحجرات", 18), (50, "ق", 45), (51, "الذاريات", 60), (52, "الطور", 49),
    (53, "النجم", 62), (54, "القمر", 55), (55, "الرحمن", 78), (56, "الواقعة", 96),
    (57, "الحديد", 29), (58, "المجادلة", 22), (59, "الحشر", 24), (60, "الممتحنة", 13),
    (61, "الصف", 14), (62, "الجمعة", 11), (63, "المنافقون", 11), (64, "التغابن", 18),
    (65, "الطلاق", 12), (66, "التحريم", 12), (67, "الملك", 30), (68, "القلم", 52),
    (69, "الحاقة", 52), (70, "المعارج", 44), (71, "نوح", 28), (72, "الجن", 28),
    (73, "المزمل", 20), (74, "المدثر", 56), (75, "القيامة", 40), (76, "الإنسان", 31),
    (77, "المرسلات", 50), (78, "النبأ", 40), (79, "النازعات", 46), (80, "عبس", 42),
    (81, "التكوير", 29), (82, "الانفطار", 19), (83, "المطففين", 36), (84, "الانشقاق", 25),
    (85, "البروج", 22), (86, "الطارق", 17), (87, "الأعلى", 19), (88, "الغاشية", 26),
    (89, "الفجر", 30), (90, "البلد", 20), (91, "الشمس", 15), (92, "الليل", 21),
    (93, "الضحى", 11), (94, "الشرح", 8), (95, "التين", 8), (96, "العلق", 19),
    (97, "القدر", 5), (98, "البينة", 8), (99, "الزلزلة", 8), (100, "العاديات", 11),
    (101, "القارعة", 11), (102, "التكاثر", 8), (103, "العصر", 3), (104, "الهمزة", 9),
    (105, "الفيل", 5), (106, "قريش", 4), (107, "الماعون", 7), (108, "الكوثر", 3),
    (109, "الكافرون", 6), (110, "النصر", 3), (111, "المسد", 5), (112, "الإخلاص", 4),
    (113, "الفلق", 5), (114, "الناس", 6),
]

TAFSIR_BOOKS = [
    "ar-tafsir-muyassar", "ar-tafseer-al-saddi", "ar-tafsir-ibn-kathir",
    "ar-tafsir-al-wasit", "ar-tafsir-al-baghawi", "ar-tafseer-al-qurtubi",
    "ar-tafseer-tanwir-al-miqbas", "ar-tafsir-al-tabari",
]

RECITERS = [
    "المنشاوي", "العفاسي", "السديس", "الشريم", "الحصري", "عبد الباسط",
    "ماهر المعيقلي", "الغامدي", "ناصر القطامي", "ياسر الدوسري", "سعود الشريم",
    "محمد الطبلاوي", "أحمد العجمي", "مصطفى إسماعيل",
]

HADITH_TOPICS = [
    "بر الوالدين", "الصدق", "الصبر", "التوكل على الله", "حسن الخلق", "الرحمة",
    "الصلاة على وقتها", "صلة الرحم", "قيام الليل", "الصدقة", "الحياء", "التوبة",
    "الذكر بعد الصلاة", "فضل طلب العلم", "آداب الطعام", "آداب النوم", "الأمانة",
    "الوفاء بالعهد", "حسن الجوار", "إفشاء السلام", "بر اليتيم", "إكرام الضيف",
    "الصيام", "الحج", "الزكاة", "الغيبة والنميمة", "الكذب", "الظلم",
    "التواضع", "الشكر", "الدعاء", "التفكر في خلق الله", "فضل الوضوء",
    "فضل سورة الكهف", "فضل يوم الجمعة", "علامات الساعة", "الجنة والنار",
    "الحياة الآخرة", "فضل الصلاة على النبي", "فضل الاستغفار", "آداب المجلس",
    "حقوق الجار", "حقوق الزوجة", "تربية الأبناء", "طاعة الوالدين", "الجهاد",
    "فضل العشر الأوائل من ذي الحجة", "فضل شهر رمضان", "قصص الأنبياء",
]

FATWA_TOPICS = [
    "حكم التعامل بالفوائد البنكية", "حكم التأمين على الحياة", "حكم زكاة الأسهم",
    "حكم العمل في شركات التقسيط", "حكم بيع العملات الرقمية", "حكم المضاربة في الأسواق المالية",
    "حكم الاستماع إلى الموسيقى", "حكم تعليق الصور الفوتوغرافية في المنازل",
    "حكم لبس الذهب المحلق للرجال", "حكم صلاة الجماعة للمرأة في البيت",
    "حكم الجمع بين الصلاتين للمسافر", "حكم قصر الصلاة في السفر",
    "حكم الإفطار في رمضان للمريض", "حكم صيام يوم الشك", "حكم زكاة الفطر بالمال",
    "حكم التبرع بالأعضاء بعد الموت", "حكم نقل الدم بين الأقارب",
    "حكم التلقيح الصناعي بين الزوجين", "حكم تحديد النسل", "حكم عمليات التجميل",
    "حكم استخدام مستحضرات التجميل التي تحتوي كحولاً", "حكم العمل في البنوك الربوية",
    "حكم اللقطة الموجودة في الطريق العام", "حكم بيع الدين بالتقسيط",
    "حكم المرابحة المصرفية", "حكم عقد التورق", "حكم الشركة بين الأقارب",
    "حكم دفع الزكاة لغير المسلمين", "حكم إخراج الزكاة قبل موعدها",
    "حكم صيام الحامل والمرضع", "حكم قضاء الصلاة الفائتة عمداً",
    "حكم من نسي ركناً من أركان الصلاة", "حكم سجود السهو",
    "حكم من ترك الصلاة كسلاً", "حكم زواج المسيار", "حكم تعدد الزوجات بدون رضا الأولى",
    "حكم الخلع في الشريعة الإسلامية", "حكم حضانة الأطفال بعد الطلاق",
    "حكم النفقة على الزوجة الناشز", "حكم بيع المنتجات عبر الإنترنت بالعمولة",
    "حكم التبرع بالدم للأجانب", "حكم استئجار الأرحام", "حكم بيع الأعضاء البشرية",
    "حكم التأمين الصحي الإلزامي", "حكم شراء المنازل بالتمويل البنكي",
    "حكم الاستثمار في صناديق الأسهم المختلطة", "حكم بيع العربون",
    "حكم الوكالة بأجر في البيع والشراء", "حكم الصرافة الإلكترونية للعملات",
    "حكم قروض الطلاب الجامعية", "حكم العمل بالعمولة في التسويق الشبكي",
    "حكم إجارة الأرض الزراعية بجزء من المحصول", "حكم بيع التقسيط بزيادة عن السعر النقدي",
    "حكم استخدام بطاقات الائتمان", "حكم المتاجرة بالفوركس", "حكم صناديق التقاعد الاستثمارية",
    "حكم دفع الديات في حوادث السيارات", "حكم التبني في الإسلام",
    "حكم استخدام وسائل منع الحمل المؤقتة",
]

QURANIC_ROOTS = [
    ("رحم", "الرحمة"), ("صبر", "الصبر"), ("شكر", "الشكر"), ("علم", "العلم"),
    ("هدى", "الهداية"), ("خلق", "الخلق"), ("عبد", "العبادة"), ("سجد", "السجود"),
    ("صلح", "الصلاح"), ("ظلم", "الظلم"), ("كفر", "الكفر"), ("أمن", "الأمان"),
    ("سلم", "السلام"), ("حمد", "الحمد"), ("نور", "النور"), ("حسن", "الإحسان"),
]

NAMED_VERSES = [
    ("آية الكرسي", 2, 255), ("آية الدَّين", 2, 282), ("آية النور", 24, 35),
    ("آية الكوثر", 108, 1),
]

NAMED_SURAHS_NICKNAMES = [
    ("قلب القرآن", 36), ("عروس القرآن", 55), ("سنام القرآن", 2),
]


def s():
    return random.choice(SURAHS)


def sv():
    surah = s()
    ayah = random.randint(1, surah[2])
    return surah, ayah


def uniq_extend(pool, items):
    for it in items:
        if it not in pool:
            pool.append(it)


rows = []


def add(text, intent):
    rows.append({"text": text, "intent": intent})


# --- tafsir_verse (150) ---
TAFSIR_VERSE_TEMPLATES = [
    "ما تفسير الآية {ayah} من سورة {surah}؟",
    "اشرح لي معنى الآية رقم {ayah} من سورة {surah}.",
    "ما معنى قوله تعالى في الآية {ayah} من سورة {surah}؟",
    "وضّح لي تفسير الآية {ayah} من سورة {surah} حسب تفسير {book}.",
    "ممكن تفسّر لي الآية {ayah} من سورة {surah}؟",
]
for _ in range(150):
    surah, ayah = sv()
    tmpl = random.choice(TAFSIR_VERSE_TEMPLATES)
    text = tmpl.format(ayah=ayah, surah=surah[1], book=random.choice(TAFSIR_BOOKS))
    add(text, "tafsir_verse")

# --- tafsir_surah (100) ---
TAFSIR_SURAH_TEMPLATES = [
    "أريد تفسير سورة {surah} كاملة.",
    "اشرح لي تفسير سورة {surah} من كتاب {book}.",
    "ما تفسير سورة {surah}؟",
    "ممكن تفسير كامل لسورة {surah}؟",
]
for _ in range(100):
    surah = s()
    tmpl = random.choice(TAFSIR_SURAH_TEMPLATES)
    text = tmpl.format(surah=surah[1], book=random.choice(TAFSIR_BOOKS))
    add(text, "tafsir_surah")

# --- surah_info (60) ---
SURAH_INFO_TEMPLATES = [
    "كم عدد آيات سورة {surah}؟",
    "هل سورة {surah} مكية أم مدنية؟",
    "أخبرني معلومات عن سورة {surah}.",
    "ما اسم آخر السورة وأول سورة {surah}؟",
]
for _ in range(60):
    surah = s()
    tmpl = random.choice(SURAH_INFO_TEMPLATES)
    add(tmpl.format(surah=surah[1]), "surah_info")

# --- nuzool (60) ---
NUZOOL_TEMPLATES = [
    "لماذا نزلت سورة {surah}؟",
    "ما سبب نزول سورة {surah}؟",
    "ما سبب نزول الآية {ayah} من سورة {surah}؟",
]
for _ in range(60):
    surah, ayah = sv()
    tmpl = random.choice(NUZOOL_TEMPLATES)
    add(tmpl.format(surah=surah[1], ayah=ayah), "nuzool")

# --- qeraat (50) ---
for _ in range(50):
    surah, ayah = sv()
    tmpl = random.choice([
        "ما القراءات الواردة في الآية {ayah} من سورة {surah}؟",
        "هل هناك قراءات متعددة للآية {ayah} من سورة {surah}؟",
    ])
    add(tmpl.format(surah=surah[1], ayah=ayah), "qeraat")

# --- analyze_word / root analysis (60) ---
for _ in range(60):
    root, meaning = random.choice(QURANIC_ROOTS)
    tmpl = random.choice([
        "حلّل لي كلمة «{root}» من الناحية اللغوية.",
        "ما معنى وجذر كلمة «{root}» في القرآن؟",
        "ما هو جذر كلمة «{meaning}»؟",
        "ما الإعراب والصرف لكلمة «{root}»؟",
        "حلل لي كلمة «{meaning}» صرفياً ونحوياً.",
    ])
    add(tmpl.format(root=root, meaning=meaning), "analyze_word")

# --- search_quran_text (60) ---
for _ in range(60):
    root, meaning = random.choice(QURANIC_ROOTS)
    tmpl = random.choice([
        "ابحث لي عن كل المواضع التي ذُكرت فيها كلمة «{meaning}» في القرآن.",
        "أين ورد لفظ «{root}» في القرآن الكريم؟",
        "كم مرة ذُكرت كلمة «{meaning}» في القرآن؟",
        "في أي سور وردت كلمة «{root}»؟",
        "ابحث عن عبارة «{meaning}» في نص القرآن.",
    ])
    add(tmpl.format(root=root, meaning=meaning), "search_quran_text")

# --- search_in_tafsir (50) ---
for _ in range(50):
    topic = random.choice(HADITH_TOPICS + [m for _, m in QURANIC_ROOTS])
    tmpl = random.choice([
        "ابحث لي في التفسير عن آيات تتحدث عن {topic}.",
        "ما هي الآيات التي تتحدث عن {topic}؟",
    ])
    add(tmpl.format(topic=topic), "search_in_tafsir")

# --- play_ayah (80) ---
for _ in range(80):
    surah, ayah = sv()
    reciter = random.choice(RECITERS)
    tmpl = random.choice([
        "شغّل لي الآية رقم {ayah} من سورة {surah} بصوت الشيخ {reciter}.",
        "أسمعني الآية {ayah} من سورة {surah}.",
        "اقرأ لي الآية رقم {ayah} من سورة {surah} بصوت {reciter}.",
    ])
    add(tmpl.format(ayah=ayah, surah=surah[1], reciter=reciter), "play_ayah")

# --- play_surah (80) ---
for _ in range(80):
    surah = s()
    reciter = random.choice(RECITERS)
    tmpl = random.choice([
        "شغّل لي سورة {surah} بصوت الشيخ {reciter}.",
        "أريد الاستماع إلى سورة {surah} بصوت {reciter}.",
        "اقرأ لي سورة {surah} كاملة.",
        "سمّعني سورة {surah}.",
    ])
    add(tmpl.format(surah=surah[1], reciter=reciter), "play_surah")

# --- named verses/surahs (nicknames, 20) ---
for name, surah_num, ayah_num in NAMED_VERSES:
    surah_name = next(sname for n, sname, _ in SURAHS if n == surah_num)
    add(f"اقرأ لي {name}.", "play_ayah_named")
    add(f"ما تفسير {name}؟", "tafsir_verse_named")
for name, surah_num in NAMED_SURAHS_NICKNAMES:
    surah_name = next(sname for n, sname, _ in SURAHS if n == surah_num)
    add(f"شغّل لي {name}.", "play_surah_named")

# --- search_hadith (100) ---
for _ in range(100):
    topic = random.choice(HADITH_TOPICS)
    tmpl = random.choice([
        "أعطني حديثاً صحيحاً عن {topic}.",
        "ابحث لي عن أحاديث تتحدث عن {topic}.",
        "هل يوجد حديث نبوي عن {topic}؟",
        "أريد أحاديث نبوية شريفة عن {topic}.",
    ])
    add(tmpl.format(topic=topic), "search_hadith")

# --- fetch_hadith (60) ---
COLLECTIONS = ["صحيح البخاري", "صحيح مسلم", "سنن أبي داود", "سنن الترمذي", "سنن النسائي", "سنن ابن ماجه", "رياض الصالحين"]
for _ in range(60):
    coll = random.choice(COLLECTIONS)
    num = random.randint(1, 500)
    tmpl = random.choice([
        "أريد الحديث رقم {num} من {coll}.",
        "اذكر لي الحديث رقم {num} في {coll}.",
    ])
    add(tmpl.format(num=num, coll=coll), "fetch_hadith")

# --- fetch_cross_references (60, NEW tool) ---
for _ in range(60):
    topic = random.choice(HADITH_TOPICS)
    tmpl = random.choice([
        "هل ورد حديث «{topic}» بروايات مشابهة في كتب أخرى؟",
        "أعطني كل الأحاديث المشابهة لحديث {topic} عبر الكتب المختلفة.",
        "هل هذا الحديث عن {topic} متفق عليه بين البخاري ومسلم؟",
    ])
    add(tmpl.format(topic=topic), "fetch_cross_references")

# --- fatwa_search (150, NEW tool: islamqa search_answers) ---
for _ in range(150):
    topic = random.choice(FATWA_TOPICS)
    tmpl = random.choice([
        "{topic}؟",
        "ما {topic}؟",
        "أريد أن أعرف {topic}.",
        "ما رأي أهل العلم في {topic}؟",
    ])
    text = tmpl.format(topic=topic[0].lower() + topic[1:] if not topic.startswith("حكم") else topic)
    add(text, "fatwa_search")

# --- fetch_answer (40, NEW tool: islamqa fetch_answer via category) ---
CATEGORIES = ["الطهارة", "الصلاة", "الزكاة", "الصيام", "الحج", "المعاملات المالية", "الأسرة والمرأة", "العقيدة"]
for _ in range(40):
    cat = random.choice(CATEGORIES)
    add(f"اعطني أهم الفتاوى المتعلقة بموضوع {cat}.", "fetch_answer")

# --- validate_recitation (40) ---
RECITATION_SNIPPETS = [
    "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
    "قُلْ هُوَ اللَّهُ أَحَدٌ",
    "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
    "إِنَّا أَعْطَيْنَاكَ الْكَوْثَرَ",
    "وَالْعَصْرِ إِنَّ الْإِنسَانَ لَفِي خُسْرٍ",
]
for _ in range(40):
    snippet = random.choice(RECITATION_SNIPPETS)
    tmpl = random.choice([
        "أريد أن تصحح لي تلاوة هذه الآية: {snippet}",
        "{snippet} — هل قراءتي صحيحة؟",
        "صحح لي تلاوتي لهذه الآية: {snippet}",
    ])
    add(tmpl.format(snippet=snippet), "validate_recitation")

# --- ruling / ruling_v2 (measured, sensitive fiqh, 80) ---
SENSITIVE_TOPICS = [
    "تارك الصلاة", "من يمارس السحر", "من يتعامل بالربا", "من يشرب الخمر",
    "من يمارس الشعوذة", "من يسب الدين", "من يتهاون في الصيام", "من يظلم الناس",
    "من يقطع رحمه", "من يترك الحجاب", "من يتعامل مع البنوك الربوية",
    "من يستهزئ بالصحابة", "من ينكر السنة النبوية", "من يوالي أعداء الدين",
    "من يترك صيام رمضان بلا عذر", "من يمتنع عن دفع الزكاة", "من يعامل والديه بقسوة",
    "من يمارس الغش في البيع والشراء", "من يفشي أسرار الناس", "من يحلف بغير الله",
    "من يتهاون في أداء الأمانة",
]
for _ in range(80):
    topic = random.choice(SENSITIVE_TOPICS)
    tmpl = random.choice([
        "ما حكم {topic}؟",
        "هل {topic} كافر؟",
        "ما رأي الشرع في {topic}؟",
    ])
    add(tmpl.format(topic=topic), "ruling_v2")

# --- persona/identity (all unique, no sampling needed) ---
PERSONA_QS = [
    "من أنت؟", "من صنعك؟", "من هو مطورك؟", "ما اسمك؟", "ماذا تستطيع أن تفعل؟",
    "ما هي إمكانياتك؟", "لماذا تم إنشاؤك؟", "هل أنت إنسان أم برنامج؟",
    "من هو منشئك؟", "ما هدفك؟", "هل يمكنك التحدث بلغات أخرى؟", "كيف تعمل؟",
    "من هو صانعك؟", "ما الذي يمكنك مساعدتي فيه؟", "عرّفني بنفسك.",
    "هل أنت مبرمج أم شخص حقيقي؟", "من قام ببرمجتك؟", "ما دورك بالضبط؟",
    "اشرح لي وظيفتك.", "هل عندك اسم مميز؟", "من أنشأ هذا التطبيق؟",
    "بمن تفتخر من صانعيك؟", "ما هي حدود قدراتك؟", "هل يمكنك الإجابة عن كل شيء؟",
    "ما اللغات التي تتقنها؟", "من المسؤول عن تطويرك؟", "ما نوع الذكاء الذي تستخدمه؟",
    "كم عمرك؟", "أين تعيش؟", "هل لديك مشاعر؟",
]
for q in PERSONA_QS:
    add(q, "persona")

# --- scope_redirect (all unique) ---
OFF_TOPIC = [
    "ما رأيك في مباراة الأمس؟", "اكتب لي كود بايثون لحساب الأعداد الأولية.",
    "ما هي أفضل وجهة سياحية للصيف؟", "عندي صداع، ما العلاج؟",
    "ما توقعاتك للطقس غداً؟", "من سيفوز بكأس العالم القادم؟",
    "ساعدني في حل معادلة رياضية.", "ما رأيك في آخر أخبار السياسة؟",
    "اقترح علي فيلماً جيداً.", "ما هو سعر الدولار اليوم؟",
    "من هو أفضل لاعب كرة قدم في التاريخ؟", "ساعدني في كتابة سيرة ذاتية.",
    "ما هي أخبار البورصة اليوم؟", "أعطني وصفة طبخ لذيذة.",
    "ما رأيك في الذكاء الاصطناعي التنافسي؟", "احسب لي مساحة دائرة نصف قطرها خمسة.",
    "ما هو أفضل هاتف في السوق حالياً؟", "متى ستنتهي الحرب في العالم؟",
    "أعطني نصائح للياقة البدنية.", "ترجم لي هذه الجملة إلى الفرنسية.",
]
for q in OFF_TOPIC:
    add(q, "scope_redirect")

# --- greeting (all unique) ---
GREETINGS = [
    "السلام عليكم ورحمة الله وبركاته", "مرحباً", "أهلاً يا مسلم",
    "صباح الخير", "مساء الخير، كيف حالك؟", "السلام عليكم", "أهلاً وسهلاً",
    "كيف حالك اليوم؟", "تصبح على خير", "حياك الله",
]
for q in GREETINGS:
    add(q, "greeting")

# --- english_mixed (all unique) ---
ENGLISH_QS = [
    "Can you tell me about the five pillars of Islam?",
    "What is the tafsir of Surah Al-Baqarah?",
    "give me a hadith about honesty",
    "What is the ruling on music in Islam?",
    "Tell me about the Night of Power.",
    "What does Surah Al-Ikhlas mean?",
    "Can you recite Surah Al-Fatiha?",
    "Who are the ten companions promised paradise?",
    "Who created you?",
    "What is your name?",
    "Can you help me with my Quran memorization?",
    "give me a quick hadith عن الصدق",
    "What is the ruling on bank interest?",
    "How many surahs are in the Quran?",
]
for q in ENGLISH_QS:
    add(q, "english_mixed")

# --- NEW tafsir.net extra tools (11 categories, ~15 each = 165) ---
for _ in range(15):
    surah, ayah = sv()
    add(f"ما هي المصادر التي تغطي تفسير الآية {ayah} من سورة {surah[1]}؟", "list_sources_for_ayah")
for _ in range(15):
    root, meaning = random.choice(QURANIC_ROOTS)
    add(f"أعطني كل مواضع ورود جذر «{root}» في القرآن.", "find_root_occurrences")
for _ in range(15):
    root, meaning = random.choice(QURANIC_ROOTS)
    add(f"ما هي إحصاءات جذر «{root}» في القرآن؟ كم مرة ورد وفي أي سور؟", "get_root_stats")
for _ in range(15):
    add(random.choice([
        "أعطني نظرة عامة شاملة على إحصاءات القرآن الكريم.",
        "كم عدد كلمات القرآن الكريم وحروفه؟",
    ]), "get_quran_overview")
for _ in range(15):
    page = random.randint(1, 604)
    add(f"ما هي فوائد الصفحة رقم {page} من المصحف؟", "get_page_fawaed")
for _ in range(15):
    surah = s()
    add(f"أعطني إحصاءات مفصلة عن سورة {surah[1]}: عدد الكلمات والحروف وأطول كلمة.", "get_surah_statistics")
for _ in range(15):
    surah, ayah = sv()
    add(f"اجلب لي نص الآية {ayah} من سورة {surah[1]} بالرسم العثماني.", "fetch_ayah")
for _ in range(15):
    surah, ayah = sv()
    add(f"اجلب لي تفسير الآية {ayah} من سورة {surah[1]} من أكثر من مصدر.", "fetch_tafsir")
for _ in range(15):
    add("ما هي مصادر التفسير المتاحة لديك؟", "list_tafsir_sources")
for _ in range(15):
    add("ما هي مصادر علوم القرآن المتاحة لديك؟", "list_science_sources")
for _ in range(15):
    add("اذكر لي كل مصادر المحتوى المتاحة لديك حول القرآن.", "list_all_sources")

# Dedup while preserving order, then assign ids
seen = set()
final = []
for r in rows:
    if r["text"] in seen:
        continue
    seen.add(r["text"])
    final.append(r)

random.shuffle(final)

out_path = "data/sources/seed_generated.jsonl"
with open(out_path, "w", encoding="utf-8") as f:
    for i, r in enumerate(final, start=1):
        f.write(json.dumps({
            "id": f"gen_{i:04d}",
            "text": r["text"],
            "behavior": "",
            "intent": r["intent"],
            "source": "generated",
        }, ensure_ascii=False) + "\n")

print("total generated (post-dedup):", len(final))

from collections import Counter
c = Counter(r["intent"] for r in final)
for k, v in sorted(c.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
