-- The newsletter's sign-up box under each post is off until it's chosen.
-- A site that already runs a newsletter and never chose what its posts
-- show keeps the box it had: its choice is written out, as it was then.
INSERT INTO settings (key, value)
SELECT 'post_shows', 'breadcrumbs,progress,byline,tags,listen,reactions,share,support,series,related,author,newsletter,sides'
WHERE EXISTS (SELECT 1 FROM settings WHERE key = 'newsletter_mode' AND value != '')
  AND NOT EXISTS (SELECT 1 FROM settings WHERE key = 'post_shows' AND value != '')
ON CONFLICT(key) DO UPDATE SET value = excluded.value;
