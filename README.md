# bdf2tikz

Program that reads Quartus Schematic files (`.bdf` extension) and emits LaTeX
code that uses TikZ to create a graphic resembling the passed schematic. This
graphic can then be embedded in documents.

The program can generate:

 - LaTeX source for a minimal complete document (using the `standalone` class).
 - LaTeX code for the graphic (i.e. to be `\input` into a document).
 - TikZ instructions (i.e. to be `\input` inside a `tikzpicture` environment).

The third one allows for maximum control, you can supply your own TikZ styles
for parts of the schematic.

Supports:

 - All graphic elements (line, arc, rectangle, circle)
 - Input / output pins
 - Symbols
 - Node / bus connectors, with / without label
 - Junctions
 - Text comments
 - Rotated / mirrored symbols / pins

Pin location annotations are ignored.

## Install

TODO

## Usage

TODO
