"""Captions, tuned to @9d8h0garyh's real captions (fetched 2026-11-07):
most posts have no caption; the ones that do are a dua for سعود القحطاني by name,
sometimes followed by "#قرآن #ذكر". The two duas below are the account's OWN caption
texts, verbatim (posts 18123316778286595 and 18097494584559341), rotated."""

USER_DUAS = [
    "اللَّهُمَّ إِنَّ عَبْدَكَ سُعُودَ القَحْطَانِيَّ فِي ذِمَّتِكَ وَحَبْلِ جِوَارِكَ، فَقِهِ مِنْ فِتْنَةِ القَبْرِ وَعَذَابِ النَّارِ، وَأَنْتَ أَهْلُ الوَفَاءِ وَالحَقِّ، فَاغْفِرْ لَهُ وَارْحَمْهُ، إِنَّكَ أَنْتَ الغَفُورُ الرَّحِيمُ.",
    "اللَّهُمَّ ارْحَمْ سُعُودَ القَحْطَانِيَّ وَاغْفِرْ لَهُ، وَأَكْرِمْ نُزُلَهُ، وَوَسِّعْ مُدْخَلَهُ، وَغَسِلْهُ بِالمَاءِ وَالثَّلْجِ وَالْبَرَدِ، وَنَقِّهِ مِنَ الْخَطَايَا كَمَا يُنَقَّى الثَّوْبُ الأَبْيَضُ مِنَ الدَّنَسِ",
]
TAGS = "#قرآن #ذكر"


def _dua(n):
    return USER_DUAS[n % len(USER_DUAS)]


def verse(it, cfg, n=0):
    return f"{_dua(n)}\n\n{TAGS}"


def hadith(it, cfg, n=0):
    return f"{_dua(n)}\n\n{TAGS}"


def friday_salawat(it, cfg, n=0):
    return f"عصر الجمعة… أكثروا من الصلاة على النبي ﷺ\n\n{TAGS}"


def dua_deceased(it, cfg, n=0):
    return f"لا تنسوا {cfg['deceased_name']} من دعائكم\n\n{TAGS}"
