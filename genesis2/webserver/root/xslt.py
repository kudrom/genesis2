import base64
import random

from genesis2.core.core import Plugin, implements


def attr(_, v, d):
    return d if v == [] or v == ['None'] else v[0]


# TODO: I think the proposed use is misleading
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


def jsesc(_, s):
    try:
        return s.replace('\'', '\\')
    except:
        return s[0].replace('\'', '\\')


def idesc(_, s):
    try:
        return s.replace('/', '_').replace('.', '_')
    except:
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
    # TODO: Uncomment
    #implements(IXSLTFunctionProvider)

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