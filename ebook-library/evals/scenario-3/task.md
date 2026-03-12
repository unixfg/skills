# Find an excerpt from a known book in the sample Calibre library

Use the bundled sample library at `./sample-library`.

Goal:
- locate `Twenty Thousand Leagues under the Sea` by Jules Verne
- search within that specific book for a passage mentioning `Leyden`
- return:
  - the `book_id`
  - the book title
  - a short excerpt that includes the term `Leyden`
  - a brief note on how you found it

Constraints:
- prefer narrowing to the correct `book_id` first, then search within that book
- do not do a broad global content search unless you first fail to identify the book
- use the fixture data, not prior knowledge
