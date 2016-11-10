#!/usr/bin/env python

import sys
from parser import parse_bdf
import render, parser
import pprint

default_options = {
  "scale": 1/42.,
  "port_name_t_snap": 8, "port_name_n_snap": 12, "port_name_n_distance": 4,
  "anchor_ports": True, "anchor_labels": True,
  "render_pin_bounds": False,
  "render_symbol_bounds": True, "render_primitive_bounds": False,
  "port_input_arrows": True, "connector_output_arrows": True,

  "offset": (0,0), "extra_args": [],
}

def render_bdf(rs, options):
	rs = parse_bdf(rs)
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
	output += complementary_output

	return output



if __name__ == "__main__":
  rs = open(sys.argv[1],"rb").read()
  output = render_bdf(rs, default_options)
  open(sys.argv[2], "w").write(output)
