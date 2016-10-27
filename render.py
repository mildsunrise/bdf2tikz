import math
import pyparsing
import parser

class RenderError(Exception):
  pass

# Global options passed in a dictionary:
#
#     offset: (x,y) tuple (in viewport units) that will be added to passed coordinates
#     scale: for what a viewport unit maps to, in TikZ units
#     extra_args: list of strings, extra TikZ options to use in statements
#     anchor_ports: whether port names should be anchored optimally
#     anchor_labels: whether connector labels should be anchored optimally

# VERY LOW LEVEL
# TikZ syntax for coordinates, points...

def render_tikz_length(length, options):
  return u"%.4f" % (length * options["scale"])

def render_tikz_vector(vector, options):
  assert len(vector) == 2
  vector = (vector[0], -vector[1])
  return u"(%s,%s)" % tuple(map(lambda x: render_tikz_length(x, options), vector))

def render_tikz_point(point, options):
  vector = point[0] + options["offset"][0], point[1] + options["offset"][1]
  return render_tikz_vector(vector, options)

def render_tikz_statement(arguments, content, options):
  arguments = options["extra_args"] + arguments
  return u"  \\draw[%s] %s;\n" % (u", ".join(arguments), content)

def render_tikz_comment(comment, options):
  return u"  %% %s\n" % (comment,)

REGULAR_ESCAPES = u"&%$#_{}"
SPECIAL_ESCAPES = {u"\\": u"textbackslash", u"^": u"textasciicircum", u"~": u"textasciitilde"}
def escape_latex_char(c):
  if c in REGULAR_ESCAPES: return "\\" + c
  if c in SPECIAL_ESCAPES: return "\\" + SPECIAL_ESCAPES[c]
  return c

def render_tikz_text(text, options):
  return "".join(map(escape_latex_char, text))

# TEXT RENDERING
# Anchors, calculating optimal anchor points, etc.

TEXT_HPOINTS = {-1: 0, 0: .5, +1: 1}
TEXT_VPOINTS = {-1: 0, 0: .5, +1: 1}

TEXT_ANCHORS = {
  "center":     ( 0, 0),
  "east":       (+1, 0),
  "south east": (+1,-1),
  "south":      ( 0,-1),
  "south west": (-1,-1),
  "west":       (-1, 0),
  "north west": (-1,+1),
  "north":      ( 0,+1),
  "north east": (+1,+1),
}

def find_anchor(point):
  for a in TEXT_ANCHORS:
    if TEXT_ANCHORS[a] == point: return a
  raise Exception("Invalid anchor point %s" % str(point))

def calculate_anchor_point(bounds, vertical, anchor):
  def map(x, start, end):
    #if start > end: start, end = end, start
    return start + x * (end - start)
  x, y = TEXT_ANCHORS[anchor]
  x = TEXT_HPOINTS[x]
  y = TEXT_VPOINTS[y]
  if vertical: x, y = 1-y, x
  return (map(x, bounds.x1, bounds.x2), map(y, bounds.y2, bounds.y1))

def calculate_optimal_anchor_to_line(bounds, vertical, line):
  def distance_to_segment(a, b, x):
    # vector algebra on the go! :D
    subtract = lambda a, b: (a[0]-b[0], a[1]-b[1])
    dot = lambda a, b: a[0]*b[0] + a[1]*b[1]
    norm = lambda a: math.sqrt(dot(a, a))
    distance = lambda a, b: norm(subtract(a, b))
    map = lambda x, start, end: start + x * (end - start)

    l = distance(a, b)
    if l == 0: return distance(a, x)
    t = max(0, min(1, dot(subtract(x,a), subtract(b,a)) / l))
    projection = (map(t, a[0], b[0]), map(t, a[1], b[1]))
    return distance(x, projection)

  p1 = (line.p1.x, line.p1.y)
  p2 = (line.p2.x, line.p2.y)
  anchors = TEXT_ANCHORS.keys()
  anchors.sort(key=lambda anchor: distance_to_segment(p1, p2, calculate_anchor_point(bounds, vertical, anchor)) + 1*(abs(TEXT_ANCHORS[anchor][0]) + abs(TEXT_ANCHORS[anchor][1])))
  return anchors[0]

