"""The icons, as inline SVG, and the lists made of them."""
from fasthtml.common import *
from soloblog import editor_icons

GEAR_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>'
)
HAMBURGER_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor">'
    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
    'd="M4 6h16M4 12h16M4 18h16" /></svg>'
)
SEARCH_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>'
)
# Heroicons "swatch" outline - reads as "pick a look" for a multi-theme
# picker better than a sun/moon toggle would, since that implies just
# light/dark and this site offers all 35.
# the header's sidebar button - drawn like the gear and palette beside it
SIDEBAR_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" '
    'stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" '
    'd="M3.75 6A2.25 2.25 0 0 1 6 3.75h12A2.25 2.25 0 0 1 20.25 6v12A2.25 2.25 0 0 1 18 20.25H6A2.25 2.25 0 0 1 '
    '3.75 18V6Z M9 3.75v16.5" /></svg>'
)

PALETTE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M4.098 19.902a3.75 3.75 0 005.304 0l6.401-6.402M6.75 21A3.75 3.75 0 013 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125v4.072M6.75 21a3.75 3.75 0 003.75-3.75V8.197M6.75 21h13.125c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125h-4.072M10.5 8.197l2.88-2.88c.438-.439 1.15-.439 1.59 0l3.712 3.712c.44.44.44 1.152 0 1.59l-2.879 2.88M6.75 17.25h.008v.008H6.75v-.008z" /></svg>'
)

# a pinned page's own submenu trigger (PinnedNavItem) used to be a real
# <summary> - browsers (and daisyUI's own .menu CSS) draw that one's
# disclosure marker for free. A real <button> (needed for popovertarget)
# doesn't get one, so this replaces it explicitly.
CHEVRON_DOWN_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" /></svg>'
)
# Heroicons outline "arrow-top-right-on-square", next to a menu item
# that leaves the site
EXTERNAL_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 opacity-60" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 '
    '2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" /></svg>'
)
# the same, at a row action's size and weight (EDIT_SVG, EYE_SVG): View -
# the post on your site; the eye is Preview's
VIEW_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 '
    '2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" /></svg>'
)
# Heroicons outline "plus", "arrow-right" and "photo"
PLUS_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>'
)
ARROW_RIGHT_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>'
)
# a template - Heroicons' rectangle-group
TEMPLATE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 7.125C2.25 6.504 2.754 6 3.375 6h6c.621 0 1.125.504 '
    '1.125 1.125v3.75c0 .621-.504 1.125-1.125 1.125h-6a1.125 1.125 0 0 1-1.125-1.125v-3.75ZM14.25 8.625c0-.621.504-1.125 '
    '1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v8.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 '
    '1-1.125-1.125v-8.25ZM3.75 16.125c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v2.25c0 '
    '.621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 1-1.125-1.125v-2.25Z" /></svg>'
)

PHOTO_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 '
    '5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 '
    '0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 '
    '0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" /></svg>'
)

CHEVRON_UP_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 15.75 7.5-7.5 7.5 7.5" /></svg>'
)
# Heroicons outline "arrows-up-down" - same h-3.5 w-3.5 stroke-2
# treatment as EDIT_SVG/TRASH_SVG since it sits in the same join-item
# button row as those.
MOVE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M3 7.5L7.5 3m0 0L12 7.5M7.5 3v13.5m13.5 0L16.5 21m0 0L12 16.5m4.5 4.5V7.5" /></svg>'
)
# Focus mode's own icon (editor_icons), at a row action's size - "Edit in
# Focus mode", beside Edit
FOCUS_SVG = NotStr(editor_icons.svg("maximize-2").replace('class="editor-icon"', 'class="h-3.5 w-3.5"')
                   .replace('width="18" height="18" ', ''))
