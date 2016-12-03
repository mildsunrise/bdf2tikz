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
from bdf2tikz.process import render_bdf, default_options

rs = open(sys.argv[1],"rb").read()
output = render_bdf(rs, default_options)
open(sys.argv[2], "w").write(output)
