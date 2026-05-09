# VeritasReason Documentation

This documentation is built with [MkDocs](https://www.mkdocs.org/) - a fast, simple static site generator for project documentation.

## Features

- **Great themes available** - Using Material theme with beautiful design
- **Easy to customize** - Custom CSS and theme configuration
- **Preview as you work** - Built-in dev server with auto-reload
- **Host anywhere** - Static HTML that works on GitHub Pages, Netlify, etc.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements-docs.txt
```

### 2. Preview Locally

```bash
mkdocs serve
```

Then open `http://127.0.0.1:8000` in your browser.

### 3. Build for Production

```bash
mkdocs build
```

This creates a `site/` directory with static HTML files ready to deploy.

## Project Structure

```
veritasreason/
├── mkdocs.yml           # MkDocs configuration
├── requirements-docs.txt # Python dependencies
├── docs/                # Documentation source files
│   ├── index.md         # Homepage
│   ├── *.md             # Documentation pages
│   ├── css/
│   │   └── custom.css   # Custom styling
│   └── assets/
│       └── img/
│           └── VeritasReason Logo.png
└── site/                # Generated site (created by mkdocs build)
```

## Configuration

Main configuration is in `mkdocs.yml`:
- Site metadata
- Theme settings (Material theme)
- Navigation structure
- Markdown extensions
- Plugins

## Adding New Pages

1. Create a new `.md` file in `docs/`
2. Add it to `nav:` section in `mkdocs.yml`
3. Run `mkdocs serve` to preview

## Customization

### Theme

Edit `mkdocs.yml` under `theme:` section to customize:
- Color scheme
- Logo
- Features enabled
- Icons

### Styling

Edit `docs/css/custom.css` for custom styles.

## Deployment

### GitHub Pages

```bash
mkdocs gh-deploy
```

### Netlify/Vercel

1. Build: `mkdocs build`
2. Deploy the `site/` directory

### Manual

1. Run `mkdocs build`
2. Upload `site/` folder contents to your web server

## Development Workflow

1. Edit markdown files in `docs/`
2. Run `mkdocs serve` to preview
3. Changes auto-reload in browser
4. When ready, build with `mkdocs build`

## Benefits

- ✅ Python-based (fits with your Python project)
- ✅ Beautiful Material theme
- ✅ Fast and lightweight
- ✅ Easy to customize
- ✅ Great search functionality
- ✅ Mobile responsive
