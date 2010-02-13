import os
import re
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

TEMPLATES_DIR = 'templates'
HTDOCS_HARDCODED_PATH = '/home/desuchan/public_html/desuchan.net/htdocs/'
FUTABA_STYLE_DEBUG = 0

TEMPLATE_RE = re.compile(r'^use constant ([A-Z_]+) => (.*?;)\s*\n\n', re.M | re.S)
TEMPLATE_SECTION_RE = re.compile(
    r'('
        r'q{((?:[^{}]|{[^{}]*})*)}|'    # allow non-nested braces inside the q{}
        r'include\("([a-z_/\.]*?)"\)|'
        r'"(.*?)"|'
        r'([A-Z][A-Z_]+)|'
        r'sprintf\(S_ABBRTEXT,[\'"](.*?)[\'"]\)'
    r')[\.;] *',
    re.S | re.M)

COMPILE_TEMPLATE_RE = re.compile(
    r'^compile_template ?\((.*?)\);$',
    re.S)

def debug_item(name, value='', match=None, span=''):
    span = match and match.span() or span
    if value:
        value = repr(value)[1:-1]
        if len(value) > 50:
            value = value[:50] + "[...]"
    print ' %14s %-8s %s' % (span, name, value)

class FutabaStyleParser(object):
    FILENAME = "futaba_style.pl"
    
    def __init__(self):
        self.debug = FUTABA_STYLE_DEBUG

        self.lastend = 0

        self.current = None

        if not os.path.exists(TEMPLATES_DIR):
            os.mkdir(TEMPLATES_DIR)

        self.tl = Jinja2Translator(self)

        TEMPLATE_RE.sub(self.do_constant,
            open(FutabaStyleParser.FILENAME).read())

    def debug_item(self, *args, **kwds):
        if not self.debug:
            return
        debug_item(*args, **kwds)

    def do_constant(self, match):
        name, template = match.groups()
        
        if self.debug:
            print name
        
        # remove compile_template(...)
        compile = COMPILE_TEMPLATE_RE.match(template)
        if compile:
            self.debug_item('compiled', '1')
            template = compile.group(1) + ';'
        
        # init variables for the self.do_section loop
        self.lastend = 0
        self.current = StringIO()

        TEMPLATE_SECTION_RE.sub(self.do_section, template)
        
        # after the self.do_section loop
        current = self.current.getvalue()
        current = self.parse_template_tags(current)
        file = open(template_filename(name), 'w')
        file.write(current)

        if len(template) != self.lastend:
            self.debug_item("NOT MATCHED (end)", template[lastend:],
                span=(lastend, len(template)))

    def do_section(self, match):
        if not match.group():
            return

        if match.start() > self.lastend:
            span = (self.lastend, match.start())
            self.debug_item("NOT MATCHED", match.string[span[0]:span[1]],
                span=span)
        
        names = ['html', 'include', 'string', 'const', 'abbrtext']
        groups = list(match.groups())[1:]

        for groupname, value in map(None, names, groups):
            if value:
                self.debug_item(groupname, value, match)
                self.current.write(self.tl.handle_item(groupname, value))

        self.lastend = match.end()


class Jinja2Translator(object):
    '''Just to keep jinja2-specific code separate'''
    TAG_INCLUDE = "{%% include '%s' %%}"
    TAG_FILTER = "{%% filter %s %%}%s{%% endfilter %%}"
    
    def __init__(self, parent):
        # not sure if needed
        self.parent = parent
    
    def handle_item(self, type, value):
        if type == 'string':
            return self.translate_tags(value.decode('string-escape'))
        elif type == 'html':
            return self.translate_tags(value)
        elif type == 'include':
            value = value.replace(HTDOCS_HARDCODED_PATH, '')
            return self.TAG_INCLUDE % value
        elif type == 'const':
            return self.TAG_INCLUDE % template_filename(value)
        elif type == 'abbrtext':
            return self.TAG_FILTER % ('reverse_format(S_ABBRTEXT)', value)
        return value

    def translate_tags(self, value):
        return value

def template_filename(constname):
    return os.path.join(TEMPLATES_DIR, '%s.html' % constname.lower())


if __name__ == '__main__':
    FutabaStyleParser()
