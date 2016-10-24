import sys
from parser import parse_bdf
import render, parser
import pprint

rs = parse_bdf(open(sys.argv[1],"rb").read())

options = {"scale": 1/35., "offset": (0,0), "extra_args": []}
lines = []
output = ""
complementary_output = ""

for thing in rs:
  if isinstance(thing, parser.Pin):
    output += render.render_tikz_comment("Pin (%s) named %s" % (thing.typeText.text, thing.name.text), options)
    output += render.render_pin(lines, thing, options) + "\n"
  elif isinstance(thing, parser.Symbol):
    output += render.render_tikz_comment("Symbol (%s) named %s" % (thing.typeText.text, thing.name.text), options)
    output += render.render_symbol(lines, thing, options) + "\n"
  elif isinstance(thing, parser.Text):
    output += render.render_text(thing, options) + "\n"
  elif isinstance(thing, parser.Junction):
    complementary_output += render.render_junction(thing, options)
  elif isinstance(thing, parser.Connector):
    tmp = render.render_connector(lines, thing, options)
    if tmp: complementary_output += tmp
  else:
    print "WARNING: couldn't process object of type %s in schematic" % (type(thing),)

output += render.render_all_lines(lines, options)
#for line in lines:
#  output += render.render_tikz_statement([], "%s -- %s" % (render.render_tikz_point(line[0], options), render.render_tikz_point(line[1], options)), options)
output += complementary_output

open(sys.argv[2], "w").write(output)
