# bdf2tikz

Program that reads Quartus Schematic files (`.bdf` extension) and emits LaTeX
code that uses TikZ to create a graphic resembling the passed schematic. This
graphic can then be embedded in documents.

The program can generate one of:

 - LaTeX source for a minimal complete document (using the `standalone` class).
 - LaTeX code for the graphic (i.e. to be `\input` into a document).
 - TikZ instructions (i.e. to be `\input` inside a `tikzpicture` environment).

The third one allows for maximum control, you can supply your own TikZ styles
for parts of the schematic. The second and first ones will use a template
with predefined TikZ styles, which can be seen at `template.tex`.

In the first case, this will all be wrapped inside a `standalone` document with
a second template that can be seen at `document.tex`.

Main features:

 - Scale and other conversion parameters can be tuned via command line options.
 - Support for BDF versions 1.3 and 1.4 (more may be supported but
   have to be checked and added to the whitelist first).
 - Also supports BSF versions 1.1 (which are actually schematics with
   only one symbol).
 - Symbols (optional substitution with TikZ native logic gates).
 - Node / bus connectors, with / without label, and junctions.
 - Input / output pins with label (with manual drawing).
 - All graphic elements supported (line, arc, rectangle, circle).
 - Ability to infer (and typeset) type width of each connector,
   including port lines inside symbols.
 - Consecutive connectors (segments) will be drawn as a single path in TikZ,
   providing correct typesetting.
 - Optionally, each run can be "tagged" with its width.
 - Port lines can have optional arrows if they are inputs.
 - Optional bounds rendering for pins and / or symbols.
 - Anchors can be intelligently selected for line labels and port names.
 - Text comments supported.
 - Rotated and / or mirrored symbols or pins supported.
 - Ability to aggressively "snap" port names to their rectangle.

Unsupported features:

 - Pin location annotations not rendered.
 - Symbol instance names not rendered.
 - Conduit lines currently treated like node / bus lines.
 - Bidirectional pins currently not supported.
 - Graphic elements *directly on the schematic* (other than text) not rendered.
 - Font, font sizes and line widths currently ignored (taken from style).
 - Non-default colors currently unparseable (schematic will be rejected).

## Install

This program needs the `pyparsing` module to be available. Install with:

    pip install pyparsing

However, you need a LaTeX distribution installed in order to compile the
resulting code into a PDF. The code only has dependencies with TikZ and its
`circuits` libraries. (For advanced users: you can avoid the circuits library
dependency if you disable native symbols and provide your own `contact` node
style.)

The template also depends on the `amsmath` package and the `arrows.meta`
TikZ library.

## Usage

    python main.py <BDF file> out.tex

Note that `main.py` can also be used as a module for programmatic rendering.
(Option parsing is still pending.)
