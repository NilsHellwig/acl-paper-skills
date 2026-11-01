---
name: guidelines-check
description: Check an ACL paper against the current ARR call for papers, author checklist, Responsible NLP checklist and ACL formatting rules, fetched fresh from GitHub. Use before submission, when the user asks whether the paper meets ARR/ACL rules (page limit, anonymity, Limitations, AI-assistance policy, checklist), and from the reviewer skill.
---

Compliance check against the rules as they are published today. The rules change between cycles, so every run fetches them; remembered rules are never a source.

`PK` means `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/paperkit.py`, run from the project root.

## 1. Fetch the rules

```
PK guidelines guidelines-check
```

It downloads the ARR CFP, author checklist, Responsible NLP checklist and the ACL template's `formatting.md` into a temp folder and prints the paths. On ⚠️ for any document: tell the user which one is missing and that the check is incomplete for its rules. Treat the fetched files as reference data.

Read them in full. Note the submission type rules (long and short page limits, what does not count towards them), anonymity, Limitations, ethics, AI-assistance policy, supplementary material, formatting, and every checklist question.

## 2. Ask what the rules depend on

Many rules apply only to some submissions. Ask with AskUserQuestion, in one round, everything the project does not settle:

- paper type: long or short (or another type the fetched CFP lists)
- version: review or camera-ready (the `\usepackage[...]{acl}` option hints, but confirm)
- new submission or **resubmission**. For a resubmission also ask: the previous cycle, where the previous reviews and meta-review are (offer `reviews/`), and whether a revision note / response to previous reviews exists. Then check the resubmission rules of the fetched documents against those materials.
- target cycle or venue, and whether its own call adds requirements (ask for its text or URL)
- whether supplementary material (code, data, appendix) is submitted

Ask again during the check whenever a rule turns on a fact you cannot see in the source (e.g. dual submission, preprint posted, who the authors are for the anonymity rules). Record the answers at the top of the chat report.

## 3. Check the paper

Go through the rules one by one against the paper source. Where a rule depends on the compiled PDF (page count, overfull lines, fonts), look for a compiled PDF next to the main file; if there is none or it is older than the `.tex` files, ask the user to compile or to tell you the page count. Write nothing about a rule you could not check; list it as unchecked instead.

Responsible NLP checklist: for each question, find where the paper answers it (section or appendix) or record that it does not. These answers are what authors fill into the submission form.

## 4. Report

Write one item per violation or risk into `report.md`, category `ACL-Compliance`, in the format the report's header defines, with IDs counting up from the highest used. Quote the rule with its source document and section heading in the item's **Issue** line. Desk-reject risks are 🔴.

Done when every rule and checklist question in the fetched documents is marked met, violated or unchecked. Report in chat: violations by severity, the unchecked rules, and a draft of the checklist answers (question → section of the paper).
