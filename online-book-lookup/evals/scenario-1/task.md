# Exact ISBN lookup

A user asks:

`Look up ISBN 9780140328721 online and tell me the title, author, first publication year, publisher, and source URL.`

Goal:
- use the Open Library ISBN API through the bundled helper
- return an exact sourced result for the ISBN
- include title, author, first publication year or publication date, publisher when available, and source URL

Constraints:
- do not use shopping, review, or ebook download pages
- do not infer fields that Open Library did not return
- if the API returns no match, report the no-match result honestly