EDIT_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>'
)
# the admin menu's own Posts and pages icon (ui.admin), at a row action's size
POSTS_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>'
)
# Delete/Save/Cancel/Restore - same h-3.5 w-3.5 stroke-2 outline
# treatment as EDIT_SVG, since these all sit in the same small button
# rows as Edit and need to read as one consistent icon family, not a
# mix of sizes/weights. Heroicons outline paths, fetched verbatim
# (same reasoning as the brand icons elsewhere in this file - exact
# path data, not reconstructed from memory).
TRASH_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>'
)
RSS_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M12.75 19.5v-.75a7.5 7.5 0 0 0-7.5-7.5H4.5m0-6.75h.75'
    'c7.87 0 14.25 6.38 14.25 14.25v.75M6 18.75a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" /></svg>'
)
CHECK_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>'
)
X_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>'
)
COPY_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 '
    '0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-'
    '.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 '
    '2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" /></svg>'
)
RESTORE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" /></svg>'
)
ROTATE_LEFT_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M3 12a9 9 0 1 0 3-6.7L3 8m0-5v5h5" /></svg>'
)
ROTATE_RIGHT_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M21 12a9 9 0 1 1-3-6.7L21 8m0-5v5h-5" /></svg>'
)
CROP_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M6 2v14a2 2 0 0 0 2 2h14M18 22V8a2 2 0 0 0-2-2H2" /></svg>'
)
DUPLICATE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 0 1-1.125-1.125V7.875c0-.621.504-1.125 '
    '1.125-1.125H6.75a9.06 9.06 0 0 1 1.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161'
    '-7.5-8.876a9.06 9.06 0 0 0-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 0 1-'
    '1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125-1.125v-1.5a3.375 '
    '3.375 0 0 0-3.375-3.375H9.75" /></svg>'
)
DOWNLOAD_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>'
)
UPLOAD_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" /></svg>'
)
HOME_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 '
    '1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 '
    '1.125-.504 1.125-1.125V9.75M8.25 21h8.25" /></svg>'
)
SEND_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" /></svg>'
)
SYNC_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 '
    '13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>'
)
KEY_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25'
    'v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z" /></svg>'
)
LOGIN_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 '
    '2.25 0 0 1-2.25-2.25V15M12 9l3 3m0 0-3 3m3-3H2.25" /></svg>'
)
# SEARCH_SVG at the button-icon size (h-3.5) the rest of this family uses
SEARCH_BTN_SVG = NotStr(str(SEARCH_SVG).replace("h-4 w-4", "h-3.5 w-3.5"))
# same family as Edit/Delete/Save/Cancel/Restore above - the editor
# page's "View" link (the live post, opened in a new context) gets the
# same icon-button treatment those already have instead of being a
# plain text link on its own.
EYE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />'
    '<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>'
)
# a plain speech-bubble, not RESTORE_SVG's uturn-arrow - the admin
# comments list needed its own "Reply" icon distinct from Restore's,
# even though the two never appear on the same tab at once (Reply only
# shows on Approved rows, Restore only on Trash rows)
REPLY_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M2.25 12.76c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.184a1.14 1.14 0 01.778-.332 '
    '48.294 48.294 0 005.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 '
    '48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" /></svg>'
)
# proper Heroicons outline/solid heart paths (MIT, Tailwind Labs) - the
# previous version reused one fill-optimized path for both states,
# which is why the outline heart looked distorted when stroked instead
# of filled. these two are each designed for their own render mode.
HEART_OUTLINE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="1.5">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" /></svg>'
)
HEART_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z" /></svg>'
)

