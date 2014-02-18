import platform
from genesis2.utils.utils import shell, shell_status


def detect_platform(mapping=True):
    """
    Returns a text shortname of the current system platform.

    :param  mapping:    if True, map Ubuntu to Debian and so on.
    :type   mapping:    bool
    :rtype:             str
    """
    base_mapping = {
        'gentoo base system': 'gentoo',
        'centos linux': 'centos',
        'mandriva linux': 'mandriva',
        }

    platform_mapping = {
        'ubuntu': 'debian',
        'linuxmint': 'debian',
        }

    if platform.system() != 'Linux':
        return platform.system().lower()

    dist = ''
    (maj, min, patch) = platform.python_version_tuple()
    if (maj * 10 + min) >= 26:
        dist = platform.linux_distribution()[0]
    else:
        dist = platform.dist()[0]

    if dist == '':
        try:
            dist = shell('strings -4 /etc/issue').split()[0]
        except:
            dist = 'unknown'

    res = dist.strip().lower()
    if res in base_mapping:
        res = base_mapping[res]
    if mapping:
        if res in platform_mapping:
            res = platform_mapping[res]
    return res


def detect_distro():
    """
    Returns human-friendly OS name.
    """
    if shell_status('lsb_release -sd') == 0:
        return shell('lsb_release -sd')
    return shell('uname -mrs')


