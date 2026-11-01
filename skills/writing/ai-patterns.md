# Patterns that make prose read as machine-written

Distilled from [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (revision of November 2026) and adapted to NLP papers. Each pattern names what to write instead. One occurrence is rarely a problem; clusters are. Project rules in `CLAUDE.md` → `## Style` win where they differ.

## Content

- **Inflated significance.** "marks a pivotal moment", "represents a significant shift", "part of a broader movement". → State what the work does and what it changes, with the number or the comparison.
- **Superficial analysis.** A trailing "-ing" clause that comments on importance: "..., highlighting the importance of context", "..., underscoring the need for ...". → Delete it, or turn it into a claim with evidence.
- **Vague attribution.** "Researchers have argued", "it is widely believed", "several studies show" with one or no citation. → Name the source with `\citet{}` or narrow the claim to what the cited work shows.
- **Vague connection.** "is closely related to", "is associated with". → Say how: "extends", "reuses the encoder of", "evaluates on the same data as".
- **Formulaic outlook.** "Despite its strengths, X faces challenges ... Future work could ...". → Name the concrete limitation and the concrete next experiment.
- **Promotional tone.** "novel", "powerful", "state-of-the-art" without a comparison; "remarkable", "impressive". → Let the result table carry the claim.

## Vocabulary

Overused words (the full list, which `paperkit.py check` scans for, is `scripts/paperkit/data/ai_vocabulary.txt` in the plugin): *delve, crucial, pivotal, key (adj.), landscape, leverage, showcase, underscore, highlight (fig.), emphasize, enhance, foster, intricate, multifaceted, notably, realm, seamless, tapestry, testament, valuable insights, plays a crucial role*. → Use the plain verb ("use", "show", "improve") or cut the word.

Paper-specific:

- "significant" only for statistical significance, with the test named.
- "robust" only for a measured robustness property.
- "novel" at most once, for the contribution itself.
- Superlatives that cannot be checked ("one of the first", "the most comprehensive") → "an early", or cite the comparison.
- Vague agents ("practitioners", "the community") → describe the process or name who.

## Sentence structure

- **Negative parallelism.** "not X but Y", "not just X, but also Y", "Y rather than X". → State Y directly. Keep a contrast only when X is a real position someone holds (and cite it).
- **Rule of three.** Triads used for rhythm: "efficient, scalable, and robust". → Keep the items that carry distinct content, with evidence for each.
- **Copula avoidance.** "serves as", "stands as", "functions as", "marks". → "is".
- **Colon reveal.** "The result is clear: ..." repeated across a paragraph. → One per paragraph at most.
- **Formulaic openers.** "This paper addresses this gap.", "In this section, we ...". → Vary, or start with the content.
- **Overpacked sentences.** Several subordinate clauses chained with "which", "-ing", "via". → Split at the second clause.

## Punctuation and formatting

- **Em dashes.** Frequent `---` for asides. → Comma, parentheses, or a new sentence.
- **Curly or straight quotes in LaTeX.** → ``` ``...'' ```.
- **Bold and inline-header lists in running text.** → Paragraphs; bold only where the template uses it (caption lead phrases, table headers).
- **Capitalized common nouns in running text.** "our Proposed Framework" → "our proposed framework". Section titles keep the template's title case.

## Citations and numbers

- Each sentence that rests on a source keeps its citation after a rewrite.
- Paraphrase; copy no sentence or longer phrase from a cited paper.
- Report numbers exactly as printed in the cited paper. Differences, averages or gains you compute go in words ("clearly higher"), not as figures attributed to the paper.

## Signs of human writing worth keeping

Specific detail, uneven sentence length, a clear claim with its evidence, domain terms used precisely and consistently. Edits keep these.