# real brand marks (Simple Icons, MIT) for the footer's icon-mode social
# row - fetched verbatim rather than reconstructed from memory, since a
# slightly-wrong brand logo reads as broken in a way a slightly-wrong
# generic UI icon doesn't. Website/custom links aren't a brand, so
# those two use plain Heroicons instead (globe / generic link).
TWITTER_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M14.234 10.162 22.977 0h-2.072l-7.591 8.824L7.251 0H.258l9.168 13.343L.258 24H2.33l8.016-9.318L16.749 24h6.993zm-2.837 3.299-.929-1.329L3.076 1.56h3.182l5.965 8.532.929 1.329 7.754 11.09h-3.182z" /></svg>'
)
GITHUB_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" /></svg>'
)
FACEBOOK_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 1.888-.287 1.779h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z" /></svg>'
)
MASTODON_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M23.268 5.313c-.35-2.578-2.617-4.61-5.304-5.004C17.51.242 15.792 0 11.813 0h-.03c-3.98 0-4.835.242-5.288.309C3.882.692 1.496 2.518.917 5.127.64 6.412.61 7.837.661 9.143c.074 1.874.088 3.745.26 5.611.118 1.24.325 2.47.62 3.68.55 2.237 2.777 4.098 4.96 4.857 2.336.792 4.849.923 7.256.38.265-.061.527-.132.786-.213.585-.184 1.27-.39 1.774-.753a.057.057 0 00.023-.043v-1.809a.052.052 0 00-.02-.041.053.053 0 00-.046-.01 20.282 20.282 0 01-4.709.545c-2.73 0-3.463-1.284-3.674-1.818a5.593 5.593 0 01-.319-1.433.053.053 0 01.066-.054c1.517.363 3.072.546 4.632.546.376 0 .75 0 1.125-.01 1.57-.044 3.224-.124 4.768-.422.038-.008.077-.015.11-.024 2.435-.464 4.753-1.92 4.989-5.604.008-.145.03-1.52.03-1.67.002-.512.167-3.63-.024-5.545zm-3.748 9.195h-2.561V8.29c0-1.309-.55-1.976-1.67-1.976-1.23 0-1.846.79-1.846 2.35v3.403h-2.546V8.663c0-1.56-.617-2.35-1.848-2.35-1.112 0-1.668.668-1.67 1.977v6.218H4.822V8.102c0-1.31.337-2.35 1.011-3.12.696-.77 1.608-1.164 2.74-1.164 1.311 0 2.302.5 2.962 1.498l.638 1.06.638-1.06c.66-.999 1.65-1.498 2.96-1.498 1.13 0 2.043.395 2.74 1.164.675.77 1.012 1.81 1.012 3.12z" /></svg>'
)
INSTAGRAM_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1118.39 4.144a1.44 1.44 0 01-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 114.008 3.9921A3.9996 3.9996 0 018 12.0077" /></svg>'
)
YOUTUBE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" /></svg>'
)
LINKEDIN_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" /></svg>'
)
BLUESKY_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M5.202 2.857C7.954 4.922 10.913 9.11 12 11.358c1.087-2.247 4.046-6.436 6.798-8.501C20.783 1.366 24 .213 24 3.883c0 .732-.42 6.156-.667 7.037-.856 3.061-3.978 3.842-6.755 3.37 4.854.826 6.089 3.562 3.422 6.299-5.065 5.196-7.28-1.304-7.847-2.97-.104-.305-.152-.448-.153-.327 0-.121-.05.022-.153.327-.568 1.666-2.782 8.166-7.847 2.97-2.667-2.737-1.432-5.473 3.422-6.3-2.777.473-5.899-.308-6.755-3.369C.42 10.04 0 4.615 0 3.883c0-3.67 3.217-2.517 5.202-1.026" /></svg>'
)
THREADS_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M17.69 11.13c-.1-.05-.2-.1-.31-.14-.18-3.3-1.99-5.2-5.02-5.22h-.04c-1.82 0-3.33.77-4.26 2.18l1.67 1.15'
    'c.7-1.05 1.79-1.28 2.6-1.28h.03c1 .01 1.76.3 2.24.87.35.41.59.98.7 1.7-.88-.15-1.83-.2-2.85-.14-2.86.17-4.7 1.83'
    '-4.58 4.15.06 1.18.65 2.19 1.65 2.85.85.56 1.94.83 3.08.77 1.5-.08 2.68-.66 3.5-1.7.62-.8 1.02-1.82 1.2-3.12.72.43'
    ' 1.25 1 1.54 1.69.5 1.17.53 3.09-1.04 4.66-1.38 1.38-3.03 1.97-5.52 1.99-2.76-.02-4.85-.91-6.21-2.64C4.5 16.8 3.84'
    ' 14.62 3.81 12c.03-2.62.69-4.8 1.97-6.44 1.36-1.73 3.45-2.62 6.21-2.64 2.78.02 4.9.91 6.31 2.66.69.85 1.21 1.93 1.56'
    ' 3.18l1.96-.52c-.42-1.55-1.08-2.88-1.99-4C18.02 1.99 15.4.87 12.01.84h-.01C8.62.87 6.02 2 4.27 4.2 2.72 6.17 1.91'
    ' 8.9 1.88 12v.01c.03 3.1.84 5.83 2.39 7.8C6.02 22 8.62 23.13 12 23.16h.01c3-.02 5.12-.81 6.86-2.55 2.28-2.28 2.21'
    '-5.13 1.46-6.88-.54-1.26-1.56-2.28-2.95-2.94Zm-5.18 4.86c-1.25.07-2.55-.49-2.62-1.69-.05-.89.63-1.88 2.68-2 .23-.01'
    '.46-.02.69-.02.74 0 1.44.07 2.07.21-.24 2.95-1.62 3.43-2.82 3.5Z"/></svg>'
)
# not brand marks - Website/custom "extra" links aren't any one
# platform, so these are plain Heroicons (solid) instead: a globe for
# "Website", a generic link glyph for anything in extra_social_links.
GLOBE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M21.721 12.752a9.711 9.711 0 00-.945-5.003 12.754 12.754 0 01-4.339 2.708 18.991 18.991 0 01-.214 4.772 17.165 17.165 0 005.498-2.477zM14.634 15.55a17.324 17.324 0 00.332-4.647c-.952.227-1.945.347-2.966.347-1.021 0-2.014-.12-2.966-.347a17.515 17.515 0 00.332 4.647 17.385 17.385 0 005.268 0zM9.772 17.119a18.963 18.963 0 004.456 0A17.182 17.182 0 0112 21.724a17.18 17.18 0 01-2.228-4.605zM7.777 15.23a18.87 18.87 0 01-.214-4.774 12.753 12.753 0 01-4.34-2.708 9.711 9.711 0 00-.944 5.004 17.165 17.165 0 005.498 2.477zM21.356 14.752a9.765 9.765 0 01-7.478 6.817 18.64 18.64 0 001.988-4.718 18.627 18.627 0 005.49-2.098zM2.644 14.752c1.682.971 3.53 1.688 5.49 2.099a18.64 18.64 0 001.988 4.718 9.765 9.765 0 01-7.478-6.816zM13.878 2.43a9.755 9.755 0 016.116 3.986 11.267 11.267 0 01-3.746 2.504 18.63 18.63 0 00-2.37-6.49zM12 2.276a17.152 17.152 0 012.805 7.121c-.897.23-1.837.353-2.805.353-.968 0-1.908-.122-2.805-.353A17.151 17.151 0 0112 2.276zM10.122 2.43a18.629 18.629 0 00-2.37 6.49 11.266 11.266 0 01-3.746-2.504 9.754 9.754 0 016.116-3.985z" /></svg>'
)
LINK_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path fill-rule="evenodd" clip-rule="evenodd" '
    'd="M19.902 4.098a3.75 3.75 0 00-5.304 0l-4.5 4.5a3.75 3.75 0 001.035 6.037.75.75 0 01-.646 1.353 5.25 5.25 0 01-1.449-8.45l4.5-4.5a5.25 5.25 0 117.424 7.424l-1.757 1.757a.75.75 0 11-1.06-1.06l1.757-1.757a3.75 3.75 0 000-5.304zm-7.389 4.267a.75.75 0 011-.353 5.25 5.25 0 011.449 8.45l-4.5 4.5a5.25 5.25 0 11-7.424-7.424l1.757-1.757a.75.75 0 111.06 1.06l-1.757 1.757a3.75 3.75 0 105.304 5.304l4.5-4.5a3.75 3.75 0 00-1.035-6.037.75.75 0 01-.354-1z" /></svg>'
)
MAIL_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M1.5 8.67v8.58a3 3 0 003 3h15a3 3 0 003-3V8.67l-8.928 5.493a3 3 0 01-3.144 0L1.5 8.67z" />'
    '<path d="M22.5 6.908V6.75a3 3 0 00-3-3h-15a3 3 0 00-3 3v.158l9.714 5.978a1.5 1.5 0 001.572 0L22.5 6.908z" /></svg>'
)
HEART_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z" /></svg>'
)
STAR_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path fill-rule="evenodd" clip-rule="evenodd" '
    'd="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.007 5.404.433c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.433 2.082-5.006z" /></svg>'
)
BOOKMARK_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">'
    '<path fill-rule="evenodd" clip-rule="evenodd" '
    'd="M6.32 2.577a49.255 49.255 0 0111.36 0c1.497.174 2.57 1.46 2.57 2.93V21a.75.75 0 01-1.085.67L12 18.089l-7.165 3.583A.75.75 0 013.75 21V5.507c0-1.47 1.073-2.756 2.57-2.93z" /></svg>'
)
# the curated set an admin can pick from for a custom (extra_social_links)
# link, one level up from the plain LINK_SVG default every one of them
# used to be stuck with regardless of what it actually pointed to.
# Deliberately small and generic - these aren't brand marks like
# SOCIAL_PLATFORMS' own icons (a free-text link isn't one known
# platform), same reasoning GLOBE_SVG/LINK_SVG were built on originally.
EXTRA_LINK_ICONS = {
    "link": LINK_SVG, "globe": GLOBE_SVG, "mail": MAIL_SVG,
    "heart": HEART_SVG, "star": STAR_SVG, "bookmark": BOOKMARK_SVG,
}

