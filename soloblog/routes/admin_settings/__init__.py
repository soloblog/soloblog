"""Settings, by area. Other code imports from here:
`from soloblog.routes.admin_settings import settings_index`, whichever file
it lives in. Every file adds its routes to the one router, `ar`."""
from soloblog.routes.admin_settings.base import *  # noqa: F401,F403
from soloblog.routes.admin_settings.saves import *  # noqa: F401,F403
from soloblog.routes.admin_settings.design import *  # noqa: F401,F403
from soloblog.routes.admin_settings.panels import *  # noqa: F401,F403
from soloblog.routes.admin_settings.integrations import *  # noqa: F401,F403
from soloblog.routes.admin_settings.pages import *  # noqa: F401,F403
from soloblog.routes.admin_settings.base import _toast_redirect  # noqa: F401
from soloblog.routes.admin_settings.pages import _cached  # noqa: F401
