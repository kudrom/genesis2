import base64
import random

from genesis2.core.core import Plugin, implements
from genesis2.interfaces.gui import IXSLTFunctionProvider


def attr(_, v, d):
    return d if v == [] or v == ['None'] else v[0]


# (kudrom) TODO: I think the proposed use is misleading
def css(_, v, d):
    v = d if v == [] or v == ['None'] else v[0]
    if v == 'auto':
            return v
    return v if '%' in v else '%spx' % v


def iif(_, q, a, b):
    if isinstance(q, bool):
        return a if q is not False else b
    else:
        return a if len(q) > 0 and q[0].lower() == 'true' else b


# (kudrom) TODO: If we're using this to escape real js it should be secure
# i don't like the duck typing but the exception handling is worse
def jsesc(_, s):
    if "replace" in dir(s):
        return s.replace('\'', '\\')
    else:
        return s[0].replace('\'', '\\')


def idesc(_, s):
    if "replace" in dir(s):
        return s.replace('/', '_').replace('.', '_')
    else:
        return s[0].replace('/', '_').replace('.', '_')


def b64(_, s):
    try:
        return base64.b64encode(str(s[0]))
    except:
        return base64.b64encode(str(s))


def id(_, s):
    if s.__class__ == list and len(s) > 0:
        s = s[0]
    return s if s else str(random.randint(1, 9000*9000))


class CoreFunctions (Plugin):
    implements(IXSLTFunctionProvider)

    def get_funcs(self):
        return {
            'attr': attr,
            'iif': iif,
            'b64': b64,
            'jsesc': jsesc,
            'idesc': idesc,
            'css': css,
            'id': id
        }