# the single source of truth for the 9 fixed social platforms - key
# (matches the settings.py "social_{key}" field and a social_order
# entry), display label, brand icon, and whether it has a real "share
# this URL" path (still no 3rd-party redirector - Mastodon's own is a
# prompt for the *visitor's* instance, then that instance's own
# documented /share?text= endpoint, handled specially in ShareButtons
# since it needs a click-time prompt rather than a plain href).
# GitHub/Instagram/YouTube/Website don't have "share a blog post"
# semantics at all, share-URL or otherwise, so those stay real social
# links only. ShareButtons filters to just the share-capable ones.
SOCIAL_PLATFORMS = [
    ("twitter", "X/Twitter", TWITTER_SVG, True),
    ("facebook", "Facebook", FACEBOOK_SVG, True),
    ("mastodon", "Mastodon", MASTODON_SVG, True),
    ("bluesky", "Bluesky", BLUESKY_SVG, True),
    ("threads", "Threads", THREADS_SVG, True),
    ("linkedin", "LinkedIn", LINKEDIN_SVG, True),
    ("github", "GitHub", GITHUB_SVG, False),
    ("instagram", "Instagram", INSTAGRAM_SVG, False),
    ("youtube", "YouTube", YOUTUBE_SVG, False),
    ("website", "Website", GLOBE_SVG, False),
]


