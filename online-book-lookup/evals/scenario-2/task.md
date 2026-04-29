# Title and author candidate lookup

A user asks:

`Find online book information for The Left Hand of Darkness by Ursula K. Le Guin. Show the best few Open Library matches.`

Goal:
- use title and author fields, not a single vague query, when calling the helper
- return multiple ranked candidates when Open Library provides them
- include author, first publish year, ISBNs or edition keys when available, and source URLs

Constraints:
- do not collapse multiple candidates into one unsupported certainty if the returned records differ
- do not use shopping links or review summaries
- keep the answer tied to Open Library data
