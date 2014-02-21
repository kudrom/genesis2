def get_template(self, filename=None, search_path=[]):
    return BasicTemplate(
        filename=filename,
        search_path=self.template_path + search_path,
        styles=self.template_styles,
        scripts=self.template_scripts
    )

def inflate(self, layout):
    """
    Inflates an XML UI layout into DOM UI tree.

    :param  layout: '<pluginid>:<layoutname>', ex: dashboard:main for
                    /plugins/dashboard/layout/main.xml
    :type   layout: str
    :rtype:         :class:`genesis.ui.Layout`
    """
    f = self.layouts[layout+'.xml']
    return Layout(f)_author__ = 'kudrom'
