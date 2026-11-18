# Soloblog's brand

## The words

Soloblog is described in these words, everywhere - GitHub, the README,
the image, the app stores, the website, the guide. Use the length that
fits; don't reword them.

| Length | Words | Where |
|---|---|---|
| **Tagline** | Your own blog and website. Yours to keep. | The README's heading, the website's tagline, share images and covers |
| **One line** | A free, open source blog and website for one person, run on your own server or hosting account. | The repository and organisation on GitHub, the Docker image, app-store taglines and short descriptions, the FAQ, the website's description |
| **Paragraph** | Soloblog is a free, open source blog and website for one person, run on your own server or hosting account. Write in a calm editor, pick from 35 colour palettes, and build pages from sections. Your posts are plain text files you own. | Under the README's heading, app-store long descriptions, the website's homepage and announcements |

A longer text starts with the paragraph and goes on from there. A store
with a short limit takes the tagline. `tests/test_brand.py` checks the
places above still say them.

## The logo

The mark is an **S with a dot** - one person, their own site. The name is
written **s●loblog**, the first o a filled dot.

| File | Use |
|---|---|
| `soloblog-icon.svg`, `soloblog-icon-512.png` (also 180, 32) | App icon and favicon: the S and dot on a dark rounded square |
| `soloblog-mark.svg` / `-dark.svg` | The S and dot alone, for light / dark backgrounds |
| `soloblog-wordmark.svg` / `-dark.svg` | The name, for light / dark backgrounds |
| `soloblog-social.png` | 1280 x 640 share image (GitHub's social preview, link previews) |

**Colours:** the dot is `#605DFF`, the same on light and dark. Text is
`#16161A` on light backgrounds and `#ECEAE6` on dark ones.

**Font:** [Sora](https://fonts.google.com/specimen/Sora) SemiBold (SIL Open
Font License), turned into outlines, so the files don't need the font.

Please don't recolour, stretch or redraw the mark. Use it freely to write
about Soloblog or link to it. The MIT licence covers the code, not the name
and logo, so please don't use them in a way that suggests something is
the Soloblog project's own when it isn't.

`python tools/brand.py` makes all of these again.
