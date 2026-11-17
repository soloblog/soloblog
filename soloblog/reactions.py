from soloblog.db import get_db

# Emoji reactions under a post (Settings > Appearance > Reading
# experience > Reader reactions). Readers are anonymous, so the limits
# live on the server (see react in routes/public.py): each network
# address can add each reaction to a post once a day, and only so many
# reactions an hour overall. The browser also remembers what it
# reacted, so the buttons show as pressed.

# key -> (emoji, label for screen readers). The key is what's stored.
CHOICES = {
    "heart": ("❤️", "Love"),
    "clap": ("👏", "Applause"),
    "laugh": ("😂", "Funny"),
    "wow": ("😮", "Surprising"),
    "think": ("🤔", "Thought-provoking"),
    "sad": ("😢", "Sad"),
    "fire": ("🔥", "Fire"),
    "party": ("🎉", "Celebrate"),
    "thumbs": ("👍", "Agree"),
}
DEFAULT = "heart,clap,laugh,wow,think"
STYLES = [("like", "A heart Like button"), ("emoji", "A row of emoji reactions"), ("off", "Neither")]


def enabled_keys(value: str) -> list:
    keys = [k.strip() for k in (value or "").split(",") if k.strip() in CHOICES]
    return keys or DEFAULT.split(",")


def counts(slug: str) -> dict:
    rows = get_db().execute("SELECT reaction, count FROM post_reactions WHERE post_slug=?", (slug,)).fetchall()
    return {r["reaction"]: r["count"] for r in rows}


def add(slug: str, key: str) -> dict:
    db = get_db()
    db.execute("INSERT INTO post_reactions (post_slug, reaction, count) VALUES (?, ?, 1) "
               "ON CONFLICT(post_slug, reaction) DO UPDATE SET count = count + 1", (slug, key))
    db.commit()
    return counts(slug)
