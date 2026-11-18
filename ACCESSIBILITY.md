# Accessibility

Soloblog should work for everyone who writes with it and everyone who
reads a site made with it.

## What Soloblog aims for

[WCAG 2.2](https://www.w3.org/TR/WCAG22/) level AA, in the admin and on
every site it publishes:

- Text readable against its background in all 35 colour palettes, and in
  any palette you make yourself.
- Everything works with a keyboard alone, and every field and button has
  a label.
- Buttons and links big enough to tap, larger still on a touch screen.
- Animations stop when your device asks for less motion, or when the
  site's owner switches them off. Nothing moves on its own.
- Visitors read a site in any of 23 languages, including ones written
  right to left.

How each of these is checked is in
[STANDARDS.md](docs/STANDARDS.md#accessibility).

## Where it's tested

- Current versions of Chrome, Firefox, Safari and Edge.
- A computer and a phone, on screens down to 320 pixels wide.
- A keyboard alone, and with reduced motion switched on.

## What isn't there yet

- **Screen readers haven't been tested by hand.** Pages are built from
  real headings, labels and buttons, and an automatic checker (axe)
  looks at every page, but nobody has yet used Soloblog with NVDA, JAWS,
  VoiceOver or TalkBack. Reports from people who do are especially
  welcome.
- **The admin is in English only.** Visitors' sites are translated.

## Report a barrier

If something in Soloblog is hard or impossible to use, it's a bug.
[Open a bug report](https://github.com/soloblog/soloblog/issues/new/choose),
or select **Report a problem** at the bottom of any admin page. Say what
you were trying to do, what got in the way, and what you use - a browser,
a screen reader, a keyboard, zoom. Reports are read every week and
answered, as [SUPPORT.md](SUPPORT.md) says.
