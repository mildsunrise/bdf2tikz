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

from pyparsing import ZeroOrMore
from .utils.sexp import sexp
import traceback
import re
import pprint

class ParseError(Exception):
  def __init__(self, reason):
    Exception.__init__(self, u"Malformed BDF file: %s" % (reason,))

SUPPORTED_HEADERS = {
  u"graphic": [u"1.3", u"1.4"],
  u"symbol": [u"1.1"],
}

def parse_bdf(input):
  # Decode in ASCII (FIXME)
  try:
    input = input.decode("ascii")
  except UnicodeDecodeError as e:
    raise ParseError("Non-ASCII content")

  # Remove starting comments, if present
  while True:
    input = input.lstrip()
    if input.startswith(u"/*"):
      input = input[2:]
      idx = input.find(u"*/")
      if idx == -1: raise ParseError(u"Unterminated comment")
      input = input[idx+2:]
    elif input.startswith(u"//"):
      input = input[2:]
      idx = input.find(u"\n")
      if idx == -1: idx = len(input)
      input = input[idx+1:]
    else: break

  # Parse S-expressions, validate and strip header
  parsed = ZeroOrMore(sexp).parseString(input, parseAll=True).asList()
  validate_header(parsed)

  return interpret_bdf(parsed)

def validate_header(parsed):
  if len(parsed) == 0 or parsed[0][:1] != [u"header"]:
    raise ParseError(u"No header present")
  header = parsed.pop(0)[1:]
  if len(header) != 2 or header[0] not in SUPPORTED_HEADERS or header[1][0] != u"version":
    raise ParseError(u"Not a BDF file, or unparseable header")
  version_info = header[1]
  if len(version_info) != 2 or version_info[1] not in SUPPORTED_HEADERS[header[0]]:
    raise ParseError(u"Invalid version info: %s %s" % (header[0], version_info[1]))

def interpret_bdf(parsed):
  objects = list(map(parse_object, parsed))
  for i in objects: assert isinstance(i, SchematicObject)
  return objects

# Internal objects
# (don't appear on the parsed result, will be replaced by its carrying attribute)

class ParseObject(object): pass

class FontSize(ParseObject):
  name = u"font_size"
  def __init__(self, size):
    self.size = size
  @staticmethod
  def parse(object):
    size = object.pop(0)
    assert isinstance(size, int)
    assert len(object) == 0
    return FontSize(size)

class LineWidth(ParseObject):
  name = u"line_width"
  def __init__(self, width):
    self.width = width
  @staticmethod
  def parse(object):
    width = object.pop(0)
    assert isinstance(width, int)
    assert len(object) == 0
    return LineWidth(width)

class Drawing(ParseObject):
  name = u"drawing"
  def __init__(self, objects):
    self.objects = objects
  @staticmethod
  def parse(object):
    objects = list(map(parse_object, object))
    for o in objects: assert isinstance(o, GraphicObject)
    return Drawing(objects)

class AnnotationBlock(ParseObject):
  name = u"annotation_block"
  @staticmethod
  def parse(object):
    return AnnotationBlock() # TODO: parse those, use in Pin

# Basic objects

class Font(ParseObject):
  name = u"font"
  def __init__(self, font, font_size, bold):
    self.font = font
    self.font_size = font_size
    self.bold = bold
  def __repr__(self):
    result = self.font
    if self.bold:
      result += u" Bold"
    if not (self.font_size is None):
      result += u" %d" % self.font_size
    return result
  @staticmethod
  def parse(object):
    font = object.pop(0)
    assert isinstance(font, str)
    font_size = None
    bold = None
    for o in object:
      o = parse_object(o)
      if o == u"bold":
        assert bold is None
        bold = True
      elif isinstance(o, FontSize):
        assert font_size is None
        font_size = o.size
      else: raise ParseError("Invalid object %s found in font" % o)
    return Font(font, font_size, bold)

class Bounds(ParseObject):
  name = u"rect"
  def __init__(self, x1, y1, x2, y2):
    self.x1, self.y1 = x1, y1
    self.x2, self.y2 = x2, y2
  def __repr__(self):
    return u"Bounds{(%d, %d) to (%d, %d)}" % (self.x1, self.y1, self.x2, self.y2)
  @staticmethod
  def parse(object):
    assert len(object) == 4
    for i in object: assert isinstance(i, int)
    return Bounds(*object)

