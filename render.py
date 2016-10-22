import math
import parser

class RenderError(Exception):
  pass

# Global options passed in a dictionary:
# offset: (x,y) tuple (in viewport units) that will be added to passed coordinates
# scale: for what a viewport unit maps to, in TikZ units
# extra_args: list of strings, extra TikZ options to use in statements

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

# GRAPHIC SHAPES
# Renders one TikZ statement for a passed graphic shape

#TODO: remove
def draw_test_point(point, options):
  if isinstance(point, parser.Point): point = (point.x, point.y)
  return "  \\filldraw[gray] %s circle [radius=2pt];\n" % render_tikz_point(point, options)

def render_graphic_object(object, options):

  if isinstance(object, parser.Text):
    bounds = object.bounds
    bold = object.font.bold
    text = render_tikz_text(object.text, options)
    vertical = object.vertical

    arguments = []
    if vertical: arguments.append("rotate=-90")
    if bold: text = "\textsf{%s}" % text
    center = ((bounds.x1+bounds.x2) / 2.0, (bounds.y1+bounds.y2) / 2.0)
    contents = "%s node[%s] {%s}" % (render_tikz_point(center, options), ", ".join(arguments), text)
    return render_tikz_statement([], contents, options)

  if isinstance(object, parser.Line):
    p1, p2 = object.p1, object.p2
    contents = "%s -- %s" % (render_tikz_point((p1.x, p1.y), options), render_tikz_point((p2.x, p2.y), options))
    arguments = []
    # TODO: line_width
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
    # TODO: line_width
    return render_tikz_statement(arguments, contents, options)

  if isinstance(object, parser.Rectangle):
    bounds = object.bounds
    start = (bounds.x1, bounds.y1)
    end = (bounds.x2, bounds.y2)
    contents = "%s rectangle %s" % (render_tikz_point(start, options), render_tikz_point(end, options))
    arguments = []
    # TODO: line_width
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
    # TODO: line_width
    return render_tikz_statement(arguments, contents, options)

# SCHEMATIC SHAPES
# Renders TikZ statements for a passed schematic object
# Highest level possible, prints warnings etc.

def render_drawing(objects, options):
  pass