def render_text(object, options):
  anchor = options["text_anchor"] if "text_anchor" in options else "center"
  bold = object.font.bold
  text_transform = options["text_transform"] if "text_transform" in options else lambda x: render_tikz_text(x, options)
  text = text_transform(object.text)
  vertical = object.vertical
  point = calculate_anchor_point(object.bounds, vertical, anchor)

  arguments = []
  if anchor != "center": arguments.append("anchor=" + anchor)
  if vertical: arguments.append("rotate=90")
  if bold: text = "\\textsf{%s}" % text
  contents = "%s node[%s] {%s}" % (render_tikz_point(point, options), ", ".join(arguments), text)
  return render_tikz_statement([], contents, options)

# GRAPHIC SHAPES
# Renders one TikZ statement for a passed graphic shape

def render_graphic_object(object, options):

  if isinstance(object, parser.Text):
    return render_text(object)

  if isinstance(object, parser.Line):
    p1, p2 = object.p1, object.p2
    contents = "%s -- %s" % (render_tikz_point((p1.x, p1.y), options), render_tikz_point((p2.x, p2.y), options))
    arguments = []
    return render_tikz_statement(arguments, contents, options)

  if isinstance(object, parser.Arc):
    bounds = object.bounds
    center = ((bounds.x1+bounds.x2) / 2.0, (bounds.y1+bounds.y2) / 2.0)
    radius = (abs(bounds.x1-bounds.x2) / 2.0, abs(bounds.y1-bounds.y2) / 2.0)

    p1 = (object.p1.x, object.p1.y)
    p2 = (object.p2.x, object.p2.y)
    dp1 = ((p1[0]-center[0])/radius[0], -(p1[1]-center[1])/radius[1])
    dp2 = ((p2[0]-center[0])/radius[0], -(p2[1]-center[1])/radius[1])

    angle1 = math.degrees(math.atan2(dp1[1], dp1[0]))
    angle2 = math.degrees(math.atan2(dp2[1], dp2[0]))
    mod1 = math.sqrt(dp1[0]**2 + dp1[1]**2)
    mod2 = math.sqrt(dp2[0]**2 + dp2[1]**2)

    np1 = (dp1[0]/mod1 * radius[0] + center[0], -dp1[1]/mod1 * radius[1] + center[1])
    np2 = (dp2[0]/mod2 * radius[0] + center[0], -dp2[1]/mod2 * radius[1] + center[1])

    contents = "%s arc[x radius=%s, y radius=%s, start angle=%.1f, end angle=%.1f]" % ( \
      render_tikz_point(np1, options), \
      render_tikz_length(radius[0], options), \
      render_tikz_length(radius[1], options), \
      angle1, angle2, \
    )
    arguments = []
    return render_tikz_statement(arguments, contents, options)

  if isinstance(object, parser.Rectangle):
    bounds = object.bounds
    start = (bounds.x1, bounds.y1)
    end = (bounds.x2, bounds.y2)
    contents = "%s rectangle %s" % (render_tikz_point(start, options), render_tikz_point(end, options))
    arguments = []
    return render_tikz_statement(arguments, contents, options)

  if isinstance(object, parser.Circle):
    bounds = object.bounds
    center = ((bounds.x1+bounds.x2) / 2.0, (bounds.y1+bounds.y2) / 2.0)
    radius = (abs(bounds.x1-bounds.x2) / 2.0, abs(bounds.y1-bounds.y2) / 2.0)
    contents = "%s circle[x radius=%s, y radius=%s]" % ( \
      render_tikz_point(center, options), \
      render_tikz_length(radius[0], options), \
      render_tikz_length(radius[1], options), \
    )
    arguments = []
    return render_tikz_statement(arguments, contents, options)

# TRANSFORMS
# Interpret transform attributes in objects into TikZ arguments,
# or equivalent matrixes.