class Point(ParseObject):
  name = u"pt"
  def __init__(self, x, y):
    self.x, self.y = x, y
  def __repr__(self):
    return u"(%d, %d)" % (self.x, self.y)
  @staticmethod
  def parse(object):
    assert len(object) == 2
    for i in object: assert isinstance(i, int)
    return Point(*object)

# Attribute containers
# (only found as attributes of one specific block)

DIRECTIONS = [u"output", u"input", u"bidir"] # FIXME: verify bidir

class Port(ParseObject):
  name = u"port"
  def __init__(self, p, direction, text1, text2, line):
    self.p = p
    self.direction = direction
    self.text1 = text1
    self.text2 = text2
    self.line = line
  def __str__(self):
    return u"%s port %s at %s" % (self.direction, self.text1.text, self.point)
  @staticmethod
  def parse(object):
    assert len(object) == 5
    object = list(map(parse_object, object))
    assert isinstance(object[0], Point)
    assert object[1] in DIRECTIONS
    assert isinstance(object[2], Text) and isinstance(object[3], Text)
    assert isinstance(object[4], Line)
    return Port(*object)

# Schematic objects
# (anything that can appear on the top level)

class SchematicObject(ParseObject):
  def __repr__(self):
    return "\n" + type(self).__name__ +" {\n  %s\n}" % pprint.pformat(vars(self), indent=2)[2:-1]

class Junction(SchematicObject):
  name = u"junction"
  def __init__(self, p):
    self.p = p
  @staticmethod
  def parse(object):
    assert len(object) == 1
    object = list(map(parse_object, object))
    assert isinstance(object[0], Point)
    return Junction(*object)

class Connector(SchematicObject):
  name = u"connector"
  def __init__(self, p1, p2, label, bus): # FIXME: conduit lines
    self.p1, self.p2 = p1, p2
    self.label = label
    self.bus = bus
  @staticmethod
  def parse(object):
    object = parse_grouped(object, {
      Point: (2,2),
      Text: (0,1),
      str: (0,1),
    })
    bus = None
    label = None
    if u"bus" in object[str]: bus = True
    if len(object[Text]): label = object[Text][0]
    return Connector(object[Point][0], object[Point][1], label, bus)

class Symbol(SchematicObject):
  name = u"symbol"
  def __init__(self, bounds, ports, typeText, name, drawing, mirror, rotation):
    self.bounds = bounds
    self.ports = ports
    self.typeText = typeText
    self.name = name
    self.drawing = drawing
    self.mirror = mirror
    self.rotation = rotation
  @staticmethod
  def parse(object):
    o = parse_grouped(object, {
      Text: (2,2),
      Bounds: (1,1),
      Port: (0,),
      Drawing: (1,1),
      str: (0,),
    })
    mirror, rotation = None, None
    for flag in o[str]:
      sflag = re.match("^(flip([xy])_)?rotate(90|180|270)$", flag) or re.match("^(flip([xy]))$", flag)
      if sflag:
        mirror = sflag.group(2)
        if len(sflag.groups()) > 2 and sflag.group(3): rotation = int(sflag.group(3))
      else: raise ParseError(u"Unknown flag %s in Symbol" % flag)
    return Symbol(o[Bounds][0], o[Port], o[Text][0], o[Text][1], o[Drawing][0].objects, mirror, rotation)

class Pin(SchematicObject):
  name = u"pin"
  def __init__(self, bounds, direction, p, typeText, name, level, drawing, mirror, rotation):
    self.bounds = bounds
    self.direction = direction
    self.p = p
    self.typeText = typeText
    self.name = name
    self.level = level
    self.drawing = drawing
    self.mirror = mirror
    self.rotation = rotation
  @staticmethod
  def parse(object):
    o = parse_grouped(object, {
      Text: (2,3),
      Bounds: (1,1),
      Point: (1,1),
      Drawing: (1,1),
      AnnotationBlock: (0,),
      str: (0,),
    })
    level = o[Text][2] if len(o[Text]) > 2 else None
    direction, mirror, rotation = None, None, None
    for flag in o[str]:
      sflag = re.match("^(flip([xy])_)?rotate(90|180|270)$", flag) or re.match("^(flip([xy]))$", flag)
      if sflag: # FIXME: check duplicity
        mirror = sflag.group(2)
        if len(sflag.groups()) > 2 and sflag.group(3): rotation = int(sflag.group(3))
      elif flag in DIRECTIONS:
        assert direction is None
        direction = flag
      else: raise ParseError(u"Unknown flag %s in Pin" % flag)
    return Pin(o[Bounds][0], direction, o[Point][0], o[Text][0], o[Text][1], level, o[Drawing][0].objects, mirror, rotation)

