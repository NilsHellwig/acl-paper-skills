<!-- Example style profile offered by /acl-paper:init for the `## Style` section of
CLAUDE.md. Distilled from a PhD thesis workflow; every rule is optional. -->

- Introduce terms in plain text. Reserve `\emph{}` / `\textit{}` for genuine emphasis, which a paper rarely needs.
- Write spelled-out forms of abbreviations in title case: "Aspect Sentiment Triplet Extraction (ASTE)". After the introduction, use the abbreviation.
- Join clauses with a comma and a connector ("and", "though", "with") where a semicolon would go. Keep the sentence connected and avoid choppy short sentences.
- Use "significant" only for statistical significance.
- Prefer concrete verbs over "established": "introduced", "defined", "proposed".
- Capitalize names of defined items (criteria, table rows, categories) wherever the text refers to them by name.
- Start captions with a bold lead phrase that ends in a period: `\caption{\textbf{Short title.} Description.}`. Captions go below tables.
- Every `\section` and `\subsection` gets a `\label{sec:...}` on the next line.
- Link Hugging Face models as `https://hf.co/...` in a footnote, only for an explicitly versioned checkpoint or a model without a paper. Cite the model's paper at its first mention.