ROTATION_MATRIXES = {
    0: [[ 1, 0],
        [ 0, 1]],
   90: [[ 0,-1],
        [-1, 0]],
  180: [[ 0,-1],
        [ 1, 0]],
  270: [[ 0, 1],
        [ 1, 0]],
}

def apply_matrix(matrix, point):
  x = matrix[0][0] * point[0] + matrix[0][1] * point[1]
  y = matrix[1][0] * point[0] + matrix[1][1] * point[1]
  return (x, y)

def get_point_transform(object):
  bounds = object.bounds
  matrix = ROTATION_MATRIXES[object.rotation or 0]
  size = (bounds.x2 - bounds.x1, bounds.y2 - bounds.y1)
  def transform_point(point):
    if object.mirror == "x": point = (point[0], size[1]-point[1])
    if object.mirror == "y": point = (size[0]-point[0], point[1])
    return apply_matrix(matrix, point)
  return transform_point

def transform_text_anchor(object, anchor):
  matrix = get_object_transform_matrix(object)
  point = TEXT_ANCHORS[anchor]
  point = apply_matrix(matrix, (point[0], point[1]))
  return find_anchor((point[0], -point[1]))

def get_object_transform_matrix(object):
  matrix = ROTATION_MATRIXES[object.rotation or 0]
  matrix = map(list, matrix) # deep copy
  if object.mirror == "x":
    matrix[0][1] *= -1
    matrix[1][1] *= -1
  if object.mirror == "y":
    matrix[0][0] *= -1
    matrix[1][0] *= -1
  return matrix

def get_object_transform_arguments(object):
  #TODO
  return []

# SCHEMATIC SHAPES
# Renders TikZ statements for a passed schematic object
# Highest level possible, prints warnings etc.

# Parsing and formatting node names

def _prepare_node_name_parser():
  from pyparsing import Suppress, Regex, OneOrMore, Optional, Group
  decimal = Regex("\d+").setParseAction(lambda t: int(t[0]))
  subscript_contents = decimal + Optional(Suppress("..") + decimal)
  subscript = Group(Suppress("[") + subscript_contents + Suppress("]")).setParseAction(lambda x: tuple(x[0]))
  component_name = Regex("\w+")
  component = Group(component_name + Optional(subscript)) \
    .setParseAction(lambda x: (x[0][0], x[0][1] if len(x[0]) > 1 else None))
  return OneOrMore(component)

node_name_parser = _prepare_node_name_parser()

def parse_node_name(name):
  """ Parse name in Quartus notation, returning a list of (name, subscript) tuples,
      where subscript is either None (no subscript found), or a (start[, end]) tuple. """
  return node_name_parser.parseString(name, parseAll=True).asList()

def get_type_width(parsed_name):
  get_component_width = lambda x: abs(x[1][0]-x[1][1])+1 if x[1] and len(x[1]) > 1 else 1
  return sum(map(get_component_width, parsed_name))

def render_node_name(name, options):
  def render_component(component):
    name, subscript = component
    if subscript and len(subscript) == 1:
      return "\\nodenamesingle{%s}{%d}" % (render_tikz_text(name, options), subscript[0])
    if subscript and len(subscript) == 2:
      return "\\nodenamerange{%s}{%d}{%d}" % (render_tikz_text(name, options), subscript[0], subscript[1])
    return "\\nodenamebit{%s}" % (render_tikz_text(name, options))
  return "$%s$" % " ".join(map(render_component, parse_node_name(name)))

# Line rendering

