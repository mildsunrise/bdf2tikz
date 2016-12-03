#!/usr/bin/env python
# Copyright 2016 Alba Mendez <me@alba.sh>
#
# This file is part of bdf2tikz.
#
# bdf2tikz is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bdf2tikz is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bdf2tikz.  If not, see <http://www.gnu.org/licenses/>.

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
  "port_input_arrows": True, "port_arrows_if_invisible": False,
  "connector_output_arrows": True,

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
      print("WARNING: couldn't process object of type %s in schematic" % (type(thing),))

  output += render.render_all_lines(lines, options)
  output += complementary_output

  return output



if __name__ == "__main__":
  rs = open(sys.argv[1],"rb").read()
  output = render_bdf(rs, default_options)
  open(sys.argv[2], "w").write(output)
