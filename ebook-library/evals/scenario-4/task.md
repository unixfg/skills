# Identify a book from a topic term using global content search

Use the bundled sample library at `./sample-library`.

A user does not remember the title, but wants the book in the fixture library that prominently discusses `bourgeois`.

Goal:
- use the fixture data to identify which book best matches that topic
- report the `book_id`, title, and author
- include a short snippet or explanation showing why it matches
- briefly explain how you found the answer

Constraints:
- the title is unknown up front, so a global content search is appropriate
- do not rely on prior knowledge of the books
- use the actual search results from the fixture library

Expected outcome:
- the correct book is `The Communist Manifesto` by Karl Marx and Friedrich Engels
