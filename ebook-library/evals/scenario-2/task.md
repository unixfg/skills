# Fall back to browsing when a metadata search fails

Use the bundled sample library at `./sample-library`.

A user says they want the sea adventure novel in the fixture library, but a first metadata lookup using the phrase `ocean depths` returns no matches.

Goal:
- do not guess from the failed search alone
- fall back to browsing the fixture library titles
- identify the most likely matching book
- report the `book_id`, exact title, and author
- briefly explain the fallback workflow you used

Constraints:
- start with metadata lookup
- if the first lookup returns `[]`, inspect available titles before choosing an answer
- do not use broad global content search for this task

Expected outcome:
- the correct book is `Twenty Thousand Leagues under the Sea` by Jules Verne