class GraphicObject(SchematicObject):
  pass

class Text(GraphicObject):
  name = u"text"
  def __init__(self, text, bounds, font, vertical, invisible):
    self.text = text
    self.bounds = bounds
    self.font = font
    self.vertical = vertical
    self.invisible = invisible
  @staticmethod
  def parse(object):
    text = object.pop(0)
    assert isinstance(text, str)
    o = parse_grouped(object, {
      Bounds: (1,1),
      Font: (1,1),
      str: (0,),
    })
    vertical, invisible = None, None
    for flag in o[str]:
      if flag == u"vertical":
        assert vertical is None
        vertical = True
      elif flag == u"invisible":
        assert invisible is None
        invisible = True
      else: raise ParseError(u"Unknown flag %s in Text" % flag)
    return Text(text, o[Bounds][0], o[Font][0], vertical, invisible)

class Line(GraphicObject):
  name = u"line"
  def __init__(self, p1, p2, line_width):
    self.p1, self.p2 = p1, p2
    self.line_width = line_width
  @staticmethod
  def parse(object): # FIXME: migrate
    assert len(object) == 3
    object = list(map(parse_object, object))
    assert isinstance(object[0], Point)
    assert isinstance(object[1], Point)
    assert isinstance(object[2], LineWidth)
    object[2] = object[2].width
    return Line(*object)

class Arc(GraphicObject):
  name = u"arc"
  def __init__(self, p1, p2, bounds, line_width):
    self.p1, self.p2 = p1, p2
    self.bounds = bounds
    self.line_width = line_width
  @staticmethod
  def parse(object):
    o = parse_grouped(object, {
      Point: (2,2),
      Bounds: (1,1),
      LineWidth: (0,1),
    })
    line_width = None
    if len(o[LineWidth]): line_width = o[LineWidth][0].width
    return Arc(o[Point][0], o[Point][1], o[Bounds][0], line_width)

class Rectangle(GraphicObject):
  name = u"rectangle"
  def __init__(self, bounds, line_width):
    self.bounds = bounds
    self.line_width = line_width
  @staticmethod
  def parse(object):
    o = parse_grouped(object, {
      Bounds: (1,1),
      LineWidth: (0,1),
    })
    line_width = None
    if len(o[LineWidth]): line_width = o[LineWidth][0].width
    return Rectangle(o[Bounds][0], line_width)

class Circle(GraphicObject):
  name = u"circle"
  def __init__(self, bounds, line_width):
    self.bounds = bounds
    self.line_width = line_width
  @staticmethod
  def parse(object):
    o = parse_grouped(object, {
      Bounds: (1,1),
      LineWidth: (0,1),
    })
    line_width = None
    if len(o[LineWidth]): line_width = o[LineWidth][0].width
    return Circle(o[Bounds][0], line_width)

# Generic parsing

all_types = {}

def parse_object(object):
  if (not isinstance(object, list)) or len(object) < 1 or (not isinstance(object[0], str)):
    raise ParseError(u"Not an object: %s" % repr(object))
  name = object.pop(0)
  if name not in all_types:
    if len(object) == 0: return name
    raise ParseError(u"Unknown object type %s" % name)
  try:
    result = all_types[name].parse(object)
    assert isinstance(result, all_types[name])
    return result
  except Exception as e:
    if isinstance(e, ParseError): raise
    raise ParseError(u"Couldn't parse %s %s:\n%s" % (name, repr(object), traceback.format_exc(e)))

def parse_grouped(object, types):
  """ types is a dictionary mapping Type -> (min occurrences, max occurrences) """
  result = {t: [] for t in types}
  for o in map(parse_object, object):
    added = False
    for t in result:
      if isinstance(o, t):
        result[t].append(o)
        added = True
        break
    if not added:
      raise ParseError(u"Unexpected %s object in %s" % (type(o), o))
  for t in result:
    l, constraints = len(result[t]), types[t]
    min, max = constraints[0], None
    if len(constraints) > 1: max = constraints[1]
    if not (min is None):
      if l < min: raise ParseError(u"Need at least %d instances of %s, found %d" % (min, t, l))
    if not (max is None):
      if l > max: raise ParseError(u"Need at most %d instances of %s, found %d" % (min, t, l))
  return result

# Make them inherit from base class to tag them, don't rely in name present
for thing in list(globals().values()):
  if (type(thing) is type) and issubclass(thing, ParseObject) and hasattr(thing, "name"):
    all_types[thing.name] = thing
