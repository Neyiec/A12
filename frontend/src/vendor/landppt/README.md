# LandPPT attribution

Parts of A12's browser-based HTML slide quick-edit behavior are adapted from
[LandPPT](https://github.com/sligter/LandPPT), version `0.3.2`, commit
`19971a1120a42003658b3782666843b5ecbe7144`.

The adapted behavior is based on these upstream modules:

- `projectSlidesEditor.quickEdit.js`
- `projectSlidesEditor.quickEditActions.js`
- `projectSlidesEditor.quickEditStyling.js`

LandPPT is licensed under the Apache License 2.0. A copy of that license is
included in this directory. The A12 implementation is an adaptation for Vue,
same-origin iframe editing, local draft persistence, and Java-backed page APIs;
it is not a verbatim copy of LandPPT's Jinja-based editor.
