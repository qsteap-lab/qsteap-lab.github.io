# QSTEAP Lab website

Source for **https://qsteap-lab.github.io**, the website of the QSTEAP Lab
(Quantum Science and Technology with Electrons, Atoms and Photons),
University of Wisconsin–Madison. Built with [Quarto](https://quarto.org).

## Editing (the easy way)

1. Install [Quarto](https://quarto.org/docs/get-started/) once, and make sure Python 3 is installed.
2. Double-click **`start-editor.command`** (Mac) or **`start-editor.bat`** (Windows).
   The first launch takes a minute to set up, and then the editor opens in your browser at http://localhost:5055.
   *(Mac: if it says the file can't be opened, right-click it → Open.)*
3. Edit things in the tabs (General, Research, Team, Publications, News, Page text), then press **Save**.
4. **Preview site** builds the site and opens it in your browser.
5. **Preview & Publish → Publish** pushes your changes to GitHub. The live site rebuilds by itself in about a minute.

## Where the content lives

| What | File |
|---|---|
| Lab name, email, address, tagline | `_lab.yml` |
| Team members | `data/team.yml` |
| Publications | `data/publications.yml` |
| News | `data/news.yml` |
| Research directions | `data/research.yml` |
| Free page text | `index.qmd`, `research.qmd`, `join.qmd`, `contact.qmd` |
| Images | `images/` (uploads go to `images/uploads/`) |
| Look & feel | `assets/styles.css`, hero animation in `assets/hero.html` |

## Command line

```bash
quarto preview      # live preview with auto-reload
quarto render       # build into _site/
```

Deployment is handled by `.github/workflows/publish.yml`. Every push to `main` builds the site and publishes it to GitHub Pages.