def ordered_social_platforms(s):
    """SOCIAL_PLATFORMS, reordered per the admin's saved social_order -
    shared by SocialLinks and ShareButtons so the two can never drift
    apart (reordering one always reorders the other, since both read
    from this same function). Any key in social_order that isn't a
    real platform is ignored; any real platform missing from
    social_order (a future platform added after an install's order
    string was already saved) is appended at the end rather than
    silently never appearing."""
    by_key = {pl[0]: pl for pl in SOCIAL_PLATFORMS}
    order = [k.strip() for k in (s.get("social_order") or "").split(",") if k.strip()]
    seen = set()
    result = []
    for key in order:
        if key in by_key and key not in seen:
            result.append(by_key[key])
            seen.add(key)
    for pl in SOCIAL_PLATFORMS:
        if pl[0] not in seen:
            result.append(pl)
    return result


DOTS_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" '
    'stroke-width="2" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" '
    'd="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 '
    '12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"/></svg>')

SPEAKER_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" '
    'stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" '
    'd="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 '
    '1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 '
    '12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" /></svg>'
)
PAUSE_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" '
    'stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" '
    'd="M15.75 5.25v13.5m-7.5-13.5v13.5" /></svg>'
)
# Heroicons outline "eye-slash": the eye struck through - left out of a menu
EYE_OFF_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" '
    'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 '
    '6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 '
    '3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" /></svg>'
)
