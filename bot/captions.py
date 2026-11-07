"""Caption templates. Provisional: to be re-tuned to the account's real captions
once the last ~40 posts are fetched (STEP 3). Keep them short and calm."""


def _tail(cfg):
    return f"صدقة جارية عن {cfg['deceased_name']}، رحمه الله.\n\n{cfg['hashtags']}"


def verse(it, cfg):
    return f"{it['title']}\n\n{it['source']}\n\n{_tail(cfg)}"


def hadith(it, cfg):
    return f"{it['title']}\n\n{it['source']}\n\n{_tail(cfg)}"


def friday_salawat(it, cfg):
    return (f"عصر الجمعة… أكثروا من الصلاة على النبي ﷺ\n\n{it['source']}\n\n{_tail(cfg)}")


def dua_deceased(it, cfg):
    return (f"لا تنسوا {cfg['deceased_name']} من دعائكم\n\n{it['source']}\n\n"
            f"{cfg['hashtags']}")
