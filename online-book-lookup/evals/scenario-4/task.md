# Network or API failure handling

Simulate or encounter an Open Library network/API failure while a user asks:

`Look up online book metadata for Dune.`

Goal:
- use the bundled helper
- report the structured `error` and `error_code` returned by the helper
- explain that the lookup could not be completed from Open Library data

Constraints:
- do not fall back to memory as if it were a verified online lookup
- do not invent current source URLs or identifiers
- do not recommend unrelated providers unless the user asks for alternatives
