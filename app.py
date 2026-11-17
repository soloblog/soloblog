"""Starts Soloblog: python app.py. The app itself is the soloblog
package - soloblog/app.py puts it together."""
import os

from fasthtml.common import serve

from soloblog import config


def run_as_soloblog():
    """The image starts as root (a host's disk at /data is root's); this
    hands /data to the image's own soloblog user and carries on as it, so
    a bug in the app can't reach the rest of the container. Outside the
    image (no such user), or not root, nothing changes. If /data can't be
    handed over (a network disk), it stays root and says so."""
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return
    import pwd
    try:
        user = pwd.getpwnam("soloblog")
    except KeyError:
        return
    try:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        for folder, dirs, files in os.walk(config.DATA_DIR):
            for path in [folder] + [os.path.join(folder, name) for name in dirs + files]:
                if os.lstat(path).st_uid != user.pw_uid:
                    os.lchown(path, user.pw_uid, user.pw_gid)
    except OSError as e:
        print(f"[start] couldn't hand {config.DATA_DIR} to the soloblog user, so running as root: {e}")
        return
    os.setgroups([])
    os.setgid(user.pw_gid)
    os.setuid(user.pw_uid)
    os.environ["HOME"] = user.pw_dir


if __name__ == "__main__":
    run_as_soloblog()

from soloblog.app import app  # noqa: F401,E402 - what serve() runs, as app:app

if __name__ == "__main__":
    serve(reload=not config.IS_PROD)
