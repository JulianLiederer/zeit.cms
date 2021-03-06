import zeit.cms.workingcopy.interfaces
import zeit.cms.clipboard.interfaces


class IGhost(zeit.cms.workingcopy.interfaces.ILocalContent,
             zeit.cms.clipboard.interfaces.IObjectReference):
    """Marker interface to distinguish ghosts from "normal" local content
    objects.
    """
