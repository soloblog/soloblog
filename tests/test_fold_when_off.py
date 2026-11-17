"""A feature that's switched off is its switch and one line; the rest of its
page shows when the switch goes on (data-shown-for on the switch)."""
import re

import pytest

from soloblog import settings

SWITCHED = [  # (tab, switch, what's only there while it's on)
    ("messages", "comments_enabled", "comments_autoload"),
    ("messages", "contact_enabled", "contact_intro"),
    ("members", "members_enabled", "members_welcome"),
    ("sharing", "activitypub_enabled", "activitypub_username"),
]


@pytest.fixture
def keep():
    keys = [k for _, k, _ in SWITCHED] + ["analytics_provider"]
    before = {k: settings.get(k) for k in keys}
    yield
    settings.set_many(before)


def _hidden_wrapper(page, field, rule):
    """Whether the wrapper with this rule is hidden - and holds `field`."""
    start = page.index(f'data-shown-for="{rule}"')
    tag = page[page.rfind("<div", 0, start):page.index(">", start)]
    assert page.index(f'name="{field}"') > start
    return " hidden" in tag


@pytest.mark.parametrize("tab,switch,field", SWITCHED)
def test_the_rest_of_the_page_waits_for_its_switch(admin, keep, tab, switch, field):
    settings.set_many({switch: "0"})
    tab = tab.strip()
    off = admin.get(f"/admin/settings?tab={tab}").text
    assert _hidden_wrapper(off, field, f"{switch}=1")
    # the fields are still sent with the form, so saving keeps what they hold
    assert f'name="{field}"' in off and f'name="{switch}"' in off
    settings.set_many({switch: "1"})
    assert not _hidden_wrapper(admin.get(f"/admin/settings?tab={tab}").text, field, f"{switch}=1")


def test_the_analytics_site_id_waits_for_a_provider(admin, keep):
    settings.set_many({"analytics_provider": ""})
    assert _hidden_wrapper(admin.get("/admin/settings?tab=analytics").text, "analytics_id", "analytics_provider!=")
    settings.set_many({"analytics_provider": "plausible"})
    assert not _hidden_wrapper(admin.get("/admin/settings?tab=analytics").text, "analytics_id", "analytics_provider!=")


def test_a_switch_counts_as_its_value_only_while_on(admin):
    js = admin.get("/app.js").text
    assert "field.type === 'checkbox' && !field.checked ? '' : field.value" in js


def test_only_a_switch_with_the_value_1_is_ever_a_data_shown_for_target(admin):
    """Every rule on a settings page points at a field that exists, and one
    that points at a checkbox asks for "1" - what a switch is while on."""
    for tab in ("messages", "members", "sharing", "analytics", "newsletter", "email", "language",
                "blog", "posts", "header"):
        page = admin.get(f"/admin/settings?tab={tab}").text
        for rule in re.findall(r'data-shown-for="([^"]+)"', page):
            for one in rule.split(";"):
                name, _, value = one.replace("!=", "=").partition("=")
                inputs = re.findall(rf'<input[^>]*name="{name}"[^>]*>', page)
                if inputs and all('type="checkbox"' in i for i in inputs):
                    assert value == "1" and "!=" not in one, (tab, one)
