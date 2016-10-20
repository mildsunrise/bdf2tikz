from pyparsing import ZeroOrMore
from utils.sexp import sexp
import traceback
import re
import pprint

class ParseError(Exception):
  def __init__(self, reason):
    Exception.__init__(self, u"Malformed BDF file: %s" % (reason,))

def parse_bdf(input):
  # Decode in ASCII (FIXME)
  try:
    input = input.decode("ascii")
  except UnicodeDecodeError, e:
    raise ParseError(u"Non-ASCII content")

  # Remove starting comments, if present
  while True:
    input = input.lstrip()
    if not input.startswith(u"/*"): break
    input = input[2:]
    idx = input.find(u"*/")
    if idx == -1: raise ParseError(u"Unterminated comment")
    input = input[idx+2:]

  # Parse S-expressions, validate and strip header
  parsed = ZeroOrMore(sexp).parseString(input, parseAll=True).asList()
  validate_header(parsed)

  return interpret_bdf(parsed)

def validate_header(parsed):
  if len(parsed) == 0 or parsed[0][:1] != [u"header"]:
    raise ParseError(u"No header present")
  header = parsed.pop(0)[1:]
  if len(header) != 2 or header[0] != u"graphic" or header[1][0] != u"version":
    raise ParseError(u"Not a BDF file, or unparseable header")
  if header[1] != [u"version", u"1.4"]:
    raise ParseError(u"Invalid version info: %s" % (header[1],))

def interpret_bdf(parsed):
  objects = map(parse_object, parsed)
  for i in objects: assert isinstance(i, SchematicObject)
  return objects

# Internal objects
# (don't appear on the parsed result, will be replaced by its carrying attribute)

class FontSize:
  name = u"font_size"
  def __init__(self, size):
    self.size = size
  @staticmethod
  def parse(object):
    size = object.pop(0)
    assert isinstance(size, int)
    assert len(object) == 0
    return FontSize(size)

class LineWidth:
  name = u"line_width"
  def __init__(self, width):
    self.width = width
  @staticmethod
  def parse(object):
    width = object.pop(0)
    assert isinstance(width, int)
    assert len(object) == 0
    return LineWidth(width)

class Drawing:
  name = u"drawing"
  def __init__(self, objects):
    self.objects = objects
  @staticmethod
  def parse(object):
    objects = map(parse_object, object)
    for o in objects: assert isinstance(o, GraphicObject)
    return Drawing(objects)

# Basic objects

class Font:
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
    assert isinstance(font, unicode)
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

class Bounds:
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

class Point:
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

class Port:
  name = u"port"
  def __init__(self, point, direction, text1, text2, line):
    self.point = point
    self.direction = direction
    self.text1 = text1
    self.text2 = text2
    self.line = line
  def __str__(self):
    return u"%s port %s at %s" % (self.direction, self.text1.text, self.point)
  @staticmethod
  def parse(object):
    assert len(object) == 5
    object = map(parse_object, object)
    assert isinstance(object[0], Point)
    assert object[1] in DIRECTIONS
    assert isinstance(object[2], Text) and isinstance(object[3], Text)
    assert isinstance(object[4], Line)
    return Port(*object)

# Schematic objects
# (anything that can appear on the top level)

class SchematicObject(object):
  def __repr__(self):
    return "\n" + type(self).__name__ +" {\n  %s\n}" % pprint.pformat(vars(self), indent=2)[2:-1]

class Junction(SchematicObject):
  name = u"junction"
  def __init__(self, point):
    self.point = point
  @staticmethod
  def parse(object):
    assert len(object) == 1
    object = map(parse_object, object)
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
      unicode: (0,1),
    })
    bus = None
    label = None
    if u"bus" in object[unicode]: bus = True
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
      unicode: (0,),
    })
    mirror, rotation = None, None
    for flag in o[unicode]:
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
      unicode: (0,),
    })
    level = o[Text][2] if len(o[Text]) > 2 else None
    direction, mirror, rotation = None, None, None
    for flag in o[unicode]:
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
    assert isinstance(text, unicode)
    o = parse_grouped(object, {
      Bounds: (1,1),
      Font: (1,1),
      unicode: (0,),
    })
    vertical, invisible = None, None
    for flag in o[unicode]:
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
    object = map(parse_object, object)
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
  def __init__(self, bounds):
    self.bounds = bounds
  @staticmethod
  def parse(object): # FIXME: migrate
    assert len(object) == 1
    object = map(parse_object, object)
    assert isinstance(object[0], Bounds)
    return Rectangle(*object)

class Circle(GraphicObject):
  name = u"circle"
  def __init__(self, bounds):
    self.bounds = bounds
  @staticmethod
  def parse(object): # FIXME: migrate
    assert len(object) == 1
    object = map(parse_object, object)
    assert isinstance(object[0], Bounds)
    return Circle(*object)

# Generic parsing

all_types = {}

def parse_object(object):
  if (not isinstance(object, list)) or len(object) < 1 or (not isinstance(object[0], unicode)):
    raise ParseError(u"Not an object: %s" % repr(object))
  name = object.pop(0)
  if name not in all_types:
    if len(object) == 0: return name
    raise ParseError(u"Unknown object type %s" % name)
  try:
    result = all_types[name].parse(object)
    assert isinstance(result, all_types[name])
    return result
  except Exception, e:
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
import types
for thing in globals().values():
  if (isinstance(thing, type) or isinstance(thing, types.ClassType)) and hasattr(thing, u"name"):
    all_types[thing.name] = thing
