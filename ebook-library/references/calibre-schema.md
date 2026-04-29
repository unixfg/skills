# Calibre Database Schema Reference

## metadata.db

### books
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| title | TEXT | Book title |
| sort | TEXT | Sort key |
| timestamp | TIMESTAMP | Date added/imported into Calibre |
| pubdate | TIMESTAMP | Publication date |
| path | TEXT | Relative path from library root |
| author_sort | TEXT | Author name for sorting |
| has_cover | BOOL | Cover image exists |
| uuid | TEXT | Unique identifier |
| last_modified | TIMESTAMP | Last metadata modification date |

### authors
| Column | Type |
|--------|------|
| id | INTEGER |
| name | TEXT |

### books_authors_link
| Column | Type |
|--------|------|
| book | INTEGER |
| author | INTEGER |

### data (file formats)
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| book | INTEGER | FK to books |
| format | TEXT | EPUB, PDF, AZW3, etc. |
| name | TEXT | Filename without extension |

### Other tables
- `series`, `books_series_link` - Series info
- `tags`, `books_tags_link` - Tags/categories
- `publishers`, `books_publishers_link` - Publishers
- `comments` - Book descriptions
- `identifiers` - ISBN, etc.

## full-text-search.db

### books_text (content table)
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| book | INTEGER | FK to metadata.db books |
| format | TEXT | Source format |
| searchable_text | TEXT | Full extracted text |

### books_fts (FTS5 virtual table)
Uses Calibre's custom tokenizer - not usable outside Calibre.
Query `books_text` directly with LIKE for content search.

## Path Resolution

Full path to a book file:
```
{library_root}/{books.path}/{data.name}.{data.format.lower()}
```

Example:
```
/path/to/Calibre Library/Ted Dunning/Practical Machine Learning (915)/Practical Machine Learning - Ted Dunning.pdf
```