def render_all_lines(lines, options):
  # It's important to draw series of connectors "in a single run",
  # rather than many segments, so group them in runs, where each
  # run is a (point list, width) tuple
  runs = []

  def process_end(run):
    point = run[0][-1]
    neighbors = []

    def process(line):
      sides = {line[0], line[1]}
      if point not in sides: return True

      sides.remove(point)
      neighbors.append(iter(sides).next())
      if line[2] and run[1][0] and line[2] != run[1][0]:
        print "WARNING: widths inconsistent on point %s" % str(point)
      if run[1][0] is None:
        run[1][0] = line[2]
      return False
    lines[:] = [line for line in lines if process(line)]

    if len(neighbors) == 1:
      run[0].append(neighbors[0])
      return process_end(run)
    for neighbor in neighbors:
      start_run(point, neighbor, run[1])

  def start_run(start, to, width):
    run = ([start, to], width)
    runs.append(run)
    process_end(run)
    return run

  while len(lines):
    line = lines.pop()
    run = start_run(line[0], line[1], [line[2]])
    run[0].reverse()
    process_end(run)

  return "".join(map(lambda x: render_line_run(x,options), runs))

def render_line_run(run, options):
  points, width = run
  width = width[0]
  if width is None:
    print "WARNING: No known type for %s run, defaulting to node" % str(points[0])
    width = 1
  assert len(points) >= 2 and width >= 1
  contents = " -- ".join(map(lambda x: render_tikz_point(x, options), points))
  arguments = [("node" if width == 1 else "bus") + " line"]
  return render_tikz_statement(arguments, contents, options)

# Pin rendering

def render_pin(lines, pin, options):
  name = pin.name.text
  if pin.direction == "output":
    connection = (52,8)
    text_point = (82,8)
    text_anchor = "west"
    drawing = [(52,4), (78,4), (82,8), (78,12), (52,12)]
  elif pin.direction == "input":
    connection = (120.5,8)
    text_point = (92,8)
    text_anchor = "east"
    drawing = [(92,12), (117,12), (121,8), (117,4), (92,4)]
  else:
    print "WARNING: don't know how to render %s pin drawing" % pin.direction
    return None

  noptions = dict(options)
  noptions["offset"] = (options["offset"][0] + pin.bounds.x1, options["offset"][1] + pin.bounds.y1)
  statements = []

  # (apply transform to drawing if needed)
  transform = get_point_transform(pin)
  connection = transform(connection)
  text_point = transform(text_point)
  drawing = map(transform, drawing)
  text_anchor = transform_text_anchor(pin, text_anchor)

  # Draw bounds
  contents = "%s rectangle %s" % (render_tikz_point((0,0), noptions), render_tikz_point((pin.bounds.x2 - pin.bounds.x1, pin.bounds.y2 - pin.bounds.y1), noptions))
  if options["render_pin_bounds"]:
    statements += [render_tikz_statement(["pin bounds"], contents, noptions)]

  # Create connection line
  connection = (connection[0] + pin.bounds.x1, connection[1] + pin.bounds.y1)
  entry = (pin.p.x + pin.bounds.x1, pin.p.y + pin.bounds.y1)
  width = get_type_width(parse_node_name(name))
  lines.append((connection, entry, width))

  # Pin drawing itself
  contents = " -- ".join(map(lambda x: render_tikz_point(x, noptions), drawing) + ["cycle"])
  arguments = [pin.direction + " pin"]
  statements += [render_tikz_statement(arguments, contents, noptions)]

  # Draw pin name
  arguments = ["anchor=%s" % text_anchor]
  contents = "%s node[%s] {%s}" % ( \
    render_tikz_point(text_point, noptions), \
    ", ".join(arguments), \
    render_node_name(name, noptions), \
  )
  arguments = ["pin name"]
  statements += [render_tikz_statement(arguments, contents, noptions)]

  # FIXME: draw default level

  return "".join(statements)

# Symbol rendering

def is_primitive(symbol):
  # Try to detect if symbol is primitive
  #if symbol.typeText.bounds.x1 != 1 or symbol.typeText.bounds.y1 != 0:
  #  return False
  if len(symbol.drawing) == 1 and isinstance(symbol.drawing[0], parser.Rectangle):
    return False
  for port in symbol.ports:
    if not (port.text1.invisible and port.text2.invisible):
      return False
  return True

