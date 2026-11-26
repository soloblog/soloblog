-- When a post first went out. A post's date becomes the day it's first
-- published, not the day its draft was started; this keeps that day when
-- it's unpublished and published again. A post already out keeps its date.
ALTER TABLE posts ADD COLUMN first_published_at TEXT NOT NULL DEFAULT '';
UPDATE posts SET first_published_at = created_at WHERE published = 1;
