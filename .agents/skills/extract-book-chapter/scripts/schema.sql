PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS book_books (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    source_path   TEXT    NOT NULL UNIQUE,
    source_sha256 TEXT    NOT NULL,
    page_count    INTEGER NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS book_chapters (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id    INTEGER NOT NULL REFERENCES book_books(id),
    number     TEXT,
    slug       TEXT    NOT NULL,
    title      TEXT    NOT NULL,
    start_page INTEGER NOT NULL,
    end_page   INTEGER NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'extracted'
               CHECK (status IN ('extracted', 'translated', 'reviewed', 'rendered')),
    UNIQUE (book_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_book_chapters_book ON book_chapters (book_id, start_page);

CREATE TABLE IF NOT EXISTS book_pages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id   INTEGER NOT NULL REFERENCES book_chapters(id),
    pdf_page     INTEGER NOT NULL,
    printed_page TEXT,
    UNIQUE (chapter_id, pdf_page)
);

CREATE TABLE IF NOT EXISTS book_figures (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id   INTEGER NOT NULL REFERENCES book_pages(id),
    seq       INTEGER NOT NULL,
    file_path TEXT    NOT NULL UNIQUE,
    label     TEXT,
    kind      TEXT    NOT NULL DEFAULT 'raster' CHECK (kind IN ('raster', 'vector')),
    bbox_json TEXT,
    col       INTEGER NOT NULL DEFAULT 0 CHECK (col IN (0, 1, 2)),
    y0        REAL    NOT NULL,
    width_pt  REAL    NOT NULL,
    height_pt REAL    NOT NULL,
    UNIQUE (page_id, seq)
);

CREATE TABLE IF NOT EXISTS book_blocks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id       INTEGER NOT NULL REFERENCES book_pages(id),
    seq           INTEGER NOT NULL,
    col           INTEGER NOT NULL DEFAULT 0 CHECK (col IN (0, 1, 2)),
    y0            REAL    NOT NULL,
    type          TEXT    NOT NULL
                  CHECK (type IN ('chapter_title', 'heading', 'paragraph', 'list_item',
                                  'callout', 'caption', 'footnote', 'footer')),
    heading_level INTEGER,
    list_marker   TEXT,
    figure_id     INTEGER REFERENCES book_figures(id),
    figure_role   TEXT CHECK (figure_role IN ('title', 'annotation', 'caption')),
    translatable  INTEGER NOT NULL DEFAULT 1,
    source_html   TEXT    NOT NULL,
    style_json    TEXT,
    bbox_json     TEXT,
    UNIQUE (page_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_book_blocks_type ON book_blocks (type);

CREATE TABLE IF NOT EXISTS book_glossary (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    term_en  TEXT NOT NULL,
    term     TEXT NOT NULL,
    abbr_en  TEXT,
    abbr     TEXT,
    UNIQUE (language, term_en)
);

CREATE TABLE IF NOT EXISTS book_translations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id   INTEGER NOT NULL REFERENCES book_blocks(id),
    language   TEXT    NOT NULL,
    text_html  TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'machine' CHECK (status IN ('machine', 'reviewed', 'rejected')),
    model      TEXT,
    updated_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (block_id, language)
);
CREATE INDEX IF NOT EXISTS idx_book_translations_status ON book_translations (status);