def render_symbol(lines, symbol, options):
  statements = []
  noptions = dict(options)
  noptions["offset"] = (noptions["offset"][0] + symbol.bounds.x1, noptions["offset"][1] + symbol.bounds.y1)
  primitive = is_primitive(symbol)

  # Draw bounds
  contents = "%s rectangle %s" % (render_tikz_point((0,0), noptions), render_tikz_point((symbol.bounds.x2 - symbol.bounds.x1, symbol.bounds.y2 - symbol.bounds.y1), noptions))
  if options["render_symbol_bounds"]:
    statements += [render_tikz_statement(["symbol bounds"], contents, noptions)]

  # Draw symbol type
  if (not primitive or symbol.typeText.text in ["VCC"]) and not symbol.typeText.invisible:
    noptions["extra_args"] = options["extra_args"] + ["symbol type"]
    statements += [render_text(symbol.typeText, noptions)]

  # Drawing itself
  noptions["extra_args"] = options["extra_args"] + ["symbol"]
  statements += [render_graphic_object(o, noptions) for o in symbol.drawing if not (hasattr(o, "invisible") and o.invisible)]

  # Process ports
  for port in symbol.ports:
    if port.text1.text != port.text2.text:
      print "WARNING: port on symbol %s has different texts: \"%s\" and \"%s\". picking the last one" % (symbol.name.text, port.text1.text, port.text2.text)
    
    if not port.text2.invisible:
      noptions["extra_args"] = options["extra_args"] + ["port name"]
      noptions["text_transform"] = lambda x: render_node_name(x, options)
      noptions["text_anchor"] = "center"
      if options["port_name_t_snap"]:
        snap_port_tangential(port, options["port_name_t_snap"])
      if options["port_name_n_snap"]:
        snap_port_normal(port, options["port_name_n_snap"], noptions)
      elif options["anchor_ports"]:
        noptions["text_anchor"] = calculate_optimal_anchor_to_line(port.text2.bounds, port.text2.vertical, port.line)
      statements += [render_text(port.text2, noptions)]

    # FIXME: draw arrows!
    if (port.p.x != port.line.p1.x or port.p.y != port.line.p1.y) and (port.p.x != port.line.p2.x or port.p.y != port.line.p2.y):
      print "WARNING: port line does not match port connection point"
    p1 = (port.line.p1.x + symbol.bounds.x1, port.line.p1.y + symbol.bounds.y1) 
    p2 = (port.line.p2.x + symbol.bounds.x1, port.line.p2.y + symbol.bounds.y1)
    width = get_type_width(parse_node_name(port.text2.text)) if not primitive else None
    lines.append((p1, p2, width))

  return "".join(statements)

def snap_port_tangential(port, limit):
  

def snap_port_distance(port, limit, options):
  distance = options["port_name_n_distance"]
  

# Little things: connectors, junctions...

def render_connector(lines, connector, options):
  p1 = (connector.p1.x, connector.p1.y)
  p2 = (connector.p2.x, connector.p2.y)
  width = None
  if connector.label:
    name = connector.label.text
    try:
      width = get_type_width(parse_node_name(name))
    except pyparsing.ParseException, e:
      print "WARNING: Couldn't parse \"%s\", ignoring" % name
  lines.append((p1, p2, width))
  # FIXME: it'd be nice to verify, at the end, that bus matched run width

  if connector.label:
    noptions = dict(options)
    noptions["extra_args"] = options["extra_args"] + ["line name"]
    noptions["text_transform"] = lambda x: render_node_name(x, options)
    if options["anchor_labels"]:
      noptions["text_anchor"] = calculate_optimal_anchor_to_line(connector.label.bounds, connector.label.vertical, parser.Line(connector.p1, connector.p2, None))
    try:
      return render_text(connector.label, noptions)
    except pyparsing.ParseException, e:
      print "WARNING: Couldn't parse \"%s\", ignoring" % name

def render_junction(junction, options):
  p = (junction.p.x, junction.p.y)
  contents = "%s node[contact] {}" % (render_tikz_point(p, options),)
  arguments = ["junction"]
  return render_tikz_statement(arguments, contents, options)

