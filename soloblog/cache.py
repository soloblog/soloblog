import threading

# One generation number for everything cached in this process from the
# database: the settings (settings.py) and rendered posts (render.py).
# Anything that changes what they depend on - a setting, an image's alt
# text or credit, an upload, a restored backup - calls bump(), and every
# cache built under an older number is simply rebuilt on its next use.
# Soloblog is a single process, so there's nothing to share across.

_lock = threading.Lock()
_generation = 0


def generation():
    # a demo visitor's copy (config.VISITOR_DIR) is a site of its own:
    # nothing cached from one is used for another
    from soloblog import config
    visitor = config.VISITOR_DIR.get()
    return (visitor, _generation) if visitor else _generation


def bump():
    global _generation
    with _lock:
        _generation += 1
