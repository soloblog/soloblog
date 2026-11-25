# Deploy and Host Soloblog on Sealos

Soloblog is a free, open source blog and website for one person, run on your own server or hosting account. Write in a calm editor, pick from 35 colour palettes, and build pages from sections. Your posts are plain text files you own. This template runs one Soloblog container on Sealos with a persistent volume for everything it keeps, and an HTTPS address.

![Soloblog Screenshot](https://raw.githubusercontent.com/labring-actions/templates/kb-0.9/template/soloblog/website-screenshot.webp)

## About Hosting Soloblog

Soloblog keeps its posts as markdown files, its SQLite database, images and settings in one folder, mounted here at `/data`. There's no database server to run. It runs as a single copy, so the template keeps one replica.

## Common Use Cases

- **A personal blog**: write in a calm editor, with 35 colour palettes to choose from.
- **A personal website**: build a homepage, a portfolio or a book's landing page out of sections.
- **A newsletter**: readers subscribe by email, or follow from Mastodon.
- **Members-only posts**: free or paid, with sign-in by email.

## After Deploying

Open the app's address. First-time setup asks for a setup token: open the app's details in Sealos, then its logs, and copy it from the lines marked `[setup]`. Then choose your password and keep the recovery key it gives you.

## Dependencies for Soloblog Hosting

- **Soloblog**: `ghcr.io/soloblog/soloblog`
- **Persistent storage**: `/data` for posts, images, the database and settings
- **Network entry**: Service, HTTPS Ingress and the Sealos App resource

### Deployment Dependencies

- [Soloblog user guide](https://github.com/soloblog/soloblog/blob/master/docs/guide/README.md)
- [Soloblog hosting guide](https://github.com/soloblog/soloblog/blob/master/docs/DEPLOYMENT.md)
- [Soloblog source code](https://github.com/soloblog/soloblog)
- [Sealos Documentation](https://sealos.io/docs)
